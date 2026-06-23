from unittest.mock import patch

from rest_framework import status
from rest_framework.test import APITestCase

from chatbot.models import Chatbot, Visitor
from companies.models import Company


class WidgetApiTests(APITestCase):
    def setUp(self):
        self.company = Company.objects.create(name="Acme", email="a@a.com")
        self.bot = Chatbot.objects.create(company=self.company, name="Bot", active=True)
        self.auth = f"Widget {self.bot.widget_token}"

    def test_start_requires_valid_token(self):
        resp = self.client.post(
            "/api/v1/integrations/widget/start/", {"session_id": "s1"}, format="json"
        )
        self.assertEqual(resp.status_code, status.HTTP_403_FORBIDDEN)

    def test_start_creates_visitor_and_conversation(self):
        resp = self.client.post(
            "/api/v1/integrations/widget/start/",
            {"session_id": "s1", "name": "Jo"},
            format="json",
            HTTP_AUTHORIZATION=self.auth,
        )
        self.assertEqual(resp.status_code, status.HTTP_201_CREATED)
        self.assertTrue(resp.data["conversation"])
        self.assertTrue(Visitor.objects.filter(chatbot=self.bot, session_id="s1").exists())

    @patch("conversations.services.ChatService._broadcast_message", lambda self, msg: None)
    @patch("conversations.services.get_llm_provider")
    @patch("conversations.services.SearchService")
    def test_chat_returns_bot_answer(self, mock_search, mock_llm):
        mock_search.return_value.semantic_search.return_value = [
            {"qa_id": 1, "question": "hi", "answer": "hello", "score": 0.9}
        ]
        mock_llm.return_value.chat.return_value.content = "Hello!"

        Visitor.objects.create(chatbot=self.bot, session_id="s1")
        resp = self.client.post(
            "/api/v1/integrations/widget/chat/",
            {"session_id": "s1", "message": "hi"},
            format="json",
            HTTP_AUTHORIZATION=self.auth,
        )
        self.assertEqual(resp.status_code, status.HTTP_200_OK)
        self.assertEqual(resp.data["answer"], "Hello!")
