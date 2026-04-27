from django.contrib.auth import get_user_model
from django.core.management.base import BaseCommand
from django.utils import timezone

from performance.models import Attendance, Grade, Lesson, StudyGroup, Subject


class Command(BaseCommand):
    help = "Создает минимальные демонстрационные данные."

    def handle(self, *args, **options):
        User = get_user_model()

        self._user(
            User,
            username="admin",
            password="admin12345",
            role=User.Role.ADMIN,
            is_staff=True,
            is_superuser=True,
            first_name="Администратор",
        )
        teacher = self._user(
            User,
            username="teacher",
            password="teacher12345",
            role=User.Role.TEACHER,
            first_name="Иван",
            last_name="Петров",
        )
        group, _ = StudyGroup.objects.update_or_create(
            name="ИКБО-01-24",
            defaults={"curator": teacher},
        )
        student = self._user(
            User,
            username="student",
            password="student12345",
            role=User.Role.STUDENT,
            group=group,
            first_name="Анна",
            last_name="Сидорова",
        )

        subject, _ = Subject.objects.update_or_create(
            name="Базы данных",
            defaults={"description": "Основы проектирования баз данных"},
        )
        subject.teachers.set([teacher])

        today = timezone.localdate()
        lesson, _ = Lesson.objects.update_or_create(
            group=group,
            subject=subject,
            teacher=teacher,
            date=today,
            defaults={"topic": "Нормализация таблиц"},
        )
        Attendance.objects.update_or_create(
            lesson=lesson,
            student=student,
            defaults={"status": Attendance.Status.PRESENT},
        )
        Grade.objects.update_or_create(
            student=student,
            subject=subject,
            teacher=teacher,
            lesson=lesson,
            date=today,
            defaults={"value": 5, "comment": "Практическая работа"},
        )

        self.stdout.write(self.style.SUCCESS("Демо-данные созданы."))
        self.stdout.write("admin / admin12345")
        self.stdout.write("teacher / teacher12345")
        self.stdout.write("student / student12345")

    def _user(self, User, username, password, **defaults):
        user, _ = User.objects.update_or_create(username=username, defaults=defaults)
        user.set_password(password)
        user.save()
        return user
