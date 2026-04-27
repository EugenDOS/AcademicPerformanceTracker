from django.contrib.auth import update_session_auth_hash
from drf_spectacular.types import OpenApiTypes
from drf_spectacular.utils import OpenApiExample, OpenApiResponse, extend_schema, extend_schema_view
from rest_framework import serializers, viewsets
from rest_framework.decorators import action, api_view, permission_classes
from rest_framework.exceptions import PermissionDenied
from rest_framework.permissions import IsAuthenticated
from rest_framework.response import Response

from .analytics import full_analytics
from .exports import export_attendance_csv, export_grades_csv
from .models import Attendance, Grade, Lesson, Notification, StudyGroup, Subject, User
from .permissions import RolePermission
from .selectors import (
    is_admin,
    is_teacher,
    visible_attendance,
    visible_grades,
    visible_groups,
    visible_lessons,
    visible_notifications,
    visible_subjects,
    visible_users,
)
from .serializers import (
    AttendanceSerializer,
    GradeSerializer,
    LessonSerializer,
    NotificationSerializer,
    PasswordChangeSerializer,
    ProfileSerializer,
    StudyGroupSerializer,
    SubjectSerializer,
    UserSerializer,
)
from .services import mark_notification_read, save_attendance, save_grade, update_attendance, update_grade


class BaseRoleViewSet(viewsets.ModelViewSet):
    permission_classes = [RolePermission]
    teacher_can_write = False

    def teacher_owns_object(self, obj, teacher):
        return False


@extend_schema_view(
    list=extend_schema(summary="Список пользователей", tags=["Пользователи"]),
    retrieve=extend_schema(summary="Пользователь по ID", tags=["Пользователи"]),
    create=extend_schema(summary="Создать пользователя", tags=["Пользователи"]),
    update=extend_schema(summary="Обновить пользователя", tags=["Пользователи"]),
    partial_update=extend_schema(summary="Частично обновить пользователя", tags=["Пользователи"]),
    destroy=extend_schema(summary="Удалить пользователя", tags=["Пользователи"]),
)
class UserViewSet(BaseRoleViewSet):
    serializer_class = UserSerializer

    def get_queryset(self):
        return visible_users(self.request.user).select_related("group")


@extend_schema_view(
    list=extend_schema(summary="Список учебных групп", tags=["Группы"]),
    retrieve=extend_schema(summary="Учебная группа по ID", tags=["Группы"]),
    create=extend_schema(summary="Создать учебную группу", tags=["Группы"]),
    update=extend_schema(summary="Обновить учебную группу", tags=["Группы"]),
    partial_update=extend_schema(summary="Частично обновить учебную группу", tags=["Группы"]),
    destroy=extend_schema(summary="Удалить учебную группу", tags=["Группы"]),
)
class StudyGroupViewSet(BaseRoleViewSet):
    serializer_class = StudyGroupSerializer

    def get_queryset(self):
        return visible_groups(self.request.user).select_related("curator")


@extend_schema_view(
    list=extend_schema(summary="Список предметов", tags=["Предметы"]),
    retrieve=extend_schema(summary="Предмет по ID", tags=["Предметы"]),
    create=extend_schema(summary="Создать предмет", tags=["Предметы"]),
    update=extend_schema(summary="Обновить предмет", tags=["Предметы"]),
    partial_update=extend_schema(summary="Частично обновить предмет", tags=["Предметы"]),
    destroy=extend_schema(summary="Удалить предмет", tags=["Предметы"]),
)
class SubjectViewSet(BaseRoleViewSet):
    serializer_class = SubjectSerializer

    def get_queryset(self):
        return visible_subjects(self.request.user).prefetch_related("teachers")


