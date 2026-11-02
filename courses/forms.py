
import secrets

from django import forms
from django.conf import settings
from django.contrib.auth.forms import UserCreationForm
from django.contrib.auth.models import User
from django.db import transaction

from .models import (
    Course,
    Lesson,
    LessonMaterial,
    StudentProfile,
)


class RegisterForm(UserCreationForm):
    email = forms.EmailField(
        required=True,
        label="Електронна пошта",
    )

    phone_number = forms.RegexField(
        regex=r"^\+?[0-9]{10,15}$",
        label="Номер телефону",
        widget=forms.TextInput(
            attrs={"placeholder": "+380991234567"}
        ),
        error_messages={
            "invalid": "Введіть номер із 10–15 цифр."
        },
    )

    role = forms.ChoiceField(
        choices=StudentProfile.ROLE_CHOICES,
        label="Роль",
        widget=forms.RadioSelect,
    )

    special_code = forms.CharField(
        required=False,
        label="Спеціальний код адміністрації",
        widget=forms.PasswordInput(
            attrs={
                "placeholder": "Введіть спеціальний код",
                "autocomplete": "off",
            }
        ),
    )

    class Meta:
        model = User
        fields = [
            "username",
            "email",
            "phone_number",
            "role",
            "special_code",
            "password1",
            "password2",
        ]

    def clean(self):
        cleaned_data = super().clean()

        role = cleaned_data.get("role")
        entered_code = cleaned_data.get("special_code", "")

        if role == "admin":
            correct_code = getattr(
                settings,
                "SUPERADMIN_REGISTRATION_CODE",
                "",
            )

            if not correct_code:
                self.add_error(
                    "special_code",
                    "Реєстрація адміністрації тимчасово вимкнена.",
                )
            elif not entered_code or not secrets.compare_digest(
                entered_code,
                correct_code,
            ):
                self.add_error(
                    "special_code",
                    "Неправильний спеціальний код.",
                )

        return cleaned_data

    @transaction.atomic
    def save(self, commit=True):
        if not commit:
            raise ValueError(
                "Ця форма потребує збереження користувача."
            )

        user = super().save(commit=False)

        role = self.cleaned_data["role"]

        user.email = self.cleaned_data["email"]

        if role == "admin":
            user.is_superuser = True
            user.is_staff = True

        user.save()

        StudentProfile.objects.create(
            user=user,
            phone_number=self.cleaned_data["phone_number"],
            role=role,
            teacher_approved=False,
        )

        return user


class CourseForm(forms.ModelForm):
    class Meta:
        model = Course
        fields = [
            "title",
            "description",
            "monthly_price",
            "max_students",
        ]
        labels = {
            "title": "Назва курсу",
            "description": "Опис курсу",
            "monthly_price": "Ціна за 30 днів, грн",
            "max_students": "Максимальна кількість учнів",
        }
        widgets = {
            "description": forms.Textarea(
                attrs={"rows": 5}
            ),
            "monthly_price": forms.NumberInput(
                attrs={"min": "0", "step": "0.01"}
            ),
            "max_students": forms.NumberInput(
                attrs={"min": "1"}
            ),
        }

    def clean_monthly_price(self):
        price = self.cleaned_data["monthly_price"]

        if price < 0:
            raise forms.ValidationError(
                "Ціна не може бути від'ємною."
            )

        return price

    def clean_max_students(self):
        value = self.cleaned_data["max_students"]

        if value < 1:
            raise forms.ValidationError(
                "Має бути хоча б одне місце."
            )

        if self.instance.pk:
            if value < self.instance.enrolled_count:
                raise forms.ValidationError(
                    "Не можна встановити менше місць, "
                    "ніж є учнів з активною оплатою."
                )

        return value


class AdminCourseForm(CourseForm):
    teacher = forms.ModelChoiceField(
        queryset=User.objects.none(),
        required=False,
        label="Викладач курсу",
    )

    class Meta(CourseForm.Meta):
        fields = CourseForm.Meta.fields + ["teacher"]

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)

        self.fields["teacher"].queryset = User.objects.filter(
            student_profile__role="teacher",
            student_profile__teacher_approved=True,
            is_active=True,
        ).order_by("username")


class LessonForm(forms.ModelForm):
    class Meta:
        model = Lesson
        fields = [
            "title",
            "order",
            "content",
            "resource_url",
            "assignment",
        ]
        labels = {
            "title": "Назва уроку",
            "order": "Порядок уроку",
            "content": "Текст уроку",
            "resource_url": "Посилання на матеріали",
            "assignment": "Домашнє завдання",
        }
        widgets = {
            "content": forms.Textarea(
                attrs={"rows": 7}
            ),
            "assignment": forms.Textarea(
                attrs={"rows": 4}
            ),
            "order": forms.NumberInput(
                attrs={"min": "1"}
            ),
        }


class MaterialForm(forms.ModelForm):
    class Meta:
        model = LessonMaterial
        fields = ["title", "file"]
        labels = {
            "title": "Назва матеріалу",
            "file": "PDF-файл",
        }
        widgets = {
            "file": forms.ClearableFileInput(
                attrs={"accept": ".pdf,application/pdf"}
            )
        }

    def clean_file(self):
        file = self.cleaned_data["file"]

        if file.size > 10 * 1024 * 1024:
            raise forms.ValidationError(
                "Максимальний розмір PDF — 10 МБ."
            )

        if not file.name.lower().endswith(".pdf"):
            raise forms.ValidationError(
                "Дозволено завантажувати тільки PDF."
            )

        header = file.read(5)
        file.seek(0)

        if header != b"%PDF-":
            raise forms.ValidationError(
                "Файл не схожий на PDF."
            )

        return file
