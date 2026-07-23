from rest_framework.permissions import BasePermission


class IsAdminOrManager(BasePermission):
    message = "Only Admin and Manager users can access user CRUD."

    def has_permission(self, request, view):
        user_type = request.query_params.get("user_type")
        return user_type in {"Admin", "Manager"}