@extend_schema_view(
    list=extend_schema(summary="Список занятий", tags=["Занятия"]),
    retrieve=extend_schema(summary="Занятие по ID", tags=["Занятия"]),
    create=extend_schema(
        summary="Создать занятие",
        tags=["Занятия"],
        examples=[
            OpenApiExample(
                "Пример",
                value={"group": 1, "subject": 1, "date": "2026-04-27", "topic": "Практическое занятие"},
                request_only=True,
            )
        ],
    ),
    update=extend_schema(summary="Обновить занятие", tags=["Занятия"]),
    partial_update=extend_schema(summary="Частично обновить занятие", tags=["Занятия"]),
    destroy=extend_schema(summary="Удалить занятие", tags=["Занятия"]),
)
class LessonViewSet(BaseRoleViewSet):
    serializer_class = LessonSerializer
    teacher_can_write = True

    def get_queryset(self):
        return visible_lessons(self.request.user).select_related("group", "subject", "teacher")

    def teacher_owns_object(self, obj, teacher):
        return obj.teacher_id == teacher.id

    def perform_create(self, serializer):
        user = self.request.user
        if is_teacher(user):
            serializer.save(teacher=user)
            return
        if is_admin(user) and not serializer.validated_data.get("teacher"):
            raise serializers.ValidationError({"teacher": "Укажите преподавателя."})
        serializer.save()

    def perform_update(self, serializer):
        user = self.request.user
        if is_teacher(user):
            serializer.save(teacher=user)
            return
        serializer.save()


@extend_schema_view(
    list=extend_schema(summary="Список записей посещаемости", tags=["Посещаемость"]),
    retrieve=extend_schema(summary="Запись посещаемости по ID", tags=["Посещаемость"]),
    create=extend_schema(
        summary="Создать запись посещаемости",
        tags=["Посещаемость"],
        examples=[
            OpenApiExample(
                "Пример",
                value={"lesson": 1, "student": 3, "status": "present", "comment": ""},
                request_only=True,
            )
        ],
    ),
    update=extend_schema(summary="Обновить запись посещаемости", tags=["Посещаемость"]),
    partial_update=extend_schema(summary="Частично обновить запись посещаемости", tags=["Посещаемость"]),
    destroy=extend_schema(summary="Удалить запись посещаемости", tags=["Посещаемость"]),
)
class AttendanceViewSet(BaseRoleViewSet):
    serializer_class = AttendanceSerializer
    teacher_can_write = True

    def get_queryset(self):
        return visible_attendance(self.request.user).select_related(
            "lesson",
            "lesson__group",
            "lesson__subject",
            "lesson__teacher",
            "student",
        )

    def teacher_owns_object(self, obj, teacher):
        return obj.lesson.teacher_id == teacher.id

    def _check_lesson_for_teacher(self, lesson):
        user = self.request.user
        if is_teacher(user) and lesson.teacher_id != user.id:
            raise PermissionDenied("Преподаватель может менять посещаемость только по своим занятиям.")

    def perform_create(self, serializer):
        self._check_lesson_for_teacher(serializer.validated_data["lesson"])
        serializer.instance = save_attendance(**serializer.validated_data)

    def perform_update(self, serializer):
        attendance = self.get_object()
        lesson = serializer.validated_data.get("lesson") or attendance.lesson
        self._check_lesson_for_teacher(lesson)
        serializer.instance = update_attendance(attendance, **serializer.validated_data)


