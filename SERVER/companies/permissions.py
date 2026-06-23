"""Company-level access control."""

from rest_framework.permissions import BasePermission

from core.enums import UserRole


class IsCompanyAdminOrSuperAdmin(BasePermission):
    message = "Only company administrators may modify the company."

    def has_permission(self, request, view):
        user = request.user
        if not (user and user.is_authenticated):
            return False
        return user.role in {UserRole.SUPER_ADMIN, UserRole.COMPANY_ADMIN}

    def has_object_permission(self, request, view, obj):
        user = request.user
        if user.role == UserRole.SUPER_ADMIN:
            return True
        return obj.id == user.company_id
