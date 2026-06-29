"""Conversation service layer — the AI chat flow + escalation.

`ChatService.handle_user_message()` is the single entry point used by both the
REST widget endpoint and the WebSocket consumer. Keeping it here (not in a view
or consumer) means the exact same logic runs regardless of transport.
"""

from __future__ import annotations

import logging

from django.conf import settings
from django.db import transaction
from django.utils import timezone

from core.ai import get_llm_provider
from core.ai.base import ChatMessage
from core.enums import ConversationStatus, SenderType
from knowledge_base.services import SearchService

from .models import Conversation, Message

logger = logging.getLogger(__name__)

# How many prior turns to feed the LLM for conversational continuity.
HISTORY_WINDOW = 8


class ChatService:
    """Orchestrates retrieval-augmented answering for one conversation."""

    def __init__(self, conversation: Conversation):
        self.conversation = conversation
        self.company_id = conversation.company_id
        self.threshold = settings.CHAT_CONFIDENCE_THRESHOLD
        self.top_k = settings.CHAT_TOP_K

    # -- public API ---------------------------------------------------------
    @transaction.atomic
    def handle_user_message(self, text: str) -> dict:
        """Process a visitor message end-to-end.

        Returns a dict with the bot reply, confidence, retrieved sources and the
        (possibly updated) conversation status.
        """
        visitor_msg = self._save_message(SenderType.VISITOR, text)

        # If a human agent has taken over, the bot stays silent — the message is
        # simply stored and relayed to the agent over the websocket.
        if self.conversation.is_with_agent:
            return {
                "handled_by": "agent_pending",
                "status": self.conversation.status,
                "visitor_message_id": visitor_msg.id,
                "answer": None,
                "confidence": None,
            }

        # 1-4: embed the query and retrieve the most similar FAQ entries.
        sources = SearchService(self.company_id).semantic_search(text, top_k=self.top_k)
        confidence = sources[0]["score"] if sources else 0.0

        # 5-6: build context + call the LLM.
        answer = self._generate_answer(text, sources)

        # 7-8: persist the bot reply with provenance metadata.
        bot_msg = self._save_message(
            SenderType.BOT,
            answer,
            metadata={
                "confidence": confidence,
                "sources": [s["qa_id"] for s in sources],
            },
        )

        self.conversation.last_confidence = confidence
        self.conversation.save(update_fields=["last_confidence", "updated_at"])

        escalated = False
        if confidence < self.threshold:
            escalated = True
            self._record_unanswered(text)
            self.escalate(reason="low_confidence")

        return {
            "handled_by": "bot",
            "answer": answer,
            "confidence": round(confidence, 4),
            "escalated": escalated,
            "status": self.conversation.status,
            "sources": sources,
            "visitor_message_id": visitor_msg.id,
            "bot_message_id": bot_msg.id,
        }

    @transaction.atomic
    def escalate(self, reason: str = "manual") -> Conversation:
        """Move the conversation into the human-agent queue and notify agents."""
        if self.conversation.status == ConversationStatus.RESOLVED:
            return self.conversation
        if not self.conversation.is_with_agent:
            self.conversation.status = ConversationStatus.WAITING_AGENT
            self.conversation.save(update_fields=["status", "updated_at"])

        self._notify_agents(reason)
        return self.conversation

    # -- internals ----------------------------------------------------------
    def _save_message(self, sender_type, text, metadata=None, sender_agent=None) -> Message:
        msg = Message.objects.create(
            conversation=self.conversation,
            sender_type=sender_type,
            sender_agent=sender_agent,
            message=text,
            metadata=metadata or {},
        )
        self._broadcast_message(msg)
        return msg

    def _generate_answer(self, question: str, sources: list[dict]) -> str:
        if not sources:
            return (
                "I'm not sure about that yet, but I can connect you with a human "
                "agent who can help."
            )

        context_block = "\n\n".join(
            f"Q: {s['question']}\nA: {s['answer']}" for s in sources
        )
        bot = self.conversation.chatbot
        persona = bot.system_prompt or (
            "You are a helpful, concise customer-support assistant."
        )
        system = (
            f"{persona}\n\n"
            "Answer ONLY using the knowledge base entries below. If they do not "
            "contain the answer, say you are not sure and offer a human agent.\n\n"
            f"KNOWLEDGE BASE:\n{context_block}"
        )

        history = self._recent_history()
        history.append(ChatMessage(role="user", content=question))

        # `sources` lets the key-free LocalLLMProvider echo the best FAQ answer;
        # API-backed providers (OpenAI/Gemini) accept and ignore it.
        result = get_llm_provider().chat(system=system, messages=history, sources=sources)
        return result.content.strip()

    def _recent_history(self) -> list[ChatMessage]:
        recent = (
            self.conversation.messages.exclude(sender_type=SenderType.BOT, message="")
            .order_by("-created_at")[:HISTORY_WINDOW]
        )
        history = []
        for msg in reversed(list(recent)):
            role = "assistant" if msg.sender_type in {SenderType.BOT, SenderType.AGENT} else "user"
            history.append(ChatMessage(role=role, content=msg.message))
        return history

    def _record_unanswered(self, question: str):
        """Log low-confidence questions for managers to curate into FAQs."""
        try:
            from analytics.services import record_unanswered_question

            record_unanswered_question(self.company_id, question)
        except Exception:  # noqa: BLE001 - analytics must never break chat
            logger.exception("Failed to record unanswered question")

    def _notify_agents(self, reason: str):
        try:
            from agents.services import notify_available_agents

            notify_available_agents(self.conversation, reason)
        except Exception:  # noqa: BLE001
            logger.exception("Failed to notify agents")

    def _broadcast_message(self, msg: Message):
        """Push the new message to everyone in the conversation's websocket room."""
        try:
            from asgiref.sync import async_to_sync
            from channels.layers import get_channel_layer

            layer = get_channel_layer()
            if layer is None:
                return
            async_to_sync(layer.group_send)(
                f"conversation_{self.conversation.uuid}",
                {
                    "type": "chat.message",
                    "message": {
                        "id": msg.id,
                        "sender_type": msg.sender_type,
                        "message": msg.message,
                        "metadata": msg.metadata,
                        "created_at": msg.created_at.isoformat(),
                    },
                },
            )
        except Exception:  # noqa: BLE001 - realtime is best-effort
            logger.exception("WebSocket broadcast failed")


def get_or_create_conversation(chatbot, visitor) -> Conversation:
    """Return the visitor's open conversation or start a new one."""
    conversation = (
        Conversation.objects.filter(visitor=visitor, chatbot=chatbot)
        .exclude(status=ConversationStatus.RESOLVED)
        .order_by("-created_at")
        .first()
    )
    if conversation:
        return conversation
    return Conversation.objects.create(
        company_id=chatbot.company_id,
        chatbot=chatbot,
        visitor=visitor,
        status=ConversationStatus.BOT,
    )


def mark_resolved(conversation: Conversation) -> Conversation:
    conversation.status = ConversationStatus.RESOLVED
    conversation.resolved_at = timezone.now()
    conversation.save(update_fields=["status", "resolved_at", "updated_at"])
    return conversation
