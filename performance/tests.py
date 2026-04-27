from django.contrib.auth import get_user_model
from django.test import TestCase
from django.utils import timezone
from rest_framework.test import APIClient

from .models import Attendance, Grade, Lesson, Notification, StudyGroup, Subject


class RoleApiTests(TestCase):
    def setUp(self):
        User = get_user_model()
        self.teacher = User.objects.create_user(
            username="teacher",
            password="TeacherPass123!",
            role=User.Role.TEACHER,
        )
        self.group = StudyGroup.objects.create(name="ИКБО-01-24", curator=self.teacher)
        self.student = User.objects.create_user(
            username="student",
            password="StudentPass123!",
            role=User.Role.STUDENT,
            group=self.group,
        )
        self.other_student = User.objects.create_user(
            username="other",
            password="OtherPass123!",
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
        self.old_grade = Grade.objects.create(
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
        Attendance.objects.create(
            lesson=self.lesson,
            student=self.student,
            status=Attendance.Status.ABSENT,
        )
        Attendance.objects.create(
            lesson=self.lesson,
            student=self.other_student,
            status=Attendance.Status.PRESENT,
        )
        self.client = APIClient()

    def test_student_sees_only_own_grades(self):
        self.client.force_authenticate(self.student)

        response = self.client.get("/api/grades/")

        self.assertEqual(response.status_code, 200)
        self.assertEqual(len(response.data), 1)
        self.assertEqual(response.data[0]["student"], self.student.id)

    def test_teacher_can_create_grade_without_teacher_field_and_student_gets_notification(self):
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
        self.assertTrue(Notification.objects.filter(user=self.student, title="Новая оценка").exists())

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

    def test_stats_contains_absences_and_subject_average(self):
        self.client.force_authenticate(self.student)

        response = self.client.get("/api/stats/")

        self.assertEqual(response.status_code, 200)
        self.assertEqual(response.data["summary"]["absences"], 1)
        self.assertEqual(response.data["subject_averages"][0]["subject__name"], self.subject.name)

    def test_notification_can_be_marked_as_read(self):
        notification = Notification.objects.create(
            user=self.student,
            title="Проверка",
            message="Тестовое уведомление",
        )
        self.client.force_authenticate(self.student)

        response = self.client.post(f"/api/notifications/{notification.id}/mark_read/")

        self.assertEqual(response.status_code, 200)
        notification.refresh_from_db()
        self.assertTrue(notification.is_read)

    def test_password_change_api_updates_password(self):
        self.client.force_authenticate(self.student)

        response = self.client.post(
            "/api/password/change/",
            {
                "old_password": "StudentPass123!",
                "new_password": "NewStudentPass123!",
            },
            format="json",
        )

        self.assertEqual(response.status_code, 200)
        self.student.refresh_from_db()
        self.assertTrue(self.student.check_password("NewStudentPass123!"))

    def test_grades_export_returns_csv(self):
        self.client.force_authenticate(self.teacher)

        response = self.client.get("/api/export/grades.csv")

        self.assertEqual(response.status_code, 200)
        self.assertIn("text/csv", response["Content-Type"])
        self.assertIn("student", response.content.decode("utf-8"))

    def test_swagger_schema_is_available(self):
        response = self.client.get("/api/schema/")

        self.assertEqual(response.status_code, 200)
