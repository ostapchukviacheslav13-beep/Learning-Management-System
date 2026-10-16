
from django.contrib import admin
from .models import Course


@admin.register(Course)
class CourseAdmin(admin.ModelAdmin):
    list_display = ("title", "created_at", "students_count")
    search_fields = ("title", "description")
    filter_horizontal = ("students",)

    @admin.display(description="Кількість учнів")
    def students_count(self, obj):
        return obj.students.count()