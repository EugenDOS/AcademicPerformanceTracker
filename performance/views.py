from django.contrib.auth.decorators import login_required
from django.db.models import Avg
from django.shortcuts import render

from .selectors import (
    visible_attendance,
    visible_grades,
    visible_groups,
    visible_lessons,
    visible_subjects,
)


@login_required
def dashboard(request):
    grades = visible_grades(request.user)
    average_grade = grades.aggregate(value=Avg("value"))["value"]
    context = {
        "group_count": visible_groups(request.user).count(),
        "subject_count": visible_subjects(request.user).count(),
        "lesson_count": visible_lessons(request.user).count(),
        "grade_count": grades.count(),
        "attendance_count": visible_attendance(request.user).count(),
        "average_grade": average_grade,
    }
    return render(request, "performance/dashboard.html", context)


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
