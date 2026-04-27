from rest_framework import serializers, viewsets
from rest_framework.decorators import api_view, permission_classes
from rest_framework.exceptions import PermissionDenied
from rest_framework.permissions import IsAuthenticated
from rest_framework.response import Response

from .models import Attendance, Grade, Lesson, StudyGroup, Subject, User
from .permissions import RolePermission
from .selectors import (
    is_admin,
    is_teacher,
    visible_attendance,
    visible_grades,
    visible_groups,
    visible_lessons,
    visible_subjects,
    visible_users,
)
from .serializers import (
    AttendanceSerializer,
    GradeSerializer,
    LessonSerializer,
    StudyGroupSerializer,
    SubjectSerializer,
    UserSerializer,
)


class BaseRoleViewSet(viewsets.ModelViewSet):
    permission_classes = [RolePermission]
    teacher_can_write = False

    def teacher_owns_object(self, obj, teacher):
        return False


class UserViewSet(BaseRoleViewSet):
    serializer_class = UserSerializer

    def get_queryset(self):
        return visible_users(self.request.user).select_related("group")


class StudyGroupViewSet(BaseRoleViewSet):
    serializer_class = StudyGroupSerializer

    def get_queryset(self):
        return visible_groups(self.request.user).select_related("curator")


class SubjectViewSet(BaseRoleViewSet):
    serializer_class = SubjectSerializer

    def get_queryset(self):
        return visible_subjects(self.request.user).prefetch_related("teachers")


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
        serializer.save()

    def perform_update(self, serializer):
        lesson = serializer.validated_data.get("lesson") or self.get_object().lesson
        self._check_lesson_for_teacher(lesson)
        serializer.save()


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
            serializer.save(teacher=user)
            return
        if is_admin(user) and not serializer.validated_data.get("teacher"):
            raise serializers.ValidationError({"teacher": "Укажите преподавателя."})
        serializer.save()

    def perform_update(self, serializer):
        user = self.request.user
        lesson = serializer.validated_data.get("lesson") or self.get_object().lesson
        self._check_lesson_for_teacher(lesson)
        if is_teacher(user):
            serializer.save(teacher=user)
            return
        serializer.save()


@api_view(["GET"])
@permission_classes([IsAuthenticated])
def me(request):
    return Response(UserSerializer(request.user).data)
