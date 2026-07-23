from django.db import models
from django.db.models import OuterRef, Subquery
from rest_framework.response import Response
from rest_framework.views import APIView

from .models import ChatMessage, ChatSession
from .serializers import ChatSessionListSerializer, ChatSessionSerializer


class ChatHistoryView(APIView):
    def get(self, request):
        session_id = request.query_params.get("session_id")
        company_id = request.query_params.get("company_id")
        customer_user_id = request.query_params.get("customer_user_id")

        if not session_id:
            return Response({"detail": "session_id is required."}, status=400)

        queryset = ChatSession.objects.prefetch_related("messages").filter(id=session_id)
        if company_id is not None:
            queryset = queryset.filter(company_id=company_id)
        if customer_user_id is not None:
            queryset = queryset.filter(messages__customer_user_id=customer_user_id)

        session = queryset.first()
        if not session:
            return Response({"detail": "Chat session not found."}, status=404)

        return Response(ChatSessionSerializer(session).data)


class ChatSessionListView(APIView):
    def get(self, request):
        company_id = request.query_params.get("company_id")
        customer_user_id = request.query_params.get("customer_user_id")

        if not company_id:
            return Response({"detail": "company_id is required."}, status=400)
        if not customer_user_id:
            return Response({"detail": "customer_user_id is required."}, status=400)

        latest_message = ChatMessage.objects.filter(session_id=OuterRef("pk")).order_by("-created_at")
        sessions = (
            ChatSession.objects.filter(
                company_id=company_id,
                messages__customer_user_id=customer_user_id,
            )
            .select_related("company", "agent")
            .annotate(
                last_message_id=Subquery(latest_message.values("id")[:1]),
                message_count=Subquery(
                    ChatMessage.objects.filter(session_id=OuterRef("pk"))
                    .order_by()
                    .values("session_id")
                    .annotate(count=models.Count("id"))
                    .values("count")[:1]
                ),
            )
            .order_by("-updated_at")
            .distinct()
        )
        message_map = {
            message.id: message
            for message in ChatMessage.objects.filter(
                id__in=[session.last_message_id for session in sessions if session.last_message_id]
            )
        }
        for session in sessions:
            session.last_message_obj = message_map.get(session.last_message_id)

        return Response(ChatSessionListSerializer(sessions, many=True).data)
