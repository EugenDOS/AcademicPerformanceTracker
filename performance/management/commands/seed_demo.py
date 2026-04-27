from datetime import timedelta

from django.contrib.auth import get_user_model
from django.core.management.base import BaseCommand
from django.utils import timezone

from performance.models import Attendance, Grade, Lesson, Notification, StudyGroup, Subject


class Command(BaseCommand):
    help = "Создает демонстрационные данные для защиты и проверки проекта."

    def handle(self, *args, **options):
        User = get_user_model()

        admin = self._user(
            User,
            username="admin",
            password="admin12345",
            role=User.Role.ADMIN,
            is_staff=True,
            is_superuser=True,
            first_name="Администратор",
            email="admin@example.com",
        )
        teacher = self._user(
            User,
            username="teacher",
            password="teacher12345",
            role=User.Role.TEACHER,
            first_name="Иван",
            last_name="Петров",
            email="teacher@example.com",
        )
        second_teacher = self._user(
            User,
            username="teacher_math",
            password="teacher12345",
            role=User.Role.TEACHER,
            first_name="Мария",
            last_name="Орлова",
            email="math@example.com",
        )

        group_a, _ = StudyGroup.objects.update_or_create(
            name="ИКБО-01-24",
            defaults={"curator": teacher},
        )
        group_b, _ = StudyGroup.objects.update_or_create(
            name="ИКБО-02-24",
            defaults={"curator": second_teacher},
        )

        students = [
            self._user(User, "student", "student12345", role=User.Role.STUDENT, group=group_a, first_name="Анна", last_name="Сидорова", email="student@example.com"),
            self._user(User, "student_good", "student12345", role=User.Role.STUDENT, group=group_a, first_name="Павел", last_name="Никитин"),
            self._user(User, "student_risk", "student12345", role=User.Role.STUDENT, group=group_a, first_name="Олег", last_name="Зайцев"),
            self._user(User, "student_b", "student12345", role=User.Role.STUDENT, group=group_b, first_name="Елена", last_name="Кузнецова"),
        ]

        db_subject = self._subject("Базы данных", "Основы проектирования баз данных", [teacher])
        web_subject = self._subject("Веб-разработка", "Backend и REST API на Django", [teacher])
        math_subject = self._subject("Дискретная математика", "Множества, графы и логика", [second_teacher])

        today = timezone.localdate()
        lessons = [
            self._lesson(group_a, db_subject, teacher, today - timedelta(days=5), "Нормализация таблиц"),
            self._lesson(group_a, db_subject, teacher, today - timedelta(days=3), "SQL-запросы"),
            self._lesson(group_a, web_subject, teacher, today - timedelta(days=1), "REST API"),
            self._lesson(group_b, math_subject, second_teacher, today - timedelta(days=2), "Графы"),
        ]

        self._attendance(lessons[0], students[0], Attendance.Status.PRESENT)
        self._attendance(lessons[0], students[1], Attendance.Status.PRESENT)
        self._attendance(lessons[0], students[2], Attendance.Status.ABSENT, "Нет справки")
        self._attendance(lessons[1], students[0], Attendance.Status.LATE, "Опоздание 10 минут")
        self._attendance(lessons[1], students[1], Attendance.Status.PRESENT)
        self._attendance(lessons[1], students[2], Attendance.Status.ABSENT, "Нет справки")
        self._attendance(lessons[2], students[0], Attendance.Status.PRESENT)
        self._attendance(lessons[2], students[1], Attendance.Status.EXCUSED, "Олимпиада")
        self._attendance(lessons[2], students[2], Attendance.Status.PRESENT)
        self._attendance(lessons[3], students[3], Attendance.Status.PRESENT)

        self._grade(students[0], db_subject, teacher, lessons[0], 5, "Практическая работа")
        self._grade(students[0], db_subject, teacher, lessons[1], 4, "SQL-запросы")
        self._grade(students[0], web_subject, teacher, lessons[2], 5, "API endpoint")
        self._grade(students[1], db_subject, teacher, lessons[0], 5, "Отлично")
        self._grade(students[1], web_subject, teacher, lessons[2], 4, "Хорошая работа")
        self._grade(students[2], db_subject, teacher, lessons[0], 3, "Нужно повторить теорию")
        self._grade(students[2], db_subject, teacher, lessons[1], 2, "Работа не сдана")
        self._grade(students[3], math_subject, second_teacher, lessons[3], 4, "Зачтено")

        Notification.objects.filter(user__in=[admin, teacher, second_teacher, *students]).delete()
        self._notification(students[0], "Новая оценка", "По базам данных выставлена оценка 5.")
        self._notification(students[2], "Нужно внимание", "Есть пропуски и низкая средняя оценка.")
        self._notification(teacher, "Аналитика обновлена", "В группе ИКБО-01-24 появился студент зоны риска.")
        self._notification(admin, "Демо-данные", "Демонстрационный набор успешно создан.")

        self.stdout.write(self.style.SUCCESS("Демо-данные созданы."))
        self.stdout.write("admin / admin12345")
        self.stdout.write("teacher / teacher12345")
        self.stdout.write("teacher_math / teacher12345")
        self.stdout.write("student / student12345")

    def _user(self, User, username, password, **defaults):
        user, _ = User.objects.update_or_create(username=username, defaults=defaults)
        user.set_password(password)
        user.save()
        return user

    def _subject(self, name, description, teachers):
        subject, _ = Subject.objects.update_or_create(name=name, defaults={"description": description})
        subject.teachers.set(teachers)
        return subject

    def _lesson(self, group, subject, teacher, date, topic):
        lesson, _ = Lesson.objects.update_or_create(
            group=group,
            subject=subject,
            teacher=teacher,
            date=date,
            defaults={"topic": topic},
        )
        return lesson

    def _attendance(self, lesson, student, status, comment=""):
        Attendance.objects.update_or_create(
            lesson=lesson,
            student=student,
            defaults={"status": status, "comment": comment},
        )

    def _grade(self, student, subject, teacher, lesson, value, comment=""):
        Grade.objects.update_or_create(
            student=student,
            subject=subject,
            teacher=teacher,
            lesson=lesson,
            date=lesson.date,
            defaults={"value": value, "comment": comment},
        )

    def _notification(self, user, title, message):
        Notification.objects.create(user=user, title=title, message=message)
