from django.contrib import admin
from django.contrib.auth.admin import UserAdmin as DjangoUserAdmin

from .models import Attendance, Grade, Lesson, Notification, StudyGroup, Subject, User


@admin.register(User)
class UserAdmin(DjangoUserAdmin):
    list_display = ("username", "last_name", "first_name", "role", "group", "is_staff")
    list_filter = ("role", "group", "is_staff", "is_superuser")
    fieldsets = DjangoUserAdmin.fieldsets + (
        ("Роль в системе", {"fields": ("role", "group")}),
    )
    add_fieldsets = DjangoUserAdmin.add_fieldsets + (
        ("Роль в системе", {"fields": ("role", "group")}),
    )


@admin.register(StudyGroup)
class StudyGroupAdmin(admin.ModelAdmin):
    list_display = ("name", "curator")
    search_fields = ("name",)


@admin.register(Subject)
class SubjectAdmin(admin.ModelAdmin):
    list_display = ("name",)
    search_fields = ("name",)
    filter_horizontal = ("teachers",)


@admin.register(Lesson)
class LessonAdmin(admin.ModelAdmin):
    list_display = ("date", "subject", "group", "teacher", "topic")
    list_filter = ("date", "subject", "group", "teacher")
    search_fields = ("topic",)


@admin.register(Attendance)
class AttendanceAdmin(admin.ModelAdmin):
    list_display = ("lesson", "student", "status", "comment")
    list_filter = ("status", "lesson__date", "lesson__subject", "lesson__group")
    search_fields = ("student__username", "student__last_name", "comment")


@admin.register(Grade)
class GradeAdmin(admin.ModelAdmin):
    list_display = ("date", "student", "subject", "teacher", "value", "comment")
    list_filter = ("value", "date", "subject", "teacher")
    search_fields = ("student__username", "student__last_name", "comment")


@admin.register(Notification)
class NotificationAdmin(admin.ModelAdmin):
    list_display = ("created_at", "user", "title", "is_read")
    list_filter = ("is_read", "created_at")
    search_fields = ("user__username", "title", "message")
