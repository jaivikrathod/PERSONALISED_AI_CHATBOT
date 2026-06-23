"""Chatbot management endpoints (authenticated dashboard side)."""

from drf_spectacular.utils import extend_schema
from rest_framework import viewsets
from rest_framework.decorators import action
from rest_framework.permissions import IsAuthenticated
from rest_framework.response import Response

from core.mixins import CompanyCreateMixin, CompanyScopedQuerysetMixin
from core.permissions import HasCompanyRole
from core.enums import UserRole

from .models import Chatbot, Visitor
from .serializers import ChatbotSerializer, VisitorSerializer


@extend_schema(tags=["chatbot"])
class ChatbotViewSet(
    CompanyScopedQuerysetMixin, CompanyCreateMixin, viewsets.ModelViewSet
):
    queryset = Chatbot.objects.select_related("company").all()
    serializer_class = ChatbotSerializer
    permission_classes = [IsAuthenticated, HasCompanyRole]
    allowed_roles = [UserRole.COMPANY_ADMIN, UserRole.MANAGER]
    lookup_field = "uuid"
    filterset_fields = ["active"]
    search_fields = ["name"]

    @action(detail=True, methods=["post"])
    def rotate_token(self, request, uuid=None):
        """Invalidate the current widget token and issue a fresh one."""
        bot = self.get_object()
        token = bot.rotate_widget_token()
        return Response({"success": True, "widget_token": token})


@extend_schema(tags=["chatbot"])
class VisitorViewSet(CompanyScopedQuerysetMixin, viewsets.ReadOnlyModelViewSet):
    queryset = Visitor.objects.select_related("chatbot", "chatbot__company").all()
    serializer_class = VisitorSerializer
    permission_classes = [IsAuthenticated]
    company_field = "chatbot__company"
    lookup_field = "uuid"
    filterset_fields = ["chatbot__uuid"]
    search_fields = ["name", "email", "session_id"]
