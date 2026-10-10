from django.contrib import admin
from .models import AttendanceRecord, AttendanceSession, CourseClass, Student, TeachingPlan


class StudentInline(admin.TabularInline):
    model = Student
    extra = 0
    fields = ("serial_number", "roll_number", "name", "active")


@admin.register(CourseClass)
class CourseClassAdmin(admin.ModelAdmin):
    list_display = ("name", "branch", "batch_year", "section", "teacher", "student_count")
    list_filter = ("branch", "batch_year", "section")
    search_fields = ("name", "teacher__email")
    inlines = [StudentInline]


@admin.register(AttendanceSession)
class AttendanceSessionAdmin(admin.ModelAdmin):
    list_display = ("course_class", "date", "slot", "topic", "updated_at")
    list_filter = ("date", "course_class__branch")


admin.site.register(AttendanceRecord)
admin.site.register(TeachingPlan)
