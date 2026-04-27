from .models import Attendance, Grade, Notification


def create_notification(user, title, message):
    return Notification.objects.create(
        user=user,
        title=title,
        message=message,
    )


def mark_notification_read(notification):
    notification.is_read = True
    notification.save(update_fields=["is_read"])
    return notification


def save_grade(*, student, subject, teacher, date, value, lesson=None, comment=""):
    grade = Grade.objects.create(
        student=student,
        subject=subject,
        teacher=teacher,
        lesson=lesson,
        value=value,
        date=date,
        comment=comment,
    )
    create_notification(
        student,
        "Новая оценка",
        f"По предмету {subject} выставлена оценка {value}.",
    )
    return grade


def update_grade(grade, **values):
    for field, value in values.items():
        setattr(grade, field, value)
    grade.save()
    create_notification(
        grade.student,
        "Оценка обновлена",
        f"Оценка по предмету {grade.subject} обновлена: {grade.value}.",
    )
    return grade


def save_attendance(*, lesson, student, status, comment=""):
    attendance = Attendance.objects.create(
        lesson=lesson,
        student=student,
        status=status,
        comment=comment,
    )
    create_notification(
        student,
        "Посещаемость отмечена",
        f"По занятию {lesson} указан статус: {attendance.get_status_display()}.",
    )
    return attendance


def update_attendance(attendance, **values):
    for field, value in values.items():
        setattr(attendance, field, value)
    attendance.save()
    create_notification(
        attendance.student,
        "Посещаемость обновлена",
        f"По занятию {attendance.lesson} указан статус: {attendance.get_status_display()}.",
    )
    return attendance
