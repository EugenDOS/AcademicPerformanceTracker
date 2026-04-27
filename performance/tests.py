from django.contrib.auth import get_user_model
from django.test import TestCase
from django.utils import timezone
from rest_framework.test import APIClient

from .models import Grade, Lesson, StudyGroup, Subject


class RoleApiTests(TestCase):
    def setUp(self):
        User = get_user_model()
        self.teacher = User.objects.create_user(
            username="teacher",
            password="pass",
            role=User.Role.TEACHER,
        )
        self.group = StudyGroup.objects.create(name="ИКБО-01-24", curator=self.teacher)
        self.student = User.objects.create_user(
            username="student",
            password="pass",
            role=User.Role.STUDENT,
            group=self.group,
        )
        self.other_student = User.objects.create_user(
            username="other",
            password="pass",
            role=User.Role.STUDENT,
            group=self.group,
        )
        self.subject = Subject.objects.create(name="Базы данных")
        self.subject.teachers.add(self.teacher)
        self.lesson = Lesson.objects.create(
            group=self.group,
            subject=self.subject,
            teacher=self.teacher,
            date=timezone.localdate(),
            topic="Нормализация таблиц",
        )
        Grade.objects.create(
            student=self.student,
            subject=self.subject,
            teacher=self.teacher,
            lesson=self.lesson,
            value=5,
            date=timezone.localdate(),
        )
        Grade.objects.create(
            student=self.other_student,
            subject=self.subject,
            teacher=self.teacher,
            lesson=self.lesson,
            value=4,
            date=timezone.localdate(),
        )
        self.client = APIClient()

    def test_student_sees_only_own_grades(self):
        self.client.force_authenticate(self.student)

        response = self.client.get("/api/grades/")

        self.assertEqual(response.status_code, 200)
        self.assertEqual(len(response.data), 1)
        self.assertEqual(response.data[0]["student"], self.student.id)

    def test_teacher_can_create_grade_without_teacher_field(self):
        self.client.force_authenticate(self.teacher)

        response = self.client.post(
            "/api/grades/",
            {
                "student": self.student.id,
                "subject": self.subject.id,
                "lesson": self.lesson.id,
                "value": 5,
                "date": str(timezone.localdate()),
            },
            format="json",
        )

        self.assertEqual(response.status_code, 201)
        self.assertEqual(response.data["teacher"], self.teacher.id)

    def test_student_cannot_create_grade(self):
        self.client.force_authenticate(self.student)

        response = self.client.post(
            "/api/grades/",
            {
                "student": self.student.id,
                "subject": self.subject.id,
                "lesson": self.lesson.id,
                "value": 5,
                "date": str(timezone.localdate()),
            },
            format="json",
        )

        self.assertEqual(response.status_code, 403)
