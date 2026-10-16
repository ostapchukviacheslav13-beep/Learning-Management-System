
from django.shortcuts import render, redirect, get_object_or_404
from django.contrib.auth import login, logout
from django.contrib.auth.forms import AuthenticationForm
from django.contrib.auth.decorators import login_required, user_passes_test
from django.contrib import messages
from django.contrib.auth.models import User

from .models import Course
from .forms import RegisterForm, CourseForm


def is_teacher(user):
    return user.is_authenticated and user.is_staff


def course_list(request):
    if request.user.is_authenticated and request.user.is_staff:
        courses = Course.objects.all()
    elif request.user.is_authenticated:
        courses = Course.objects.filter(students=request.user)
    else:
        courses = Course.objects.none()

    return render(request, "courses/course_list.html", {
        "courses": courses
    })



def register_view(request):
    if request.method == "POST":
        form = RegisterForm(request.POST)

        if form.is_valid():
            user = form.save()
            login(request, user)
            return redirect("course_list")
    else:
        form = RegisterForm()

    return render(
        request,
        "courses/register.html",
        {"form": form}
    )



def login_view(request):
    if request.method == "POST":
        form = AuthenticationForm(request, data=request.POST)
        if form.is_valid():
            login(request, form.get_user())
            return redirect("course_list")
        messages.error(request, "Неправильний логін або пароль.")
    else:
        form = AuthenticationForm(request)

    return render(request, "courses/login.html", {"form": form})


@login_required
def logout_view(request):
    if request.method == "POST":
        logout(request)
        return redirect("course_list")
    return redirect("course_list")


@login_required
def my_courses(request):
    if request.user.is_staff:
        courses = Course.objects.all()
    else:
        courses = Course.objects.filter(students=request.user)

    return render(request, "courses/my_courses.html", {
        "courses": courses
    })


@login_required
def course_detail(request, course_id):
    course = get_object_or_404(Course, id=course_id)

    if not request.user.is_staff:
        if not course.students.filter(id=request.user.id).exists():
            messages.error(request, "У вас немає доступу до цього курсу.")
            return redirect("my_courses")

    return render(request, "courses/course_detail.html", {
        "course": course
    })


@user_passes_test(is_teacher)
def teacher_dashboard(request):
    context = {
        "courses": Course.objects.all().order_by("-created_at"),
        "courses_count": Course.objects.count(),
        "students_count": User.objects.filter(
            is_staff=False,
            is_superuser=False
        ).count(),
    }
    return render(request, "courses/teacher_dashboard.html", context)


@user_passes_test(is_teacher)
def teacher_course_create(request):
    if request.method == "POST":
        form = CourseForm(request.POST)
        if form.is_valid():
            form.save()
            messages.success(request, "Курс успішно створено.")
            return redirect("teacher_dashboard")
    else:
        form = CourseForm()

    return render(request, "courses/teacher_course_form.html", {
        "form": form,
        "page_title": "Створення курсу",
    })


@user_passes_test(is_teacher)
def teacher_course_edit(request, course_id):
    course = get_object_or_404(Course, id=course_id)

    if request.method == "POST":
        form = CourseForm(request.POST, instance=course)
        if form.is_valid():
            form.save()
            messages.success(request, "Курс успішно оновлено.")
            return redirect("teacher_dashboard")
    else:
        form = CourseForm(instance=course)

    return render(request, "courses/teacher_course_form.html", {
        "form": form,
        "page_title": "Редагування курсу",
    })


@user_passes_test(is_teacher)
def teacher_course_delete(request, course_id):
    course = get_object_or_404(Course, id=course_id)

    if request.method == "POST":
        course.delete()
        messages.success(request, "Курс видалено.")
        return redirect("teacher_dashboard")

    return render(request, "courses/teacher_confirm_delete.html", {
        "course": course
    })


@user_passes_test(is_teacher)
def teacher_students(request):
    students = User.objects.filter(
        is_staff=False,
        is_superuser=False
    ).order_by("username")

    return render(request, "courses/teacher_students.html", {
        "students": students
    })