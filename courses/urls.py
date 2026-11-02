
from django.urls import path
from django.contrib.auth import views as auth_views
from . import views

urlpatterns = [
    path("", views.course_list, name="course_list"),
    path("register/", views.register_view, name="register"),
    path("login/", views.login_view, name="login"),
    path("logout/", views.logout_view, name="logout"),
    path("my-courses/", views.my_courses, name="my_courses"),

    path(
        "course/<int:course_id>/",
        views.course_detail,
        name="course_detail",
    ),
    path(
        "course/<int:course_id>/join/",
        views.request_join_course,
        name="request_join_course",
    ),

    path("teacher/", views.teacher_dashboard, name="teacher_dashboard"),
    path(
        "teacher/courses/create/",
        views.teacher_course_create,
        name="teacher_course_create",
    ),
    path(
        "teacher/courses/<int:course_id>/edit/",
        views.teacher_course_edit,
        name="teacher_course_edit",
    ),
    path(
        "teacher/courses/<int:course_id>/delete/",
        views.teacher_course_delete,
        name="teacher_course_delete",
    ),
    path("teacher/students/", views.teacher_students, name="teacher_students"),

    path(
        "teacher/requests/<int:request_id>/approve/",
        views.teacher_request_approve,
        name="teacher_request_approve",
    ),
    path(
        "teacher/requests/<int:request_id>/reject/",
        views.teacher_request_reject,
        name="teacher_request_reject",
    ),

    path(
        "teacher/courses/<int:course_id>/lessons/create/",
        views.teacher_lesson_create,
        name="teacher_lesson_create",
    ),
    path(
        "teacher/lessons/<int:lesson_id>/edit/",
        views.teacher_lesson_edit,
        name="teacher_lesson_edit",
    ),
    path(
        "teacher/lessons/<int:lesson_id>/delete/",
        views.teacher_lesson_delete,
        name="teacher_lesson_delete",
    ),
    path(
        "teacher/lessons/<int:lesson_id>/materials/upload/",
        views.teacher_material_upload,
        name="teacher_material_upload",
    ),
    path(
        "materials/<int:material_id>/download/",
        views.material_download,
        name="material_download",
    ),

    path("super-admin/", views.admin_dashboard, name="admin_dashboard"),
    path(
        "super-admin/teachers/<int:profile_id>/approve/",
        views.admin_teacher_approve,
        name="admin_teacher_approve",
    ),
    path(
        "super-admin/teachers/<int:profile_id>/block/",
        views.admin_teacher_block,
        name="admin_teacher_block",
    ),

    path(
        "password-reset/",
        auth_views.PasswordResetView.as_view(
            template_name="courses/password_reset.html",
            email_template_name="courses/password_reset_email.txt",
            subject_template_name="courses/password_reset_subject.txt",
            success_url="/password-reset/done/",
        ),
        name="password_reset",
    ),
    path(
        "password-reset/done/",
        auth_views.PasswordResetDoneView.as_view(
            template_name="courses/password_reset_done.html",
        ),
        name="password_reset_done",
    ),
    path(
        "reset/<uidb64>/<token>/",
        auth_views.PasswordResetConfirmView.as_view(
            template_name="courses/password_reset_confirm.html",
            success_url="/reset/complete/",
        ),
        name="password_reset_confirm",
    ),
    path(
        "reset/complete/",
        auth_views.PasswordResetCompleteView.as_view(
            template_name="courses/password_reset_complete.html",
        ),
        name="password_reset_complete",
    ),
]
