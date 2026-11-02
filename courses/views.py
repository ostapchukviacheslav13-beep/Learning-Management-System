
from datetime import timedelta
from pathlib import Path
import uuid

from django.conf import settings
from django.contrib import messages
from django.contrib.auth import login, logout
from django.contrib.auth.decorators import login_required
from django.contrib.auth.forms import AuthenticationForm
from django.contrib.auth.models import User
from django.db import transaction
from django.db.models import F
from django.http import FileResponse, Http404, HttpResponseForbidden
from django.shortcuts import render, redirect, get_object_or_404
from django.utils import timezone
from django.views.decorators.http import require_POST

from .forms import (
    RegisterForm,
    CourseForm,
    AdminCourseForm,
    LessonForm,
    MaterialForm,
)
from .models import (
    StudentProfile,
    Course,
    CourseRequest,
    CoursePayment,
    PaymentRecord,
    Lesson,
    LessonMaterial,
)
from .permissions import (
    is_admin,
    is_teacher,
    is_student,
    managed_courses,
    can_manage,
    can_read,
)


def course_list(request):
    courses = Course.objects.select_related("teacher").order_by("-created_at")

    active_ids = set()
    request_statuses = {}

    if request.user.is_authenticated and is_student(request.user):
        active_ids = set(
            CoursePayment.objects.filter(
                student=request.user,
                paid_until__gt=timezone.now(),
            ).values_list("course_id", flat=True)
        )
        request_statuses = dict(
            CourseRequest.objects.filter(
                student=request.user
            ).values_list("course_id", "status")
        )

    for course in courses:
        course.has_access = course.id in active_ids
        course.request_status = request_statuses.get(course.id)
        course.can_manage = (
            request.user.is_authenticated
            and can_manage(request.user, course)
        )

    return render(
        request,
        "courses/course_list.html",
        {"courses": courses},
    )


def register_view(request):
    if request.user.is_authenticated:
        return redirect("course_list")

    if request.method == "POST":
        form = RegisterForm(request.POST)
        if form.is_valid():
            user = form.save()
            login(request, user)

            if form.cleaned_data["role"] == "teacher":
                messages.info(
                    request,
                    "Акаунт викладача створено. "
                    "Очікуйте схвалення супер-адміністратора.",
                )
            else:
                messages.success(
                    request, "Реєстрація успішна!"
                )

            return redirect("course_list")
    else:
        form = RegisterForm()

    return render(
        request, "courses/register.html", {"form": form}
    )


def login_view(request):
    if request.user.is_authenticated:
        return redirect("course_list")

    if request.method == "POST":
        form = AuthenticationForm(request, data=request.POST)
        if form.is_valid():
            login(request, form.get_user())
            return redirect("course_list")
        messages.error(request, "Неправильний логін або пароль.")
    else:
        form = AuthenticationForm(request)

    return render(
        request, "courses/login.html", {"form": form}
    )


@require_POST
@login_required(login_url="login")
def logout_view(request):
    logout(request)
    return redirect("course_list")


@login_required(login_url="login")
def my_courses(request):
    if is_teacher(request.user) or is_admin(request.user):
        return redirect("teacher_dashboard")

    courses = Course.objects.filter(
        payments__student=request.user,
        payments__paid_until__gt=timezone.now(),
    ).select_related("teacher").distinct()

    return render(
        request, "courses/my_courses.html", {"courses": courses}
    )


@login_required(login_url="login")
def course_detail(request, course_id):
    course = get_object_or_404(
        Course.objects.select_related("teacher"),
        pk=course_id,
    )

    if not can_read(request.user, course):
        return HttpResponseForbidden(
            "Немає доступу. Учень повинен мати активну оплату."
        )

    lessons = course.lessons.prefetch_related("materials").all()

    return render(
        request,
        "courses/course_detail.html",
        {
            "course": course,
            "lessons": lessons,
            "can_manage": can_manage(request.user, course),
        },
    )


@require_POST
@login_required(login_url="login")
def request_join_course(request, course_id):
    if not is_student(request.user):
        return HttpResponseForbidden(
            "Подавати заявки можуть тільки учні."
        )

    with transaction.atomic():
        course = get_object_or_404(
            Course.objects.select_for_update(), pk=course_id
        )

        active_payment = CoursePayment.objects.filter(
            course=course,
            student=request.user,
            paid_until__gt=timezone.now(),
        ).exists()

        if active_payment:
            messages.info(request, "У тебе вже є доступ до курсу.")
        elif course.is_full:
            messages.error(request, "На курсі немає вільних місць.")
        else:
            application, created = CourseRequest.objects.get_or_create(
                course=course,
                student=request.user,
                defaults={"status": "pending"},
            )

            if not created and application.status != "pending":
                application.status = "pending"
                application.save(update_fields=["status"])

            messages.success(
                request,
                "Заявку відправлено викладачеві."
            )

    return redirect("course_list")


