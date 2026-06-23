"""Tests for the chat flow + escalation, with the AI providers mocked."""

from unittest.mock import patch

from django.contrib.auth import get_user_model
from rest_framework.test import APITestCase

from chatbot.models import Chatbot, Visitor
from companies.models import Company
from core.enums import ConversationStatus, SenderType

from .models import Conversation, Message
from .services import ChatService, get_or_create_conversation

User = get_user_model()


class ChatFlowTests(APITestCase):
    def setUp(self):
        self.company = Company.objects.create(name="Acme", email="a@a.com")
        self.bot = Chatbot.objects.create(company=self.company, name="Bot")
        self.visitor = Visitor.objects.create(chatbot=self.bot, session_id="sess-1")
        self.conversation = get_or_create_conversation(self.bot, self.visitor)

    @patch("conversations.services.ChatService._broadcast_message", lambda self, msg: None)
    @patch("conversations.services.get_llm_provider")
    @patch("conversations.services.SearchService")
    def test_high_confidence_answer_stays_with_bot(self, mock_search, mock_llm):
        mock_search.return_value.semantic_search.return_value = [
            {"qa_id": 1, "question": "Reset password?", "answer": "Click forgot.", "score": 0.95}
        ]
        mock_llm.return_value.chat.return_value.content = "Click forgot password."

        result = ChatService(self.conversation).handle_user_message("How do I reset my password?")

        self.assertEqual(result["handled_by"], "bot")
        self.assertFalse(result["escalated"])
        self.assertEqual(result["status"], ConversationStatus.BOT)
        self.assertEqual(Message.objects.filter(sender_type=SenderType.BOT).count(), 1)

    @patch("conversations.services.ChatService._broadcast_message", lambda self, msg: None)
    @patch("conversations.services.ChatService._notify_agents", lambda self, reason: None)
    @patch("conversations.services.ChatService._record_unanswered", lambda self, q: None)
    @patch("conversations.services.get_llm_provider")
    @patch("conversations.services.SearchService")
    def test_low_confidence_escalates(self, mock_search, mock_llm):
        mock_search.return_value.semantic_search.return_value = [
            {"qa_id": 1, "question": "x", "answer": "y", "score": 0.10}
        ]
        mock_llm.return_value.chat.return_value.content = "I'm not sure."

        result = ChatService(self.conversation).handle_user_message("Unknown thing?")

        self.assertTrue(result["escalated"])
        self.conversation.refresh_from_db()
        self.assertEqual(self.conversation.status, ConversationStatus.WAITING_AGENT)

    @patch("conversations.services.ChatService._broadcast_message", lambda self, msg: None)
    def test_get_or_create_reuses_open_conversation(self):
        again = get_or_create_conversation(self.bot, self.visitor)
        self.assertEqual(again.id, self.conversation.id)
