"""KB write access is limited to admins/managers; agents are read-only."""

from rest_framework.permissions import SAFE_METHODS, BasePermission

from core.enums import UserRole


class CanEditKnowledgeBase(BasePermission):
    message = "Only admins and managers can modify the knowledge base."

    def has_permission(self, request, view):
        user = request.user
        if not (user and user.is_authenticated):
            return False
        if request.method in SAFE_METHODS:
            return True
        return user.role in {
            UserRole.SUPER_ADMIN,
            UserRole.COMPANY_ADMIN,
            UserRole.MANAGER,
        }
