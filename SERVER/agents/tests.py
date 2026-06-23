from unittest.mock import patch

from django.contrib.auth import get_user_model
from rest_framework.test import APITestCase

from chatbot.models import Chatbot, Visitor
from companies.models import Company
from conversations.models import Conversation
from core.enums import ConversationStatus, UserRole

from .models import ConversationAssignment
from .services import assign_conversation, close_conversation, transfer_conversation

User = get_user_model()


@patch("agents.services._notify_conversation", lambda *a, **k: None)
class AssignmentServiceTests(APITestCase):
    def setUp(self):
        self.company = Company.objects.create(name="Acme", email="a@a.com")
        self.bot = Chatbot.objects.create(company=self.company, name="Bot")
        self.visitor = Visitor.objects.create(chatbot=self.bot, session_id="s1")
        self.conversation = Conversation.objects.create(
            company=self.company, chatbot=self.bot, visitor=self.visitor,
            status=ConversationStatus.WAITING_AGENT,
        )
        self.agent1 = User.objects.create_user(
            email="ag1@acme.com", password="pass12345", role=UserRole.AGENT, company=self.company
        )
        self.agent2 = User.objects.create_user(
            email="ag2@acme.com", password="pass12345", role=UserRole.AGENT, company=self.company
        )

    def test_assign_sets_active_agent(self):
        assign_conversation(self.conversation, self.agent1)
        self.conversation.refresh_from_db()
        self.assertEqual(self.conversation.status, ConversationStatus.ACTIVE_AGENT)
        self.assertTrue(
            ConversationAssignment.objects.filter(
                conversation=self.conversation, agent=self.agent1, is_active=True
            ).exists()
        )

    def test_transfer_moves_active_assignment(self):
        assign_conversation(self.conversation, self.agent1)
        transfer_conversation(self.conversation, self.agent2)

        active = ConversationAssignment.objects.get(
            conversation=self.conversation, is_active=True
        )
        self.assertEqual(active.agent, self.agent2)
        self.assertEqual(
            ConversationAssignment.objects.filter(
                conversation=self.conversation, is_active=True
            ).count(),
            1,
        )

    def test_close_resolves_conversation(self):
        assign_conversation(self.conversation, self.agent1)
        close_conversation(self.conversation)
        self.conversation.refresh_from_db()
        self.assertEqual(self.conversation.status, ConversationStatus.RESOLVED)
        self.assertFalse(
            ConversationAssignment.objects.filter(
                conversation=self.conversation, is_active=True
            ).exists()
        )

    def test_cross_company_assignment_blocked(self):
        from core.exceptions import TenantIsolationError

        other_company = Company.objects.create(name="Other", email="o@o.com")
        outsider = User.objects.create_user(
            email="out@o.com", password="pass12345", role=UserRole.AGENT, company=other_company
        )
        with self.assertRaises(TenantIsolationError):
            assign_conversation(self.conversation, outsider)
