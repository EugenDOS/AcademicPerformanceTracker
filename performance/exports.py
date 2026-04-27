import csv

from django.http import HttpResponse

from .selectors import visible_attendance, visible_grades


def csv_response(filename):
    response = HttpResponse(content_type="text/csv; charset=utf-8")
    response["Content-Disposition"] = f'attachment; filename="{filename}"'
    response.write("\ufeff")
    return response


def export_grades_csv(user):
    response = csv_response("grades.csv")
    writer = csv.writer(response)
    writer.writerow(["date", "student", "group", "subject", "teacher", "value", "comment"])
    for grade in visible_grades(user).select_related("student", "student__group", "subject", "teacher"):
        writer.writerow(
            [
                grade.date,
                grade.student.get_full_name() or grade.student.username,
                grade.student.group.name if grade.student.group else "",
                grade.subject.name,
                grade.teacher.get_full_name() or grade.teacher.username,
                grade.value,
                grade.comment,
            ]
        )
    return response


def export_attendance_csv(user):
    response = csv_response("attendance.csv")
    writer = csv.writer(response)
    writer.writerow(["date", "student", "group", "subject", "status", "comment"])
    for item in visible_attendance(user).select_related("student", "lesson", "lesson__group", "lesson__subject"):
        writer.writerow(
            [
                item.lesson.date,
                item.student.get_full_name() or item.student.username,
                item.lesson.group.name,
                item.lesson.subject.name,
                item.get_status_display(),
                item.comment,
            ]
        )
    return response
