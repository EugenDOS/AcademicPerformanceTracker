from django.db.models import Q

from .models import Attendance, Grade, Lesson, Notification, StudyGroup, Subject, User


def is_admin(user):
    return user.is_authenticated and user.is_admin_role()


def is_teacher(user):
    return user.is_authenticated and user.is_teacher_role()


def is_student(user):
    return user.is_authenticated and user.is_student_role()


def visible_users(user):
    if is_admin(user):
        return User.objects.all()
    if is_teacher(user):
        return User.objects.filter(Q(id=user.id) | Q(role=User.Role.STUDENT))
    if is_student(user):
        return User.objects.filter(id=user.id)
    return User.objects.none()


def visible_groups(user):
    if is_admin(user) or is_teacher(user):
        return StudyGroup.objects.all()
    if is_student(user) and user.group_id:
        return StudyGroup.objects.filter(id=user.group_id)
    return StudyGroup.objects.none()


def visible_subjects(user):
    if is_admin(user) or is_teacher(user):
        return Subject.objects.all()
    if is_student(user) and user.group_id:
        return Subject.objects.filter(
            Q(lessons__group_id=user.group_id) | Q(grades__student=user)
        ).distinct()
    return Subject.objects.none()


def visible_lessons(user):
    if is_admin(user):
        return Lesson.objects.all()
    if is_teacher(user):
        return Lesson.objects.filter(teacher=user)
    if is_student(user) and user.group_id:
        return Lesson.objects.filter(group_id=user.group_id)
    return Lesson.objects.none()


def visible_attendance(user):
    if is_admin(user):
        return Attendance.objects.all()
    if is_teacher(user):
        return Attendance.objects.filter(lesson__teacher=user)
    if is_student(user):
        return Attendance.objects.filter(student=user)
    return Attendance.objects.none()


def visible_grades(user):
    if is_admin(user):
        return Grade.objects.all()
    if is_teacher(user):
        return Grade.objects.filter(teacher=user)
    if is_student(user):
        return Grade.objects.filter(student=user)
    return Grade.objects.none()


def visible_notifications(user):
    if not user.is_authenticated:
        return Notification.objects.none()
    return Notification.objects.filter(user=user)
