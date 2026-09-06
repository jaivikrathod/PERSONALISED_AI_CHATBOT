from django.utils import timezone
from rest_framework.permissions import AllowAny
from rest_framework.response import Response
from rest_framework.views import APIView

from company.models import Company
from users.permissions import IsAdminOrManager, IsAgent

from .models import ChatMessage, ChatSession
from .serializers import (
    ChatMessageSerializer,
    ChatSessionListSerializer,
    ChatSessionSerializer,
)
from .services import (
    ACTIVE_SESSION_STATUSES,
    agent_group,
    flag_agent_needed,
    message_event,
    send_to_group_sync,
    session_event,
    session_group,
    with_last_message,
)


class ChatWidgetConfigView(APIView):
    """GET /api/chat/widget/?company_id=<id>

    Public metadata for the shareable chat widget (``/chat/<company_id>`` in
    the frontend). Anonymous visitors hit this before they are allowed to type,
    so it deliberately exposes only the company name — never the contact
    details on the Company record.
    """

    authentication_classes: list = []
    permission_classes = [AllowAny]

    def get(self, request):
        company_id = request.query_params.get("company_id")
        if not company_id:
            return Response({"detail": "company_id is required."}, status=400)

        company = Company.objects.filter(id=company_id).values("id", "name").first()
        if company is None:
            return Response({"detail": "Company not found."}, status=404)

        return Response({"company_id": company["id"], "company_name": company["name"]})


class ChatHistoryView(APIView):
    """GET /api/chat/history/?session_id=<id>&token=<public_token>

    The public widget replaying its own conversation after a reload. Session ids
    are sequential, so the id alone proves nothing: the caller must present the
    session's `public_token`, which only the browser that started the chat was
    ever given.
    """

    authentication_classes: list = []
    permission_classes = [AllowAny]

    def get(self, request):
        session_id = request.query_params.get("session_id")
        token = request.query_params.get("token")

        if not session_id:
            return Response({"detail": "session_id is required."}, status=400)
        if not token:
            return Response({"detail": "token is required."}, status=400)

        session = (
            ChatSession.objects.prefetch_related("messages")
            .filter(id=session_id, public_token=token)
            .first()
        )
        # One message for "no such session" and "wrong token" so the endpoint
        # cannot be used to test which session ids exist.
        if not session:
            return Response({"detail": "Chat session not found."}, status=404)

        return Response(ChatSessionSerializer(session).data)


class AssignAgentView(APIView):
    """POST /api/chat/sessions/assign/  -> assign a free agent to a session.

    Picks an Agent-type user in the session's company who is not currently
    attached to any live (open / in progress) chat, sets them as this session's
    agent and pushes the chat into their console.

    Body: {"session_id": <int>}
    """

    permission_classes = [IsAdminOrManager]

    def post(self, request):
        session_id = request.data.get("session_id")
        if not session_id:
            return Response({"detail": "session_id is required."}, status=400)

        session = ChatSession.objects.filter(
            id=session_id,
            company_id=request.user.company_id,
        ).first()
        if session is None:
            return Response({"detail": "Chat session not found."}, status=404)

        if session.agent_id is not None:
            return Response(
                {"detail": "Session already has an agent assigned."},
                status=409,
            )

        agent = flag_agent_needed(session)
        if agent is None:
            return Response(
                {"detail": "No free agent available for this company."},
                status=409,
            )

        send_to_group_sync(
            agent_group(agent.id),
            {"type": "chat.assigned", "session": session_event(session, agent.id)},
        )

        return Response(ChatSessionSerializer(session).data)


# ---------------------------------------------------------------------------
# Agent console. `agent_id` used to arrive in the request; it now comes from
# the bearer token, so an agent can only ever act as themselves.
# ---------------------------------------------------------------------------
class AgentChatListView(APIView):
    """GET /api/agent/chats/  -> chats assigned to the calling agent."""

    permission_classes = [IsAgent]

    def get(self, request):
        sessions = with_last_message(
            ChatSession.objects.filter(agent_id=request.user.id)
        )
        return Response(ChatSessionListSerializer(sessions, many=True).data)


class AgentChatHistoryView(APIView):
    """GET /api/agent/chats/history/?session_id=<id>

    Full message history of one session, scoped to the calling agent so an agent
    can only read their own conversations.
    """

    permission_classes = [IsAgent]

    def get(self, request):
        session_id = request.query_params.get("session_id")
        if not session_id:
            return Response({"detail": "session_id is required."}, status=400)

        session = (
            ChatSession.objects.prefetch_related("messages")
            .filter(id=session_id, agent_id=request.user.id)
            .first()
        )
        if not session:
            return Response({"detail": "Chat session not found for this agent."}, status=404)

        return Response(ChatSessionSerializer(session).data)


class AgentSendMessageView(APIView):
    """POST /api/agent/chats/send/  -> agent replies directly to the client.

    Body: {"session_id": <int>, "message": <str>}
    Only the agent assigned to the session may post into it. The reply is also
    pushed onto the session's channel group so the customer widget shows it
    without a refresh (same path the agent socket uses).
    """

    permission_classes = [IsAgent]

    def post(self, request):
        agent_id = request.user.id
        session_id = request.data.get("session_id")
        message = (request.data.get("message") or "").strip()

        if not session_id:
            return Response({"detail": "session_id is required."}, status=400)
        if not message:
            return Response({"detail": "message is required."}, status=400)

        session = ChatSession.objects.filter(id=session_id, agent_id=agent_id).first()
        if session is None:
            return Response(
                {"detail": "Chat session not found for this agent."},
                status=404,
            )

        chat_message = ChatMessage.objects.create(
            company_id=session.company_id,
            session=session,
            message=message,
            sent_by_us=True,
            is_ai=False,
            this_user_id=agent_id,
            message_type=ChatMessage.MessageType.TEXT,
        )

        # An agent replying means the handover actually happened; the save also
        # touches `updated_at` so the chat sorts to the top of inbox lists.
        if session.status in ACTIVE_SESSION_STATUSES:
            session.status = ChatSession.Status.IN_PROGRESS
        session.save(update_fields=["status", "updated_at"])

        payload = message_event(chat_message)
        send_to_group_sync(
            session_group(session.id), {"type": "chat.message", "message": payload}
        )
        send_to_group_sync(
            agent_group(agent_id), {"type": "chat.message", "message": payload}
        )

        return Response(ChatMessageSerializer(chat_message).data, status=201)


class AgentCloseChatView(APIView):
    """POST /api/agent/chats/close/  -> agent finishes a conversation.

    Body: {"session_id": <int>}
    Closing is what frees the agent again: `pick_free_agent` only skips agents
    sitting on open / in-progress sessions.
    """

    permission_classes = [IsAgent]

    def post(self, request):
        agent_id = request.user.id
        session_id = request.data.get("session_id")

        if not session_id:
            return Response({"detail": "session_id is required."}, status=400)

        session = ChatSession.objects.filter(id=session_id, agent_id=agent_id).first()
        if session is None:
            return Response(
                {"detail": "Chat session not found for this agent."},
                status=404,
            )

        session.status = ChatSession.Status.CLOSED
        session.closed_at = timezone.now()
        session.agent_needed = False
        session.save(
            update_fields=["status", "closed_at", "agent_needed", "updated_at"]
        )

        send_to_group_sync(
            session_group(session.id),
            {"type": "chat.closed", "session_id": session.id},
        )
        send_to_group_sync(
            agent_group(agent_id), {"type": "chat.closed", "session_id": session.id}
        )

        return Response(ChatSessionSerializer(session).data)
