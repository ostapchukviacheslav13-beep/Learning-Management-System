
from django.urls import path
from . import views

urlpatterns = [
    path("", views.course_list, name="course_list"),
    path("register/", views.register_view, name="register"),
    path("login/", views.login_view, name="login"),
    path("logout/", views.logout_view, name="logout"),

    path("my-courses/", views.my_courses, name="my_courses"),
    path("course/<int:course_id>/", views.course_detail, name="course_detail"),

    # Панель викладача
    path("teacher/", views.teacher_dashboard, name="teacher_dashboard"),

    # Керування курсами
    path("teacher/courses/create/", views.teacher_course_create, name="teacher_course_create"),
    path("teacher/courses/<int:course_id>/edit/", views.teacher_course_edit, name="teacher_course_edit"),
    path("teacher/courses/<int:course_id>/delete/", views.teacher_course_delete, name="teacher_course_delete"),

    # Список учнів
    path("teacher/students/", views.teacher_students, name="teacher_students"),
]
