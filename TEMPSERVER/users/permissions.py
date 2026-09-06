"""Permission classes.

Every class here reads the *authenticated* user resolved by
`users.authentication.BearerTokenAuthentication`. Nothing reads a role, a
company or a user id out of the request body or query string: those are
attacker-controlled, and treating them as identity is what the previous
`?user_type=Admin` check did.
"""

from rest_framework.permissions import BasePermission

from .models import User

MANAGER_TYPES = {User.Type.ADMIN, User.Type.MANAGER}


def _authenticated(request):
    user = getattr(request, "user", None)
    return user if (user and getattr(user, "is_authenticated", False)) else None


class IsAuthenticatedUser(BasePermission):
    """Any signed-in, active user."""

    message = "Authentication required."

    def has_permission(self, request, view):
        return _authenticated(request) is not None


class IsAdminOrManager(BasePermission):
    """Admin/Manager-only areas: user management, knowledge base, vectorization."""

    message = "Only Admin and Manager users can perform this action."

    def has_permission(self, request, view):
        user = _authenticated(request)
        return user is not None and user.type in MANAGER_TYPES


class IsAgent(BasePermission):
    """The human-agent console."""

    message = "This endpoint is only available to users of type Agent."

    def has_permission(self, request, view):
        user = _authenticated(request)
        return user is not None and user.type == User.Type.AGENT


class IsAdmin(BasePermission):
    """Reserved for destructive company-level operations."""

    message = "Only Admin users can perform this action."

    def has_permission(self, request, view):
        user = _authenticated(request)
        return user is not None and user.type == User.Type.ADMIN
