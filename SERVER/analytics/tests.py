from unittest.mock import patch

from rest_framework.test import APITestCase

from companies.models import Company
from knowledge_base.models import KnowledgeBase

from .models import UnansweredQuestion
from .services import convert_unanswered_to_faq, record_unanswered_question


class UnansweredQuestionTests(APITestCase):
    def setUp(self):
        self.company = Company.objects.create(name="Acme", email="a@a.com")

    def test_record_dedupes_and_counts(self):
        record_unanswered_question(self.company.id, "How do I cancel?")
        record_unanswered_question(self.company.id, "  how do I CANCEL?  ")
        self.assertEqual(UnansweredQuestion.objects.count(), 1)
        self.assertEqual(UnansweredQuestion.objects.first().occurrence_count, 2)

    @patch("knowledge_base.signals.generate_qa_embedding")
    def test_convert_to_faq_marks_resolved(self, _mock_task):
        kb = KnowledgeBase.objects.create(company=self.company, title="FAQ")
        unanswered = record_unanswered_question(self.company.id, "Refund policy?")
        qa = convert_unanswered_to_faq(unanswered, kb, "We refund within 30 days.")

        unanswered.refresh_from_db()
        self.assertTrue(unanswered.is_resolved)
        self.assertEqual(unanswered.converted_qa_id, qa.id)

    @patch("knowledge_base.signals.generate_qa_embedding")
    def test_convert_blocks_cross_company_kb(self, _mock_task):
        from core.exceptions import TenantIsolationError

        other = Company.objects.create(name="Other", email="o@o.com")
        kb_other = KnowledgeBase.objects.create(company=other, title="Other FAQ")
        unanswered = record_unanswered_question(self.company.id, "X?")
        with self.assertRaises(TenantIsolationError):
            convert_unanswered_to_faq(unanswered, kb_other, "ans")
