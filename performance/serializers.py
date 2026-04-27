from django.contrib.auth import get_user_model, password_validation
from rest_framework import serializers

from .models import Attendance, Grade, Lesson, Notification, StudyGroup, Subject, User


class UserSerializer(serializers.ModelSerializer):
    password = serializers.CharField(write_only=True, required=False)

    class Meta:
        model = get_user_model()
        fields = (
            "id",
            "username",
            "password",
            "first_name",
            "last_name",
            "email",
            "role",
            "group",
        )

    def create(self, validated_data):
        password = validated_data.pop("password", None)
        user = self.Meta.model(**validated_data)
        if password:
            user.set_password(password)
        else:
            user.set_unusable_password()
        user.save()
        return user

    def update(self, instance, validated_data):
        password = validated_data.pop("password", None)
        for field, value in validated_data.items():
            setattr(instance, field, value)
        if password:
            instance.set_password(password)
        instance.save()
        return instance


class ProfileSerializer(serializers.ModelSerializer):
    group_name = serializers.StringRelatedField(source="group", read_only=True)

    class Meta:
        model = get_user_model()
        fields = ("id", "username", "first_name", "last_name", "email", "role", "group", "group_name")
        read_only_fields = ("id", "username", "role", "group", "group_name")


class PasswordChangeSerializer(serializers.Serializer):
    old_password = serializers.CharField(write_only=True)
    new_password = serializers.CharField(write_only=True)

    def validate_old_password(self, value):
        user = self.context["request"].user
        if not user.check_password(value):
            raise serializers.ValidationError("Старый пароль указан неверно.")
        return value

    def validate_new_password(self, value):
        password_validation.validate_password(value, self.context["request"].user)
        return value

    def save(self, **kwargs):
        user = self.context["request"].user
        user.set_password(self.validated_data["new_password"])
        user.save(update_fields=["password"])
        return user


class StudyGroupSerializer(serializers.ModelSerializer):
    curator_name = serializers.StringRelatedField(source="curator", read_only=True)

    class Meta:
        model = StudyGroup
        fields = ("id", "name", "curator", "curator_name")


class SubjectSerializer(serializers.ModelSerializer):
    teacher_names = serializers.StringRelatedField(source="teachers", many=True, read_only=True)

    class Meta:
        model = Subject
        fields = ("id", "name", "description", "teachers", "teacher_names")

    def validate_teachers(self, teachers):
        for teacher in teachers:
            if teacher.role != User.Role.TEACHER:
                raise serializers.ValidationError("В предмет можно добавить только преподавателей.")
        return teachers


class LessonSerializer(serializers.ModelSerializer):
    group_name = serializers.StringRelatedField(source="group", read_only=True)
    subject_name = serializers.StringRelatedField(source="subject", read_only=True)
    teacher_name = serializers.StringRelatedField(source="teacher", read_only=True)

    class Meta:
        model = Lesson
        fields = (
            "id",
            "group",
            "group_name",
            "subject",
            "subject_name",
            "teacher",
            "teacher_name",
            "date",
            "topic",
        )
        extra_kwargs = {"teacher": {"required": False}}

    def validate(self, attrs):
        teacher = attrs.get("teacher") or getattr(self.instance, "teacher", None)
        if teacher and teacher.role != User.Role.TEACHER:
            raise serializers.ValidationError({"teacher": "Пользователь должен быть преподавателем."})
        return attrs


class AttendanceSerializer(serializers.ModelSerializer):
    lesson_name = serializers.StringRelatedField(source="lesson", read_only=True)
    student_name = serializers.StringRelatedField(source="student", read_only=True)
    status_text = serializers.CharField(source="get_status_display", read_only=True)

    class Meta:
        model = Attendance
        fields = (
            "id",
            "lesson",
            "lesson_name",
            "student",
            "student_name",
            "status",
            "status_text",
            "comment",
        )

    def validate(self, attrs):
        lesson = attrs.get("lesson") or getattr(self.instance, "lesson", None)
        student = attrs.get("student") or getattr(self.instance, "student", None)
        if student and student.role != User.Role.STUDENT:
            raise serializers.ValidationError({"student": "Пользователь должен быть студентом."})
        if lesson and student and lesson.group_id != student.group_id:
            raise serializers.ValidationError("Студент должен относиться к группе занятия.")
        return attrs


class GradeSerializer(serializers.ModelSerializer):
    student_name = serializers.StringRelatedField(source="student", read_only=True)
    subject_name = serializers.StringRelatedField(source="subject", read_only=True)
    teacher_name = serializers.StringRelatedField(source="teacher", read_only=True)
    lesson_name = serializers.StringRelatedField(source="lesson", read_only=True)

    class Meta:
        model = Grade
        fields = (
            "id",
            "student",
            "student_name",
            "subject",
            "subject_name",
            "teacher",
            "teacher_name",
            "lesson",
            "lesson_name",
            "value",
            "date",
            "comment",
        )
        extra_kwargs = {"teacher": {"required": False}}

    def validate(self, attrs):
        student = attrs.get("student") or getattr(self.instance, "student", None)
        teacher = attrs.get("teacher") or getattr(self.instance, "teacher", None)
        subject = attrs.get("subject") or getattr(self.instance, "subject", None)
        lesson = attrs.get("lesson") or getattr(self.instance, "lesson", None)

        if student and student.role != User.Role.STUDENT:
            raise serializers.ValidationError({"student": "Пользователь должен быть студентом."})
        if teacher and teacher.role != User.Role.TEACHER:
            raise serializers.ValidationError({"teacher": "Пользователь должен быть преподавателем."})
        if lesson and subject and lesson.subject_id != subject.id:
            raise serializers.ValidationError("Предмет оценки должен совпадать с предметом занятия.")
        if lesson and student and lesson.group_id != student.group_id:
            raise serializers.ValidationError("Студент должен относиться к группе занятия.")
        return attrs


class NotificationSerializer(serializers.ModelSerializer):
    class Meta:
        model = Notification
        fields = ("id", "title", "message", "is_read", "created_at")
        read_only_fields = ("id", "created_at")
