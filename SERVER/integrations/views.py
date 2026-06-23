"""Widget configuration (authenticated) + public token-based widget APIs."""

from django.db import transaction
from drf_spectacular.utils import extend_schema
from rest_framework import status, viewsets
from rest_framework.decorators import action
from rest_framework.permissions import AllowAny, IsAuthenticated
from rest_framework.response import Response
from rest_framework.views import APIView

from chatbot.models import Chatbot, Visitor
from chatbot.serializers import PublicChatbotSerializer
from conversations.services import ChatService, get_or_create_conversation
from core.enums import UserRole
from core.mixins import CompanyScopedQuerysetMixin

from .authentication import WidgetTokenAuthentication
from .models import WidgetConfig
from .permissions import HasValidWidgetToken
from .serializers import (
    WidgetChatSerializer,
    WidgetConfigSerializer,
    WidgetStartSerializer,
)


# ---------------------------------------------------------------------------
# Dashboard side (authenticated): manage widget configuration.
# ---------------------------------------------------------------------------
@extend_schema(tags=["integrations"])
class WidgetConfigViewSet(CompanyScopedQuerysetMixin, viewsets.ModelViewSet):
    queryset = WidgetConfig.objects.select_related("chatbot", "chatbot__company").all()
    serializer_class = WidgetConfigSerializer
    permission_classes = [IsAuthenticated]
    company_field = "chatbot__company"
    lookup_field = "uuid"

    def perform_create(self, serializer):
        chatbot_uuid = self.request.data.get("chatbot")
        qs = Chatbot.objects.all()
        if self.request.user.role != UserRole.SUPER_ADMIN:
            qs = qs.filter(company_id=self.request.user.company_id)
        chatbot = qs.get(uuid=chatbot_uuid)
        serializer.save(chatbot=chatbot)


# ---------------------------------------------------------------------------
# Public widget side (token-based). No user authentication.
# ---------------------------------------------------------------------------
class _WidgetBaseView(APIView):
    authentication_classes = [WidgetTokenAuthentication]
    permission_classes = [HasValidWidgetToken]

    @property
    def chatbot(self) -> Chatbot:
        return self.request.auth


@extend_schema(tags=["widget"], responses=WidgetConfigSerializer)
class WidgetBootstrapView(_WidgetBaseView):
    """GET /widget/config/ — public widget settings for the embedding page."""

    serializer_class = WidgetConfigSerializer

    def get(self, request):
        config = getattr(self.chatbot, "widget_config", None)
        payload = {
            "chatbot": PublicChatbotSerializer(self.chatbot).data,
            "config": WidgetConfigSerializer(config).data if config else None,
        }
        return Response({"success": True, **payload})


@extend_schema(tags=["widget"], request=WidgetStartSerializer, responses=WidgetStartSerializer)
class WidgetStartView(_WidgetBaseView):
    """POST /widget/start/ — create/resume a visitor + conversation."""

    serializer_class = WidgetStartSerializer

    @transaction.atomic
    def post(self, request):
        serializer = WidgetStartSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        data = serializer.validated_data

        visitor, _ = Visitor.objects.get_or_create(
            chatbot=self.chatbot,
            session_id=data["session_id"],
            defaults={
                "name": data.get("name", ""),
                "email": data.get("email", ""),
                "metadata": data.get("metadata", {}),
            },
        )
        conversation = get_or_create_conversation(self.chatbot, visitor)
        return Response(
            {
                "success": True,
                "conversation": str(conversation.uuid),
                "visitor": str(visitor.uuid),
                "welcome_message": self.chatbot.welcome_message,
                "ws_url": f"/ws/visitor/{conversation.uuid}/?token={self.chatbot.widget_token}",
            },
            status=status.HTTP_201_CREATED,
        )


@extend_schema(tags=["widget"], request=WidgetChatSerializer, responses=WidgetChatSerializer)
class WidgetChatView(_WidgetBaseView):
    """POST /widget/chat/ — send a visitor message, get the bot reply (REST path).

    Realtime clients use the WebSocket instead; this endpoint exists for
    no-JS / fallback integrations.
    """

    serializer_class = WidgetChatSerializer

    def post(self, request):
        serializer = WidgetChatSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)

        visitor = Visitor.objects.filter(
            chatbot=self.chatbot, session_id=serializer.validated_data["session_id"]
        ).first()
        if visitor is None:
            return Response(
                {"success": False, "message": "Unknown session. Call /widget/start/ first."},
                status=status.HTTP_400_BAD_REQUEST,
            )

        conversation = get_or_create_conversation(self.chatbot, visitor)
        result = ChatService(conversation).handle_user_message(
            serializer.validated_data["message"]
        )
        return Response({"success": True, **result})
