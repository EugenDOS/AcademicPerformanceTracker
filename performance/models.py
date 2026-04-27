from django.conf import settings
from django.contrib.auth.models import AbstractUser
from django.core.validators import MaxValueValidator, MinValueValidator
from django.db import models


class User(AbstractUser):
    class Role(models.TextChoices):
        ADMIN = "admin", "Администратор"
        TEACHER = "teacher", "Преподаватель"
        STUDENT = "student", "Студент"

    role = models.CharField(
        "роль",
        max_length=20,
        choices=Role.choices,
        default=Role.STUDENT,
    )
    group = models.ForeignKey(
        "StudyGroup",
        verbose_name="учебная группа",
        related_name="students",
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
    )

    def is_admin_role(self):
        return self.is_superuser or self.role == self.Role.ADMIN

    def is_teacher_role(self):
        return self.role == self.Role.TEACHER

    def is_student_role(self):
        return self.role == self.Role.STUDENT


class StudyGroup(models.Model):
    name = models.CharField("название", max_length=100, unique=True)
    curator = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        verbose_name="куратор",
        related_name="curated_groups",
        on_delete=models.SET_NULL,
        limit_choices_to={"role": User.Role.TEACHER},
        null=True,
        blank=True,
    )

    class Meta:
        verbose_name = "учебная группа"
        verbose_name_plural = "учебные группы"
        ordering = ["name"]

    def __str__(self):
        return self.name


class Subject(models.Model):
    name = models.CharField("название", max_length=120, unique=True)
    description = models.TextField("описание", blank=True)
    teachers = models.ManyToManyField(
        settings.AUTH_USER_MODEL,
        verbose_name="преподаватели",
        related_name="subjects",
        limit_choices_to={"role": User.Role.TEACHER},
        blank=True,
    )

    class Meta:
        verbose_name = "предмет"
        verbose_name_plural = "предметы"
        ordering = ["name"]

    def __str__(self):
        return self.name


class Lesson(models.Model):
    group = models.ForeignKey(
        StudyGroup,
        verbose_name="группа",
        related_name="lessons",
        on_delete=models.CASCADE,
    )
    subject = models.ForeignKey(
        Subject,
        verbose_name="предмет",
        related_name="lessons",
        on_delete=models.CASCADE,
    )
    teacher = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        verbose_name="преподаватель",
        related_name="lessons",
        on_delete=models.CASCADE,
        limit_choices_to={"role": User.Role.TEACHER},
    )
    date = models.DateField("дата")
    topic = models.CharField("тема занятия", max_length=200)

    class Meta:
        verbose_name = "занятие"
        verbose_name_plural = "занятия"
        ordering = ["-date", "subject__name"]

    def __str__(self):
        return f"{self.date}: {self.subject} ({self.group})"


class Attendance(models.Model):
    class Status(models.TextChoices):
        PRESENT = "present", "Присутствовал"
        ABSENT = "absent", "Отсутствовал"
        LATE = "late", "Опоздал"
        EXCUSED = "excused", "Уважительная причина"

    lesson = models.ForeignKey(
        Lesson,
        verbose_name="занятие",
        related_name="attendance_records",
        on_delete=models.CASCADE,
    )
    student = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        verbose_name="студент",
        related_name="attendance_records",
        on_delete=models.CASCADE,
        limit_choices_to={"role": User.Role.STUDENT},
    )
    status = models.CharField(
        "статус",
        max_length=20,
        choices=Status.choices,
        default=Status.PRESENT,
    )
    comment = models.CharField("комментарий", max_length=200, blank=True)

    class Meta:
        verbose_name = "посещаемость"
        verbose_name_plural = "посещаемость"
        unique_together = ("lesson", "student")
        ordering = ["-lesson__date", "student__last_name", "student__username"]

    def __str__(self):
        return f"{self.student} - {self.lesson}: {self.get_status_display()}"


class Grade(models.Model):
    student = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        verbose_name="студент",
        related_name="grades",
        on_delete=models.CASCADE,
        limit_choices_to={"role": User.Role.STUDENT},
    )
    subject = models.ForeignKey(
        Subject,
        verbose_name="предмет",
        related_name="grades",
        on_delete=models.CASCADE,
    )
    teacher = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        verbose_name="преподаватель",
        related_name="given_grades",
        on_delete=models.CASCADE,
        limit_choices_to={"role": User.Role.TEACHER},
    )
    lesson = models.ForeignKey(
        Lesson,
        verbose_name="занятие",
        related_name="grades",
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
    )
    value = models.PositiveSmallIntegerField(
        "оценка",
        validators=[MinValueValidator(2), MaxValueValidator(5)],
    )
    date = models.DateField("дата")
    comment = models.CharField("комментарий", max_length=200, blank=True)

    class Meta:
        verbose_name = "оценка"
        verbose_name_plural = "оценки"
        ordering = ["-date", "student__last_name", "student__username"]

    def __str__(self):
        return f"{self.student} - {self.subject}: {self.value}"


class Notification(models.Model):
    user = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        verbose_name="пользователь",
        related_name="notifications",
        on_delete=models.CASCADE,
    )
    title = models.CharField("заголовок", max_length=150)
    message = models.TextField("сообщение")
    is_read = models.BooleanField("прочитано", default=False)
    created_at = models.DateTimeField("создано", auto_now_add=True)

    class Meta:
        verbose_name = "уведомление"
        verbose_name_plural = "уведомления"
        ordering = ["-created_at"]

    def __str__(self):
        return f"{self.user}: {self.title}"
