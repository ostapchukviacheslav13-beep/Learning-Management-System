
from django import forms
from django.contrib.auth.models import User
from django.contrib.auth.forms import UserCreationForm

from .models import Course, StudentProfile


class RegisterForm(UserCreationForm):
    email = forms.EmailField(
        required=True,
        label="Електронна пошта"
    )

    phone_number = forms.RegexField(
        regex=r"^\+?[0-9]{10,15}$",
        max_length=16,
        required=True,
        label="Номер телефону",
        error_messages={
            "invalid": "Введіть номер із 10–15 цифр, наприклад +380XXXXXXXXX."
        },
        widget=forms.TextInput(
            attrs={"placeholder": "+380XXXXXXXXX"}
        )
    )

    class Meta:
        model = User
        fields = [
            "username",
            "email",
            "phone_number",
            "password1",
            "password2",
        ]

        labels = {
            "username": "Ім'я користувача",
        }

    def save(self, commit=True):
        user = super().save(commit=False)
        user.email = self.cleaned_data["email"]

        if commit:
            user.save()

            StudentProfile.objects.update_or_create(
                user=user,
                defaults={
                    "phone_number": self.cleaned_data["phone_number"]
                }
            )

        return user


class CourseForm(forms.ModelForm):
    students = forms.ModelMultipleChoiceField(
        queryset=User.objects.filter(
            is_staff=False,
            is_superuser=False
        ),
        required=False,
        label="Учні, які мають доступ",
        widget=forms.CheckboxSelectMultiple()
    )

    class Meta:
        model = Course

        fields = [
            "title",
            "description",
            "monthly_price",
            "students",
        ]

        labels = {
            "title": "Назва курсу",
            "description": "Опис курсу",
            "monthly_price": "Ціна за місяць (грн)",
        }

        widgets = {
            "description": forms.Textarea(
                attrs={"rows": 6}
            ),
            "monthly_price": forms.NumberInput(
                attrs={
                    "min": "0",
                    "step": "0.01",
                    "placeholder": "Наприклад: 500"
                }
            ),
        }

    def clean_monthly_price(self):
        price = self.cleaned_data["monthly_price"]

        if price < 0:
            raise forms.ValidationError(
                "Ціна не може бути від'ємною."
            )

        return price
