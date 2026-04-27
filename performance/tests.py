from django.conf import settings
from django.contrib.auth import get_user_model
from django.core.management import call_command
from django.test import Client, TestCase, override_settings
from django.urls import reverse
from django.utils import timezone
from rest_framework.test import APIClient

from .analytics import full_analytics, problem_students
from .models import Attendance, Grade, Lesson, Notification, StudyGroup, Subject
from .serializers import AttendanceSerializer, GradeSerializer, LessonSerializer, SubjectSerializer


FAST_HASHERS = ["django.contrib.auth.hashers.MD5PasswordHasher"]


class TestDataMixin:
    def setUp(self):
        User = get_user_model()
        self.admin = User.objects.create_superuser(
            username="admin",
            password="AdminPass123!",
            role=User.Role.ADMIN,
            email="admin@example.com",
        )
        self.teacher = User.objects.create_user(
            username="teacher",
            password="TeacherPass123!",
            role=User.Role.TEACHER,
            first_name="Иван",
            last_name="Петров",
        )
        self.other_teacher = User.objects.create_user(
            username="other_teacher",
            password="TeacherPass123!",
            role=User.Role.TEACHER,
        )
        self.group = StudyGroup.objects.create(name="ИКБО-01-24", curator=self.teacher)
        self.other_group = StudyGroup.objects.create(name="ИКБО-02-24", curator=self.other_teacher)
        self.student = User.objects.create_user(
            username="student",
            password="StudentPass123!",
            role=User.Role.STUDENT,
            group=self.group,
            first_name="Анна",
            last_name="Сидорова",
            email="student@example.com",
        )
        self.other_student = User.objects.create_user(
            username="other",
            password="OtherPass123!",
            role=User.Role.STUDENT,
            group=self.group,
        )
        self.student_without_group = User.objects.create_user(
            username="nogroup",
            password="NoGroupPass123!",
            role=User.Role.STUDENT,
        )
        self.subject = Subject.objects.create(name="Базы данных", description="SQL")
        self.subject.teachers.add(self.teacher)
        self.other_subject = Subject.objects.create(name="Математика")
        self.other_subject.teachers.add(self.other_teacher)
        self.lesson = Lesson.objects.create(
            group=self.group,
            subject=self.subject,
            teacher=self.teacher,
            date=timezone.localdate(),
            topic="Нормализация таблиц",
        )
        self.other_lesson = Lesson.objects.create(
            group=self.other_group,
            subject=self.other_subject,
            teacher=self.other_teacher,
            date=timezone.localdate(),
            topic="Графы",
        )
        self.grade = Grade.objects.create(
            student=self.student,
            subject=self.subject,
            teacher=self.teacher,
            lesson=self.lesson,
            value=5,
            date=timezone.localdate(),
        )
        self.low_grade = Grade.objects.create(
            student=self.other_student,
            subject=self.subject,
            teacher=self.teacher,
            lesson=self.lesson,
            value=2,
            date=timezone.localdate(),
        )
        self.other_grade = Grade.objects.create(
            student=self.student,
            subject=self.other_subject,
            teacher=self.other_teacher,
            lesson=self.other_lesson,
            value=4,
            date=timezone.localdate(),
        )
        self.attendance = Attendance.objects.create(
            lesson=self.lesson,
            student=self.student,
            status=Attendance.Status.ABSENT,
        )
        Attendance.objects.create(
            lesson=self.lesson,
            student=self.other_student,
            status=Attendance.Status.ABSENT,
        )
        Attendance.objects.create(
            lesson=self.other_lesson,
            student=self.student,
            status=Attendance.Status.PRESENT,
        )
        self.notification = Notification.objects.create(
            user=self.student,
            title="Проверка",
            message="Тестовое уведомление",
        )
        self.api = APIClient()