@login_required(login_url="login")
def teacher_dashboard(request):
    if not (is_teacher(request.user) or is_admin(request.user)):
        return HttpResponseForbidden("Немає доступу до панелі.")

    courses = managed_courses(request.user).select_related("teacher")
    pending_requests = CourseRequest.objects.filter(
        course__in=courses,
        status="pending",
    ).select_related("course", "student")

    return render(
        request,
        "courses/teacher_dashboard.html",
        {
            "courses": courses,
            "courses_count": courses.count(),
            "pending_requests": pending_requests,
            "pending_count": pending_requests.count(),
            "students_count": StudentProfile.objects.filter(
                role="student"
            ).count(),
            "is_super_admin": is_admin(request.user),
        },
    )


@login_required(login_url="login")
def teacher_course_create(request):
    if not (is_teacher(request.user) or is_admin(request.user)):
        return HttpResponseForbidden("Немає доступу.")

    form_class = AdminCourseForm if is_admin(request.user) else CourseForm

    if request.method == "POST":
        form = form_class(request.POST)
        if form.is_valid():
            course = form.save(commit=False)
            if is_admin(request.user):
                course.teacher = form.cleaned_data.get("teacher")
            else:
                course.teacher = request.user
            course.save()
            messages.success(request, "Курс створено.")
            return redirect("teacher_dashboard")
    else:
        form = form_class()

    return render(
        request,
        "courses/teacher_course_form.html",
        {"form": form, "page_title": "Створити курс"},
    )


@login_required(login_url="login")
def teacher_course_edit(request, course_id):
    course = get_object_or_404(
        managed_courses(request.user), pk=course_id
    )
    form_class = AdminCourseForm if is_admin(request.user) else CourseForm

    if request.method == "POST":
        form = form_class(request.POST, instance=course)
        if form.is_valid():
            with transaction.atomic():
                locked = Course.objects.select_for_update().get(pk=course.pk)
                if form.cleaned_data["max_students"] < locked.enrolled_count:
                    form.add_error(
                        "max_students",
                        "Кількість місць не може бути меншою за кількість учнів з активною оплатою.",
                    )
                else:
                    updated = form.save(commit=False)
                    if is_admin(request.user):
                        updated.teacher = form.cleaned_data.get("teacher")
                    else:
                        updated.teacher = request.user
                    updated.save()
                    messages.success(request, "Курс оновлено.")
                    return redirect("teacher_dashboard")
    else:
        form = form_class(instance=course)

    return render(
        request,
        "courses/teacher_course_form.html",
        {"form": form, "page_title": "Редагувати курс"},
    )


@login_required(login_url="login")
def teacher_course_delete(request, course_id):
    course = get_object_or_404(
        managed_courses(request.user), pk=course_id
    )

    if request.method == "POST":
        course.delete()
        messages.success(request, "Курс видалено.")
        return redirect("teacher_dashboard")

    return render(
        request,
        "courses/teacher_confirm_delete.html",
        {"course": course},
    )


@login_required(login_url="login")
def teacher_students(request):
    if is_admin(request.user):
        students = User.objects.filter(
            student_profile__role="student"
        )
    elif is_teacher(request.user):
        students = User.objects.filter(
            course_requests__course__teacher=request.user
        ).distinct()
    else:
        return HttpResponseForbidden("Немає доступу.")

    return render(
        request,
        "courses/teacher_students.html",
        {"students": students.order_by("username")},
    )


@require_POST
@login_required(login_url="login")
def teacher_request_approve(request, request_id):
    application = get_object_or_404(
        CourseRequest.objects.select_related("course", "student"),
        pk=request_id,
    )
    course = get_object_or_404(
        managed_courses(request.user), pk=application.course_id
    )

    with transaction.atomic():
        course = Course.objects.select_for_update().get(pk=course.pk)
        application = CourseRequest.objects.select_for_update().get(
            pk=application.pk
        )

        if application.status != "pending":
            messages.error(request, "Цю заявку вже оброблено.")
            return redirect("teacher_dashboard")

        if not is_student(application.student):
            messages.error(request, "Обліковий запис не є учнем.")
            return redirect("teacher_dashboard")

        now = timezone.now()
        payment = CoursePayment.objects.filter(
            course=course, student=application.student
        ).first()

        if payment and payment.paid_until > now:
            start = payment.paid_until
        else:
            if course.is_full:
                messages.error(request, "Вільних місць більше немає.")
                return redirect("teacher_dashboard")
            start = now

        access_until = start + timedelta(days=30)

        CoursePayment.objects.update_or_create(
            course=course,
            student=application.student,
            defaults={
                "confirmed_at": now,
                "paid_until": access_until,
            },
        )

        PaymentRecord.objects.create(
            course=course,
            student=application.student,
            confirmed_by=request.user,
            amount=course.monthly_price,
            confirmed_at=now,
            access_from=start,
            access_until=access_until,
        )

        course.students.add(application.student)
        application.status = "approved"
        application.save(update_fields=["status"])

    messages.success(
        request, "Оплату підтверджено, доступ відкрито на 30 днів."
    )
    return redirect("teacher_dashboard")


