
from django.db import models
from django.contrib.auth.models import User


class Course(models.Model):
    title = models.CharField(
        max_length=200,
        verbose_name="Назва курсу"
    )

    description = models.TextField(
        verbose_name="Опис курсу"
    )

    monthly_price = models.DecimalField(
        max_digits=10,
        decimal_places=2,
        default=0,
        verbose_name="Ціна за місяць (грн)"
    )

    created_at = models.DateTimeField(
        auto_now_add=True,
        verbose_name="Дата створення"
    )

    students = models.ManyToManyField(
        User,
        blank=True,
        related_name="enrolled_courses",
        verbose_name="Учні з доступом"
    )

    def __str__(self):
        return self.title

    class Meta:
        verbose_name = "Курс"
        verbose_name_plural = "Курси"


class StudentProfile(models.Model):
    user = models.OneToOneField(
        User,
        on_delete=models.CASCADE,
        related_name="student_profile"
    )

    phone_number = models.CharField(
        max_length=20,
        verbose_name="Номер телефону"
    )

    def __str__(self):
        return self.user.username
