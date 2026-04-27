from django.contrib.auth.views import LoginView, LogoutView
from django.urls import include, path
from rest_framework.routers import DefaultRouter

from . import api_views, views

router = DefaultRouter()
router.register("users", api_views.UserViewSet, basename="users")
router.register("groups", api_views.StudyGroupViewSet, basename="groups")
router.register("subjects", api_views.SubjectViewSet, basename="subjects")
router.register("lessons", api_views.LessonViewSet, basename="lessons")
router.register("attendance", api_views.AttendanceViewSet, basename="attendance")
router.register("grades", api_views.GradeViewSet, basename="grades")
router.register("notifications", api_views.NotificationViewSet, basename="notifications")

urlpatterns = [
    path("", views.dashboard, name="dashboard"),
    path("login/", LoginView.as_view(template_name="performance/login.html"), name="login"),
    path("logout/", LogoutView.as_view(), name="logout"),
    path("groups/", views.groups_page, name="groups"),
    path("subjects/", views.subjects_page, name="subjects"),
    path("lessons/", views.lessons_page, name="lessons"),
    path("grades/", views.grades_page, name="grades"),
    path("attendance/", views.attendance_page, name="attendance"),
    path("profile/", views.profile_page, name="profile"),
    path("profile/password/", views.password_change_page, name="password-change"),
    path("notifications/", views.notifications_page, name="notifications"),
    path("notifications/<int:pk>/read/", views.notification_read_page, name="notification-read"),
    path("analytics/", views.analytics_page, name="analytics"),
    path("exports/grades.csv", views.export_grades_page, name="export-grades"),
    path("exports/attendance.csv", views.export_attendance_page, name="export-attendance"),
    path("api/me/", api_views.me, name="api-me"),
    path("api/profile/", api_views.profile_update, name="api-profile"),
    path("api/password/change/", api_views.password_change, name="api-password-change"),
    path("api/stats/", api_views.stats, name="api-stats"),
    path("api/export/grades.csv", api_views.export_grades, name="api-export-grades"),
    path("api/export/attendance.csv", api_views.export_attendance, name="api-export-attendance"),
    path("api/", include(router.urls)),
]
