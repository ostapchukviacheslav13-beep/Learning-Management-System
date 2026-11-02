
from django.utils import timezone

from .models import Course, CoursePayment, StudentProfile


def is_admin(user):
    return (
        user.is_authenticated
        and user.is_active
        and user.is_superuser
    )


def is_teacher(user):
    if (
        not user.is_authenticated
        or not user.is_active
        or user.is_superuser
    ):
        return False

    profile = StudentProfile.objects.filter(
        user=user
    ).first()

    if profile:
        return (
            profile.role == "teacher"
            and profile.teacher_approved
        )

    # Для старих акаунтів, створених до системи ролей.
    return user.is_staff


def is_student(user):
    if (
        not user.is_authenticated
        or not user.is_active
        or user.is_superuser
        or user.is_staff
    ):
        return False

    profile = StudentProfile.objects.filter(
        user=user
    ).first()

    return (
        profile is not None
        and profile.role == "student"
    )


def managed_courses(user):
    if is_admin(user):
        return Course.objects.all()

    if is_teacher(user):
        return Course.objects.filter(teacher=user)

    return Course.objects.none()


def can_manage(user, course):
    return (
        is_admin(user)
        or (
            is_teacher(user)
            and course.teacher_id == user.pk
        )
    )


def can_read(user, course):
    if can_manage(user, course):
        return True

    if not is_student(user):
        return False

    return CoursePayment.objects.filter(
        course=course,
        student=user,
        paid_until__gt=timezone.now(),
    ).exists()