@require_POST
@login_required(login_url="login")
def teacher_request_reject(request, request_id):
    application = get_object_or_404(
        CourseRequest.objects.select_related("course"),
        pk=request_id,
    )
    get_object_or_404(
        managed_courses(request.user), pk=application.course_id
    )

    if application.status == "pending":
        application.status = "rejected"
        application.save(update_fields=["status"])
        messages.success(request, "Заявку відхилено.")

    return redirect("teacher_dashboard")


@login_required(login_url="login")
def teacher_lesson_create(request, course_id):
    course = get_object_or_404(
        managed_courses(request.user), pk=course_id
    )

    if request.method == "POST":
        form = LessonForm(request.POST)
        if form.is_valid():
            lesson = form.save(commit=False)
            lesson.course = course
            lesson.created_by = request.user
            lesson.save()
            messages.success(request, "Урок створено.")
            return redirect("course_detail", course_id=course.pk)
    else:
        form = LessonForm()

    return render(
        request,
        "courses/teacher_lesson_form.html",
        {"form": form, "course": course, "page_title": "Новий урок"},
    )


@login_required(login_url="login")
def teacher_lesson_edit(request, lesson_id):
    lesson = get_object_or_404(
        Lesson.objects.select_related("course"), pk=lesson_id
    )
    get_object_or_404(
        managed_courses(request.user), pk=lesson.course_id
    )

    if request.method == "POST":
        form = LessonForm(request.POST, instance=lesson)
        if form.is_valid():
            form.save()
            messages.success(request, "Урок оновлено.")
            return redirect("course_detail", course_id=lesson.course_id)
    else:
        form = LessonForm(instance=lesson)

    return render(
        request,
        "courses/teacher_lesson_form.html",
        {"form": form, "course": lesson.course, "page_title": "Редагувати урок"},
    )


@require_POST
@login_required(login_url="login")
def teacher_lesson_delete(request, lesson_id):
    lesson = get_object_or_404(Lesson, pk=lesson_id)
    get_object_or_404(
        managed_courses(request.user), pk=lesson.course_id
    )
    course_id = lesson.course_id
    lesson.delete()
    messages.success(request, "Урок видалено.")
    return redirect("course_detail", course_id=course_id)


@login_required(login_url="login")
def teacher_material_upload(request, lesson_id):
    lesson = get_object_or_404(Lesson, pk=lesson_id)
    get_object_or_404(
        managed_courses(request.user), pk=lesson.course_id
    )

    if request.method == "POST":
        form = MaterialForm(request.POST, request.FILES)
        if form.is_valid():
            material = form.save(commit=False)
            material.lesson = lesson
            material.save()
            messages.success(request, "Матеріал завантажено.")
            return redirect("course_detail", course_id=lesson.course_id)
    else:
        form = MaterialForm()

    return render(
        request,
        "courses/teacher_material_form.html",
        {"form": form, "lesson": lesson},
    )


@login_required(login_url="login")
def material_download(request, material_id):
    material = get_object_or_404(
        LessonMaterial.objects.select_related("lesson__course"),
        pk=material_id,
    )

    if not can_read(request.user, material.lesson.course):
        return HttpResponseForbidden("Немає доступу до цього матеріалу.")

    if not material.file:
        raise Http404("Файл не знайдено.")

    file_path = Path(material.file.path)
    if not file_path.is_file():
        raise Http404("Файл не знайдено.")

    return FileResponse(
        open(file_path, "rb"),
        as_attachment=True,
        filename=Path(material.file.name).name,
    )


@login_required(login_url="login")
def admin_dashboard(request):
    if not is_admin(request.user):
        return HttpResponseForbidden("Доступ тільки для супер-адміністратора.")

    teachers = StudentProfile.objects.filter(
        role="teacher"
    ).select_related("user").order_by("teacher_approved", "user__username")

    courses = Course.objects.select_related("teacher").order_by("-created_at")

    records = PaymentRecord.objects.select_related(
        "course", "student", "confirmed_by"
    )[:100]

    return render(
        request,
        "courses/admin_dashboard.html",
        {
            "teachers": teachers,
            "courses": courses,
            "students_count": StudentProfile.objects.filter(role="student").count(),
            "payment_records": records,
        },
    )


@require_POST
@login_required(login_url="login")
def admin_teacher_approve(request, profile_id):
    if not is_admin(request.user):
        return HttpResponseForbidden("Немає доступу.")

    profile = get_object_or_404(
        StudentProfile, pk=profile_id, role="teacher"
    )
    profile.teacher_approved = True
    profile.save(update_fields=["teacher_approved"])
    messages.success(request, "Викладача схвалено.")
    return redirect("admin_dashboard")


@require_POST
@login_required(login_url="login")
def admin_teacher_block(request, profile_id):
    if not is_admin(request.user):
        return HttpResponseForbidden("Немає доступу.")

    profile = get_object_or_404(
        StudentProfile, pk=profile_id, role="teacher"
    )
    profile.teacher_approved = False
    profile.save(update_fields=["teacher_approved"])
    messages.success(request, "Викладача заблоковано.")
    return redirect("admin_dashboard")
