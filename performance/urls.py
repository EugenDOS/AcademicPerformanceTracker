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

urlpatterns = [
    path("", views.dashboard, name="dashboard"),
    path("login/", LoginView.as_view(template_name="performance/login.html"), name="login"),
    path("logout/", LogoutView.as_view(), name="logout"),
    path("groups/", views.groups_page, name="groups"),
    path("subjects/", views.subjects_page, name="subjects"),
    path("lessons/", views.lessons_page, name="lessons"),
    path("grades/", views.grades_page, name="grades"),
    path("attendance/", views.attendance_page, name="attendance"),
    path("api/me/", api_views.me, name="api-me"),
    path("api/", include(router.urls)),
]
