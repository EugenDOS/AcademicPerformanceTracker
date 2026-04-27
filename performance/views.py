from django.contrib.auth.decorators import login_required
from django.contrib.auth.forms import PasswordChangeForm
from django.contrib.auth import update_session_auth_hash
from django.contrib import messages
from django.shortcuts import get_object_or_404, redirect, render

from .analytics import full_analytics, summary_for_user
from .exports import export_attendance_csv, export_grades_csv
from .selectors import (
    visible_attendance,
    visible_grades,
    visible_groups,
    visible_lessons,
    visible_notifications,
    visible_subjects,
)
from .services import mark_notification_read


@login_required
def dashboard(request):
    return render(request, "performance/dashboard.html", summary_for_user(request.user))


@login_required
def groups_page(request):
    groups = visible_groups(request.user).select_related("curator")
    return render(request, "performance/groups.html", {"groups": groups})


@login_required
def subjects_page(request):
    subjects = visible_subjects(request.user).prefetch_related("teachers")
    return render(request, "performance/subjects.html", {"subjects": subjects})


@login_required
def lessons_page(request):
    lessons = visible_lessons(request.user).select_related("group", "subject", "teacher")
    return render(request, "performance/lessons.html", {"lessons": lessons})


@login_required
def grades_page(request):
    grades = visible_grades(request.user).select_related("student", "subject", "teacher", "lesson")
    return render(request, "performance/grades.html", {"grades": grades})


@login_required
def attendance_page(request):
    attendance = visible_attendance(request.user).select_related(
        "lesson",
        "lesson__group",
        "lesson__subject",
        "student",
    )
    return render(request, "performance/attendance.html", {"attendance": attendance})


@login_required
def profile_page(request):
    if request.method == "POST":
        user = request.user
        user.first_name = request.POST.get("first_name", "")
        user.last_name = request.POST.get("last_name", "")
        user.email = request.POST.get("email", "")
        user.save(update_fields=["first_name", "last_name", "email"])
        messages.success(request, "Профиль обновлен.")
        return redirect("profile")
    return render(request, "performance/profile.html")


@login_required
def password_change_page(request):
    form = PasswordChangeForm(request.user, request.POST or None)
    if request.method == "POST" and form.is_valid():
        user = form.save()
        update_session_auth_hash(request, user)
        messages.success(request, "Пароль изменен.")
        return redirect("profile")
    return render(request, "performance/password_change.html", {"form": form})


@login_required
def notifications_page(request):
    notifications = visible_notifications(request.user)
    return render(request, "performance/notifications.html", {"notifications": notifications})


@login_required
def notification_read_page(request, pk):
    notification = get_object_or_404(visible_notifications(request.user), pk=pk)
    mark_notification_read(notification)
    return redirect("notifications")


@login_required
def analytics_page(request):
    return render(request, "performance/analytics.html", full_analytics(request.user))


@login_required
def export_grades_page(request):
    return export_grades_csv(request.user)


@login_required
def export_attendance_page(request):
    return export_attendance_csv(request.user)