@override_settings(PASSWORD_HASHERS=FAST_HASHERS)
class RoleApiTests(TestDataMixin, TestCase):
    def test_unauthenticated_api_access_is_denied(self):
        response = self.api.get("/api/grades/")

        self.assertIn(response.status_code, (401, 403))

    def test_admin_sees_all_grades_and_can_create_group(self):
        self.api.force_authenticate(self.admin)

        list_response = self.api.get("/api/grades/")
        create_response = self.api.post("/api/groups/", {"name": "ИКБО-03-24"}, format="json")

        self.assertEqual(list_response.status_code, 200)
        self.assertEqual(len(list_response.data), 3)
        self.assertEqual(create_response.status_code, 201)

    def test_student_sees_only_own_grades_and_attendance(self):
        self.api.force_authenticate(self.student)

        grades_response = self.api.get("/api/grades/")
        attendance_response = self.api.get("/api/attendance/")

        self.assertEqual(grades_response.status_code, 200)
        self.assertEqual({item["student"] for item in grades_response.data}, {self.student.id})
        self.assertEqual(attendance_response.status_code, 200)
        self.assertEqual({item["student"] for item in attendance_response.data}, {self.student.id})

    def test_student_cannot_write_grade_attendance_or_group(self):
        self.api.force_authenticate(self.student)

        grade_response = self.api.post(
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
        attendance_response = self.api.post(
            "/api/attendance/",
            {"student": self.student.id, "lesson": self.lesson.id, "status": Attendance.Status.PRESENT},
            format="json",
        )
        group_response = self.api.post("/api/groups/", {"name": "ИКБО-99-24"}, format="json")

        self.assertEqual(grade_response.status_code, 403)
        self.assertEqual(attendance_response.status_code, 403)
        self.assertEqual(group_response.status_code, 403)

    def test_teacher_can_create_own_lesson_grade_and_attendance(self):
        self.api.force_authenticate(self.teacher)

        lesson_response = self.api.post(
            "/api/lessons/",
            {
                "group": self.group.id,
                "subject": self.subject.id,
                "date": str(timezone.localdate()),
                "topic": "REST API",
            },
            format="json",
        )
        lesson_id = lesson_response.data["id"]
        grade_response = self.api.post(
            "/api/grades/",
            {
                "student": self.student.id,
                "subject": self.subject.id,
                "lesson": lesson_id,
                "value": 5,
                "date": str(timezone.localdate()),
            },
            format="json",
        )
        attendance_response = self.api.post(
            "/api/attendance/",
            {
                "student": self.student.id,
                "lesson": lesson_id,
                "status": Attendance.Status.PRESENT,
            },
            format="json",
        )

        self.assertEqual(lesson_response.status_code, 201)
        self.assertEqual(lesson_response.data["teacher"], self.teacher.id)
        self.assertEqual(grade_response.status_code, 201)
        self.assertEqual(grade_response.data["teacher"], self.teacher.id)
        self.assertEqual(attendance_response.status_code, 201)
        self.assertTrue(Notification.objects.filter(user=self.student, title="Новая оценка").exists())
        self.assertTrue(Notification.objects.filter(user=self.student, title="Посещаемость отмечена").exists())

    def test_teacher_cannot_write_other_teacher_objects(self):
        self.api.force_authenticate(self.teacher)
        foreign_lesson = Lesson.objects.create(
            group=self.group,
            subject=self.subject,
            teacher=self.other_teacher,
            date=timezone.localdate(),
            topic="Чужое занятие",
        )

        grade_create = self.api.post(
            "/api/grades/",
            {
                "student": self.student.id,
                "subject": self.subject.id,
                "lesson": foreign_lesson.id,
                "value": 5,
                "date": str(timezone.localdate()),
            },
            format="json",
        )
        attendance_create = self.api.post(
            "/api/attendance/",
            {
                "student": self.student.id,
                "lesson": foreign_lesson.id,
                "status": Attendance.Status.PRESENT,
            },
            format="json",
        )
        other_grade_update = self.api.patch(f"/api/grades/{self.other_grade.id}/", {"value": 2}, format="json")

        self.assertEqual(grade_create.status_code, 403)
        self.assertEqual(attendance_create.status_code, 403)
        self.assertEqual(other_grade_update.status_code, 404)
        self.other_grade.refresh_from_db()
        self.assertEqual(self.other_grade.value, 4)

    def test_teacher_cannot_create_admin_only_entities(self):
        self.api.force_authenticate(self.teacher)

        group_response = self.api.post("/api/groups/", {"name": "ИКБО-04-24"}, format="json")
        subject_response = self.api.post("/api/subjects/", {"name": "Физика"}, format="json")
        user_response = self.api.post(
            "/api/users/",
            {"username": "new_user", "role": "student", "password": "UserPass123!"},
            format="json",
        )

        self.assertEqual(group_response.status_code, 403)
        self.assertEqual(subject_response.status_code, 403)
        self.assertEqual(user_response.status_code, 403)

    def test_admin_can_update_grade_with_explicit_teacher(self):
        self.api.force_authenticate(self.admin)

        response = self.api.patch(
            f"/api/grades/{self.grade.id}/",
            {"value": 4, "teacher": self.teacher.id},
            format="json",
        )

        self.assertEqual(response.status_code, 200)
        self.grade.refresh_from_db()
        self.assertEqual(self.grade.value, 4)


@override_settings(PASSWORD_HASHERS=FAST_HASHERS)
class ProfileAndPasswordApiTests(TestDataMixin, TestCase):
    def test_profile_update_changes_allowed_fields_only(self):
        self.api.force_authenticate(self.student)

        response = self.api.patch(
            "/api/profile/",
            {
                "first_name": "Мария",
                "last_name": "Иванова",
                "email": "new@example.com",
                "role": "admin",
            },
            format="json",
        )

        self.assertEqual(response.status_code, 200)
        self.student.refresh_from_db()
        self.assertEqual(self.student.first_name, "Мария")
        self.assertEqual(self.student.email, "new@example.com")
        self.assertEqual(self.student.role, self.student.Role.STUDENT)

    def test_password_change_api_updates_password(self):
        self.api.force_authenticate(self.student)

        response = self.api.post(
            "/api/password/change/",
            {"old_password": "StudentPass123!", "new_password": "NewStudentPass123!"},
            format="json",
        )

        self.assertEqual(response.status_code, 200)
        self.student.refresh_from_db()
        self.assertTrue(self.student.check_password("NewStudentPass123!"))

    def test_password_change_rejects_wrong_old_password(self):
        self.api.force_authenticate(self.student)

        response = self.api.post(
            "/api/password/change/",
            {"old_password": "wrong", "new_password": "NewStudentPass123!"},
            format="json",
        )

        self.assertEqual(response.status_code, 400)

    def test_password_change_rejects_weak_password(self):
        self.api.force_authenticate(self.student)

        response = self.api.post(
            "/api/password/change/",
            {"old_password": "StudentPass123!", "new_password": "123"},
            format="json",
        )

        self.assertEqual(response.status_code, 400)


@override_settings(PASSWORD_HASHERS=FAST_HASHERS)
class NotificationApiTests(TestDataMixin, TestCase):
    def test_user_sees_only_own_notifications(self):
        Notification.objects.create(user=self.teacher, title="Teacher", message="Only teacher")
        self.api.force_authenticate(self.student)

        response = self.api.get("/api/notifications/")

        self.assertEqual(response.status_code, 200)
        self.assertEqual(len(response.data), 1)
        self.assertEqual(response.data[0]["title"], self.notification.title)

    def test_notification_can_be_marked_as_read(self):
        self.api.force_authenticate(self.student)

        response = self.api.post(f"/api/notifications/{self.notification.id}/mark_read/")

        self.assertEqual(response.status_code, 200)
        self.notification.refresh_from_db()
        self.assertTrue(self.notification.is_read)

    def test_user_cannot_read_other_user_notification(self):
        teacher_notification = Notification.objects.create(
            user=self.teacher,
            title="Teacher",
            message="Only teacher",
        )
        self.api.force_authenticate(self.student)

        response = self.api.get(f"/api/notifications/{teacher_notification.id}/")

        self.assertEqual(response.status_code, 404)


@override_settings(PASSWORD_HASHERS=FAST_HASHERS)
class AnalyticsAndExportTests(TestDataMixin, TestCase):
    def test_stats_contains_summary_subjects_attendance_and_problem_students(self):
        self.api.force_authenticate(self.teacher)

        response = self.api.get("/api/stats/")

        self.assertEqual(response.status_code, 200)
        self.assertEqual(response.data["summary"]["absences"], 2)
        self.assertTrue(response.data["subject_averages"])
        self.assertTrue(response.data["attendance_by_status"])
        self.assertTrue(response.data["problem_students"])

    def test_student_without_group_gets_empty_visible_learning_data(self):
        self.api.force_authenticate(self.student_without_group)

        response = self.api.get("/api/stats/")

        self.assertEqual(response.status_code, 200)
        self.assertEqual(response.data["summary"]["subjects"], 0)
        self.assertEqual(response.data["summary"]["lessons"], 0)
        self.assertEqual(response.data["summary"]["grades"], 0)

    def test_problem_students_detects_low_grade_or_absences(self):
        result = list(problem_students(self.teacher))

        self.assertIn(self.other_student, result)

    def test_full_analytics_has_stable_top_level_keys(self):
        result = full_analytics(self.admin)

        self.assertEqual(
            set(result.keys()),
            {"summary", "subject_averages", "attendance_by_status", "problem_students"},
        )

    def test_grades_export_returns_visible_csv(self):
        self.api.force_authenticate(self.teacher)

        response = self.api.get("/api/export/grades.csv")

        self.assertEqual(response.status_code, 200)
        self.assertIn("text/csv", response["Content-Type"])
        text = response.content.decode("utf-8-sig")
        self.assertIn("student", text)
        self.assertIn("Базы данных", text)
        self.assertNotIn("Математика", text)

    def test_attendance_export_returns_visible_csv(self):
        self.api.force_authenticate(self.teacher)

        response = self.api.get("/api/export/attendance.csv")

        self.assertEqual(response.status_code, 200)
        self.assertIn("text/csv", response["Content-Type"])
        text = response.content.decode("utf-8-sig")
        self.assertIn("status", text)
        self.assertIn("Базы данных", text)
        self.assertNotIn("Математика", text)


@override_settings(PASSWORD_HASHERS=FAST_HASHERS)
class SerializerValidationTests(TestDataMixin, TestCase):
    def test_subject_serializer_rejects_student_as_teacher(self):
        serializer = SubjectSerializer(
            data={
                "name": "Новый предмет",
                "description": "",
                "teachers": [self.student.id],
            }
        )

        self.assertFalse(serializer.is_valid())
        self.assertIn("teachers", serializer.errors)

    def test_lesson_serializer_rejects_non_teacher(self):
        serializer = LessonSerializer(
            data={
                "group": self.group.id,
                "subject": self.subject.id,
                "teacher": self.student.id,
                "date": str(timezone.localdate()),
                "topic": "Ошибка роли",
            }
        )

        self.assertFalse(serializer.is_valid())
        self.assertIn("teacher", serializer.errors)

    def test_grade_serializer_rejects_non_student(self):
        serializer = GradeSerializer(
            data={
                "student": self.teacher.id,
                "subject": self.subject.id,
                "teacher": self.teacher.id,
                "lesson": self.lesson.id,
                "value": 5,
                "date": str(timezone.localdate()),
            }
        )

        self.assertFalse(serializer.is_valid())
        self.assertIn("student", serializer.errors)

    def test_grade_serializer_rejects_subject_mismatch_with_lesson(self):
        serializer = GradeSerializer(
            data={
                "student": self.student.id,
                "subject": self.other_subject.id,
                "teacher": self.teacher.id,
                "lesson": self.lesson.id,
                "value": 5,
                "date": str(timezone.localdate()),
            }
        )

        self.assertFalse(serializer.is_valid())
        self.assertIn("non_field_errors", serializer.errors)

    def test_attendance_serializer_rejects_student_from_other_group(self):
        serializer = AttendanceSerializer(
            data={
                "student": self.student.id,
                "lesson": self.other_lesson.id,
                "status": Attendance.Status.PRESENT,
            }
        )

        self.assertFalse(serializer.is_valid())
        self.assertIn("non_field_errors", serializer.errors)


@override_settings(PASSWORD_HASHERS=FAST_HASHERS)
class WebViewTests(TestDataMixin, TestCase):
    def setUp(self):
        super().setUp()
        self.web = Client()
        self.web.login(username="student", password="StudentPass123!")

    def test_login_page_is_available_and_dashboard_requires_authentication(self):
        anonymous = Client()

        login_response = anonymous.get("/login/")
        dashboard_response = anonymous.get("/")

        self.assertEqual(login_response.status_code, 200)
        self.assertEqual(dashboard_response.status_code, 302)
        self.assertIn("/login/", dashboard_response["Location"])

    def test_login_flow_redirects_to_dashboard(self):
        anonymous = Client()

        response = anonymous.post(
            "/login/",
            {"username": "student", "password": "StudentPass123!"},
        )

        self.assertEqual(response.status_code, 302)
        self.assertEqual(response["Location"], "/")

    def test_main_web_pages_are_available_for_authenticated_user(self):
        for path in [
            "/",
            "/groups/",
            "/subjects/",
            "/lessons/",
            "/grades/",
            "/attendance/",
            "/profile/",
            "/profile/password/",
            "/notifications/",
            "/analytics/",
        ]:
            with self.subTest(path=path):
                response = self.web.get(path)
                self.assertEqual(response.status_code, 200)

    def test_profile_page_updates_user(self):
        response = self.web.post(
            "/profile/",
            {
                "first_name": "Нина",
                "last_name": "Сергеева",
                "email": "nina@example.com",
            },
        )

        self.assertEqual(response.status_code, 302)
        self.student.refresh_from_db()
        self.assertEqual(self.student.first_name, "Нина")
        self.assertEqual(self.student.email, "nina@example.com")

    def test_web_password_change_updates_password_and_keeps_session(self):
        response = self.web.post(
            "/profile/password/",
            {
                "old_password": "StudentPass123!",
                "new_password1": "ChangedStudentPass123!",
                "new_password2": "ChangedStudentPass123!",
            },
        )

        self.assertEqual(response.status_code, 302)
        self.student.refresh_from_db()
        self.assertTrue(self.student.check_password("ChangedStudentPass123!"))
        self.assertEqual(self.web.get("/profile/").status_code, 200)

    def test_notification_read_page_marks_only_own_notification(self):
        response = self.web.get(f"/notifications/{self.notification.id}/read/")

        self.assertEqual(response.status_code, 302)
        self.notification.refresh_from_db()
        self.assertTrue(self.notification.is_read)

    def test_other_user_notification_read_page_returns_404(self):
        teacher_notification = Notification.objects.create(
            user=self.teacher,
            title="Teacher",
            message="Only teacher",
        )

        response = self.web.get(f"/notifications/{teacher_notification.id}/read/")

        self.assertEqual(response.status_code, 404)

    def test_web_exports_return_csv(self):
        grades_response = self.web.get("/exports/grades.csv")
        attendance_response = self.web.get("/exports/attendance.csv")

        self.assertEqual(grades_response.status_code, 200)
        self.assertIn("text/csv", grades_response["Content-Type"])
        self.assertEqual(attendance_response.status_code, 200)
        self.assertIn("text/csv", attendance_response["Content-Type"])


class SwaggerAndSecurityTests(TestCase):
    def setUp(self):
        self.api = APIClient()

    def test_swagger_schema_contains_important_paths_tags_and_examples(self):
        response = self.api.get("/api/schema/?format=json")

        self.assertEqual(response.status_code, 200)
        schema = response.json()
        self.assertIn("/api/grades/", schema["paths"])
        self.assertIn("/api/stats/", schema["paths"])
        self.assertIn("/api/export/attendance.csv", schema["paths"])
        operation = schema["paths"]["/api/grades/"]["post"]
        self.assertEqual(operation["summary"], "Создать оценку")
        self.assertEqual(operation["tags"], ["Оценки"])
        content = operation["requestBody"]["content"]["application/json"]
        self.assertIn("examples", content)

    def test_swagger_ui_is_available(self):
        response = self.api.get("/api/docs/")

        self.assertEqual(response.status_code, 200)

    def test_security_settings_are_enabled(self):
        self.assertTrue(settings.SESSION_COOKIE_HTTPONLY)
        self.assertTrue(settings.CSRF_COOKIE_HTTPONLY)
        self.assertTrue(settings.SECURE_CONTENT_TYPE_NOSNIFF)
        self.assertEqual(settings.SECURE_REFERRER_POLICY, "same-origin")
        self.assertIn("django.contrib.auth.hashers.ScryptPasswordHasher", settings.PASSWORD_HASHERS)


class SeedDemoCommandTests(TestCase):
    @override_settings(PASSWORD_HASHERS=FAST_HASHERS)
    def test_seed_demo_creates_representative_data_and_is_idempotent(self):
        call_command("seed_demo", verbosity=0)
        call_command("seed_demo", verbosity=0)

        User = get_user_model()
        self.assertTrue(User.objects.filter(username="admin", role=User.Role.ADMIN).exists())
        self.assertTrue(User.objects.filter(username="teacher", role=User.Role.TEACHER).exists())
        self.assertGreaterEqual(User.objects.filter(role=User.Role.STUDENT).count(), 4)
        self.assertGreaterEqual(StudyGroup.objects.count(), 2)
        self.assertGreaterEqual(Subject.objects.count(), 3)
        self.assertGreaterEqual(Lesson.objects.count(), 4)
        self.assertGreaterEqual(Grade.objects.count(), 8)
        self.assertGreaterEqual(Attendance.objects.count(), 10)
        self.assertGreaterEqual(Notification.objects.count(), 4)
        self.assertTrue(User.objects.get(username="student").check_password("student12345"))
