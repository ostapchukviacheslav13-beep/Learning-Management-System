
from django.conf import settings
from django.db import models
from django.db.models import Q
from django.utils import timezone


class StudentProfile(models.Model):
    ROLE_CHOICES = [
        ("student", "Учень"),
        ("teacher", "Викладач"),
    ]

    user = models.OneToOneField(
        settings.AUTH_USER_MODEL,
        on_delete=models.CASCADE,
        related_name="student_profile",
    )
    phone_number = models.CharField(max_length=20, blank=True)
    role = models.CharField(
        max_length=10,
        choices=ROLE_CHOICES,
        default="student",
    )
    teacher_approved = models.BooleanField(default=False)

    def __str__(self):
        return self.user.username


class Course(models.Model):
    teacher = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name="created_courses",
    )
    title = models.CharField(max_length=200)
    description = models.TextField()
    monthly_price = models.DecimalField(
        max_digits=10,
        decimal_places=2,
        default=0,
    )
    max_students = models.PositiveIntegerField(default=10)
    created_at = models.DateTimeField(auto_now_add=True)
    lock_version = models.PositiveIntegerField(default=0)

    students = models.ManyToManyField(
        settings.AUTH_USER_MODEL,
        blank=True,
        related_name="enrolled_courses",
    )

    @property
    def enrolled_count(self):
        return self.payments.filter(
            paid_until__gt=timezone.now()
        ).count()

    @property
    def free_places(self):
        return max(0, self.max_students - self.enrolled_count)

    @property
    def is_full(self):
        return self.free_places == 0

    def __str__(self):
        return self.title

    class Meta:
        constraints = [
            models.CheckConstraint(
                condition=Q(max_students__gte=1),
                name="course_capacity_positive",
            ),
            models.CheckConstraint(
                condition=Q(monthly_price__gte=0),
                name="course_price_nonnegative",
            ),
        ]


class CourseRequest(models.Model):
    STATUS_CHOICES = [
        ("pending", "Очікує"),
        ("approved", "Прийнято"),
        ("rejected", "Відхилено"),
    ]

    course = models.ForeignKey(
        Course,
        on_delete=models.CASCADE,
        related_name="join_requests",
    )
    student = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.CASCADE,
        related_name="course_requests",
    )
    status = models.CharField(
        max_length=10,
        choices=STATUS_CHOICES,
        default="pending",
    )
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        constraints = [
            models.UniqueConstraint(
                fields=["course", "student"],
                name="unique_course_student_request",
            )
        ]


class CoursePayment(models.Model):
    course = models.ForeignKey(
        Course,
        on_delete=models.CASCADE,
        related_name="payments",
    )
    student = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.CASCADE,
        related_name="course_payments",
    )
    confirmed_at = models.DateTimeField(default=timezone.now)
    paid_until = models.DateTimeField()

    class Meta:
        constraints = [
            models.UniqueConstraint(
                fields=["course", "student"],
                name="unique_course_payment",
            )
        ]

    @property
    def is_active(self):
        return self.paid_until > timezone.now()


class PaymentRecord(models.Model):
    course = models.ForeignKey(
        Course,
        on_delete=models.CASCADE,
        related_name="payment_records",
    )
    student = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.CASCADE,
        related_name="payment_records",
    )
    confirmed_by = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.SET_NULL,
        null=True,
        related_name="confirmed_payments",
    )
    amount = models.DecimalField(
        max_digits=10,
        decimal_places=2,
    )
    confirmed_at = models.DateTimeField(default=timezone.now)
    access_from = models.DateTimeField()
    access_until = models.DateTimeField()

    class Meta:
        ordering = ["-confirmed_at"]


class Lesson(models.Model):
    course = models.ForeignKey(
        Course,
        on_delete=models.CASCADE,
        related_name="lessons",
    )
    created_by = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name="created_lessons",
    )
    title = models.CharField(max_length=200)
    content = models.TextField(blank=True)
    resource_url = models.URLField(blank=True)
    assignment = models.TextField(blank=True)
    order = models.PositiveIntegerField(default=1)
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        ordering = ["order", "id"]

    def __str__(self):
        return self.title


class LessonMaterial(models.Model):
    lesson = models.ForeignKey(
        Lesson,
        on_delete=models.CASCADE,
        related_name="materials",
    )
    title = models.CharField(max_length=200)
    file = models.FileField(
        upload_to="lesson_pdfs/%Y/%m/"
    )
    uploaded_at = models.DateTimeField(auto_now_add=True)

    def __str__(self):
        return self.title
