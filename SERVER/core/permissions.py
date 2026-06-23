"""Reusable DRF permission classes for RBAC + multi-tenant isolation.

Tenancy model
-------------
Every authenticated (non-super-admin) user is bound to exactly one company via
`request.user.active_company` (resolved by accounts.User). Company-scoped
querysets filter on that company; object-level checks reject cross-tenant access.
"""

from rest_framework.permissions import BasePermission, SAFE_METHODS

from core.enums import UserRole


class IsAuthenticatedAndActive(BasePermission):
    message = "Authentication credentials were not provided or account is inactive."

    def has_permission(self, request, view):
        return bool(request.user and request.user.is_authenticated and request.user.is_active)


class IsSuperAdmin(BasePermission):
    message = "Only super administrators may perform this action."

    def has_permission(self, request, view):
        user = request.user
        return bool(user and user.is_authenticated and user.role == UserRole.SUPER_ADMIN)


class HasCompanyRole(BasePermission):
    """Grant access only to users whose role is in `view.allowed_roles`.

    SUPER_ADMIN always passes. Define `allowed_roles` on the view, e.g.::

        allowed_roles = [UserRole.COMPANY_ADMIN, UserRole.MANAGER]
    """

    message = "You do not have the required role for this action."

    def has_permission(self, request, view):
        user = request.user
        if not (user and user.is_authenticated):
            return False
        if user.role == UserRole.SUPER_ADMIN:
            return True
        allowed = getattr(view, "allowed_roles", None)
        if allowed is None:
            return True  # role-agnostic view, only auth required
        return user.role in allowed


class IsCompanyMember(BasePermission):
    """Object-level tenant isolation.

    Works for any object that exposes a `company_id` (directly or via the
    `get_object_company` hook). Company A can never touch Company B's rows.
    """

    message = "This resource belongs to another company."

    def has_permission(self, request, view):
        return bool(request.user and request.user.is_authenticated)

    def has_object_permission(self, request, view, obj):
        user = request.user
        if user.role == UserRole.SUPER_ADMIN:
            return True

        company_id = self._resolve_company_id(obj)
        if company_id is None:
            return False
        return company_id == user.company_id


    @staticmethod
    def _resolve_company_id(obj):
        if hasattr(obj, "get_object_company_id"):
            return obj.get_object_company_id()
        if hasattr(obj, "company_id"):
            return obj.company_id
        # Walk one relation up (e.g. QuestionAnswer -> knowledge_base.company)
        for attr in ("knowledge_base", "conversation", "chatbot"):
            related = getattr(obj, attr, None)
            if related is not None and hasattr(related, "company_id"):
                return related.company_id
        return None


class ReadOnly(BasePermission):
    def has_permission(self, request, view):
        return request.method in SAFE_METHODS
