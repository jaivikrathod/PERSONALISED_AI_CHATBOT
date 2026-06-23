"""Permission that requires a valid widget token (resolved chatbot in request.auth)."""

from chatbot.models import Chatbot
from rest_framework.permissions import BasePermission


class HasValidWidgetToken(BasePermission):
    message = "A valid widget token is required."

    def has_permission(self, request, view):
        return isinstance(request.auth, Chatbot)
