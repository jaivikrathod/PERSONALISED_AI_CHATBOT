"""Account-specific permissions (re-exports shared ones for convenience)."""

from core.permissions import (  # noqa: F401
    HasCompanyRole,
    IsAuthenticatedAndActive,
    IsCompanyMember,
    IsSuperAdmin,
)
from core.enums import UserRole
from rest_framework.permissions import BasePermission


class CanManageTeam(BasePermission):
    """Only COMPANY_ADMIN / MANAGER (or SUPER_ADMIN) may manage team members."""

    message = "You are not allowed to manage team members."

    def has_permission(self, request, view):
        user = request.user
        if not (user and user.is_authenticated):
            return False
        return user.role in {
            UserRole.SUPER_ADMIN,
            UserRole.COMPANY_ADMIN,
            UserRole.MANAGER,
        }