@extend_schema_view(
    list=extend_schema(summary="Список оценок", tags=["Оценки"]),
    retrieve=extend_schema(summary="Оценка по ID", tags=["Оценки"]),
    create=extend_schema(
        summary="Создать оценку",
        tags=["Оценки"],
        examples=[
            OpenApiExample(
                "Пример",
                value={"student": 3, "subject": 1, "lesson": 1, "value": 5, "date": "2026-04-27", "comment": "Работа на занятии"},
                request_only=True,
            )
        ],
    ),
    update=extend_schema(summary="Обновить оценку", tags=["Оценки"]),
    partial_update=extend_schema(summary="Частично обновить оценку", tags=["Оценки"]),
    destroy=extend_schema(summary="Удалить оценку", tags=["Оценки"]),
)
class GradeViewSet(BaseRoleViewSet):
    serializer_class = GradeSerializer
    teacher_can_write = True

    def get_queryset(self):
        return visible_grades(self.request.user).select_related(
            "student",
            "subject",
            "teacher",
            "lesson",
            "lesson__group",
        )

    def teacher_owns_object(self, obj, teacher):
        return obj.teacher_id == teacher.id

    def _check_lesson_for_teacher(self, lesson):
        user = self.request.user
        if lesson and is_teacher(user) and lesson.teacher_id != user.id:
            raise PermissionDenied("Преподаватель может ставить оценки только по своим занятиям.")

    def perform_create(self, serializer):
        user = self.request.user
        lesson = serializer.validated_data.get("lesson")
        self._check_lesson_for_teacher(lesson)
        if is_teacher(user):
            serializer.validated_data["teacher"] = user
            serializer.instance = save_grade(**serializer.validated_data)
            return
        if is_admin(user) and not serializer.validated_data.get("teacher"):
            raise serializers.ValidationError({"teacher": "Укажите преподавателя."})
        serializer.instance = save_grade(**serializer.validated_data)

    def perform_update(self, serializer):
        user = self.request.user
        grade = self.get_object()
        lesson = serializer.validated_data.get("lesson") or grade.lesson
        self._check_lesson_for_teacher(lesson)
        if is_teacher(user):
            serializer.validated_data["teacher"] = user
            serializer.instance = update_grade(grade, **serializer.validated_data)
            return
        serializer.instance = update_grade(grade, **serializer.validated_data)


@extend_schema_view(
    list=extend_schema(summary="Список уведомлений текущего пользователя", tags=["Уведомления"]),
    retrieve=extend_schema(summary="Уведомление по ID", tags=["Уведомления"]),
)
class NotificationViewSet(viewsets.ReadOnlyModelViewSet):
    serializer_class = NotificationSerializer
    permission_classes = [IsAuthenticated]

    def get_queryset(self):
        return visible_notifications(self.request.user)

    @extend_schema(summary="Отметить уведомление прочитанным", tags=["Уведомления"])
    @action(detail=True, methods=["post"])
    def mark_read(self, request, pk=None):
        notification = mark_notification_read(self.get_object())
        return Response(self.get_serializer(notification).data)


@extend_schema(summary="Текущий пользователь", responses=ProfileSerializer, tags=["Профиль"])
@api_view(["GET"])
@permission_classes([IsAuthenticated])
def me(request):
    return Response(ProfileSerializer(request.user).data)


@extend_schema(
    summary="Обновить профиль текущего пользователя",
    request=ProfileSerializer,
    responses=ProfileSerializer,
    tags=["Профиль"],
)
@api_view(["PATCH"])
@permission_classes([IsAuthenticated])
def profile_update(request):
    serializer = ProfileSerializer(request.user, data=request.data, partial=True)
    serializer.is_valid(raise_exception=True)
    serializer.save()
    return Response(serializer.data)


@extend_schema(
    summary="Сменить пароль текущего пользователя",
    request=PasswordChangeSerializer,
    responses={200: OpenApiResponse(description="Пароль изменен")},
    tags=["Профиль"],
)
@api_view(["POST"])
@permission_classes([IsAuthenticated])
def password_change(request):
    serializer = PasswordChangeSerializer(data=request.data, context={"request": request})
    serializer.is_valid(raise_exception=True)
    serializer.save()
    if hasattr(request, "session"):
        update_session_auth_hash(request, request.user)
    return Response({"detail": "Пароль изменен."})


@extend_schema(summary="Сводная аналитика", responses=OpenApiTypes.OBJECT, tags=["Аналитика"])
@api_view(["GET"])
@permission_classes([IsAuthenticated])
def stats(request):
    return Response(full_analytics(request.user))


@extend_schema(
    summary="Экспорт оценок в CSV",
    responses={(200, "text/csv"): OpenApiTypes.BINARY},
    tags=["Экспорт"],
)
@api_view(["GET"])
@permission_classes([IsAuthenticated])
def export_grades(request):
    return export_grades_csv(request.user)


@extend_schema(
    summary="Экспорт посещаемости в CSV",
    responses={(200, "text/csv"): OpenApiTypes.BINARY},
    tags=["Экспорт"],
)
@api_view(["GET"])
@permission_classes([IsAuthenticated])
def export_attendance(request):
    return export_attendance_csv(request.user)
