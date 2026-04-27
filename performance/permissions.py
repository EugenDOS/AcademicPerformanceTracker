from rest_framework.permissions import SAFE_METHODS, BasePermission

from .selectors import is_admin, is_teacher


class RolePermission(BasePermission):
    def has_permission(self, request, view):
        if not request.user or not request.user.is_authenticated:
            return False
        if request.method in SAFE_METHODS:
            return True
        if is_admin(request.user):
            return True
        return is_teacher(request.user) and getattr(view, "teacher_can_write", False)

    def has_object_permission(self, request, view, obj):
        if request.method in SAFE_METHODS:
            return True
        if is_admin(request.user):
            return True
        if is_teacher(request.user) and getattr(view, "teacher_can_write", False):
            return view.teacher_owns_object(obj, request.user)
        return False
