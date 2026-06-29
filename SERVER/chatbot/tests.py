from django.contrib.auth import get_user_model
from rest_framework import status
from rest_framework.test import APITestCase

from companies.models import Company
from core.enums import UserRole

from .models import Chatbot

User = get_user_model()


class ChatbotTests(APITestCase):
    def setUp(self):
        self.company = Company.objects.create(name="Acme", email="a@a.com")
        self.admin = User.objects.create_user(
            email="admin@acme.com", password="pass12345",
            role=UserRole.COMPANY_ADMIN, company=self.company,
        )
        self.client.force_authenticate(self.admin)

    def test_create_chatbot_generates_widget_token(self):
        resp = self.client.post("/api/v1/chatbot/chatbots/", {"name": "Support Bot"}, format="json")
        self.assertEqual(resp.status_code, status.HTTP_201_CREATED)
        self.assertTrue(resp.data["widget_token"])
        bot = Chatbot.objects.get(uuid=resp.data["uuid"])
        self.assertEqual(bot.company_id, self.company.id)

    def test_rotate_token_changes_value(self):
        bot = Chatbot.objects.create(company=self.company, name="Bot")
        old = bot.widget_token
        resp = self.client.post(f"/api/v1/chatbot/chatbots/{bot.id}/rotate_token/")
        self.assertEqual(resp.status_code, status.HTTP_200_OK)
        self.assertNotEqual(resp.data["widget_token"], old)
