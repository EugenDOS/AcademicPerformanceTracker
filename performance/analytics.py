from django.db.models import Avg, Count, Q

from .models import Attendance, User
from .selectors import visible_attendance, visible_grades, visible_groups, visible_lessons, visible_subjects


def summary_for_user(user):
    grades = visible_grades(user)
    attendance = visible_attendance(user)
    absences = attendance.filter(status=Attendance.Status.ABSENT).count()
    return {
        "groups": visible_groups(user).count(),
        "subjects": visible_subjects(user).count(),
        "lessons": visible_lessons(user).count(),
        "grades": grades.count(),
        "attendance_records": attendance.count(),
        "average_grade": grades.aggregate(value=Avg("value"))["value"],
        "absences": absences,
        "unread_notifications": user.notifications.filter(is_read=False).count(),
    }


def subject_average_grades(user):
    return (
        visible_grades(user)
        .values("subject__id", "subject__name")
        .annotate(average=Avg("value"), count=Count("id"))
        .order_by("subject__name")
    )


def attendance_by_status(user):
    return (
        visible_attendance(user)
        .values("status")
        .annotate(count=Count("id"))
        .order_by("status")
    )


def problem_students(user):
    if user.is_student_role():
        students = User.objects.filter(id=user.id)
    else:
        students = User.objects.filter(role=User.Role.STUDENT)
        if user.is_teacher_role():
            students = students.filter(Q(grades__teacher=user) | Q(attendance_records__lesson__teacher=user))

    rows = (
        students.annotate(
            average_grade=Avg("grades__value"),
            absences=Count(
                "attendance_records",
                filter=Q(attendance_records__status=Attendance.Status.ABSENT),
            ),
        )
        .filter(Q(average_grade__lt=3.5) | Q(absences__gte=2))
        .distinct()
        .order_by("last_name", "username")
    )
    return rows


def full_analytics(user):
    return {
        "summary": summary_for_user(user),
        "subject_averages": list(subject_average_grades(user)),
        "attendance_by_status": list(attendance_by_status(user)),
        "problem_students": [
            {
                "id": student.id,
                "username": student.username,
                "full_name": student.get_full_name(),
                "group": student.group.name if student.group else None,
                "average_grade": student.average_grade,
                "absences": student.absences,
            }
            for student in problem_students(user)
        ],
    }
