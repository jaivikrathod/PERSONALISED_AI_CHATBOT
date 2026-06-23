"""Tests for the knowledge base: CRUD, soft delete, bulk parsing, search service."""

import io
from unittest.mock import patch

from django.contrib.auth import get_user_model
from rest_framework import status
from rest_framework.test import APITestCase

from companies.models import Company
from core.enums import CompanyStatus, UserRole

from .models import KnowledgeBase, QuestionAnswer
from .services import BulkUploadService

User = get_user_model()


class KnowledgeBaseTests(APITestCase):
    def setUp(self):
        self.company = Company.objects.create(name="Acme", email="a@a.com", status=CompanyStatus.ACTIVE)
        self.admin = User.objects.create_user(
            email="admin@acme.com", password="pass12345",
            role=UserRole.COMPANY_ADMIN, company=self.company,
        )
        self.client.force_authenticate(self.admin)

    def test_create_knowledge_base_is_company_scoped(self):
        resp = self.client.post(
            "/api/v1/kb/knowledge-bases/", {"title": "Billing FAQ"}, format="json"
        )
        self.assertEqual(resp.status_code, status.HTTP_201_CREATED)
        kb = KnowledgeBase.objects.get(uuid=resp.data["uuid"])
        self.assertEqual(kb.company_id, self.company.id)

    def test_soft_delete_hides_kb_but_keeps_row(self):
        kb = KnowledgeBase.objects.create(company=self.company, title="Temp")
        resp = self.client.delete(f"/api/v1/kb/knowledge-bases/{kb.uuid}/")
        self.assertEqual(resp.status_code, status.HTTP_204_NO_CONTENT)
        self.assertFalse(KnowledgeBase.objects.filter(pk=kb.pk).exists())
        self.assertTrue(KnowledgeBase.all_objects.filter(pk=kb.pk).exists())


class BulkUploadServiceTests(APITestCase):
    def setUp(self):
        self.company = Company.objects.create(name="Acme", email="a@a.com")
        self.kb = KnowledgeBase.objects.create(company=self.company, title="FAQ")

    @patch("knowledge_base.signals.generate_qa_embedding")
    def test_csv_ingest_creates_qa_rows(self, _mock_task):
        csv = b"question,answer\nHow to reset password?,Click forgot password.\n"
        created = BulkUploadService(self.kb).ingest(io.BytesIO(csv), "faq.csv")
        self.assertEqual(len(created), 1)
        self.assertEqual(QuestionAnswer.objects.filter(knowledge_base=self.kb).count(), 1)

    def test_missing_columns_raise(self):
        bad = b"q,a\nx,y\n"
        with self.assertRaises(ValueError):
            BulkUploadService(self.kb).ingest(io.BytesIO(bad), "faq.csv")
