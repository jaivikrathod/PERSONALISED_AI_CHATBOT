"""Regression tests for the Phase 0 retrieval work.

Three defects are pinned here:

  * embeddings lived in a JSONField and were scored by a Python loop over every
    row, so there was no index to use;
  * rows were embedded as a "Question: ... Answer: ..." block while queries were
    embedded as bare sentences, which depressed every similarity score;
  * the confidence threshold was 0.90, far above anything all-MiniLM-L6-v2
    produces for a paraphrase, so rephrased questions escalated to a human.

The calibration tests assert against `DEFAULT_CHAT_CONFIDENCE_THRESHOLD` rather
than the live setting on purpose: they are checking that the *recommended*
value separates answerable from unanswerable questions, and must not start
passing or failing because someone edited `.env`.
"""

from django.conf import settings
from django.test import TestCase
from pgvector.django import CosineDistance

from company.models import Company
from questions.models import EMBEDDING_DIMENSIONS, Question
from vector_question.services import build_retrieval_text, generate_embedding

# Measured bands for all-MiniLM-L6-v2 with bare-question index text. The gap
# between the last two is the only room a single cosine threshold has to work
# in, which is why the LLM's own `is_answer_found` is the real decision.
EXACT_FLOOR = 0.95
PARAPHRASE_FLOOR = 0.40
UNRELATED_CEILING = 0.40


class RetrievalTextTests(TestCase):
    def test_index_text_is_the_bare_question(self):
        """Index and query text must be the same shape to be comparable."""
        self.assertEqual(
            build_retrieval_text("  What is your refund policy?  "),
            "What is your refund policy?",
        )

    def test_empty_input_is_handled(self):
        self.assertEqual(build_retrieval_text(None), "")


class ThresholdConfigTests(TestCase):
    def test_default_threshold_sits_inside_the_measured_gap(self):
        self.assertGreaterEqual(
            settings.DEFAULT_CHAT_CONFIDENCE_THRESHOLD, UNRELATED_CEILING - 0.05
        )
        self.assertLessEqual(
            settings.DEFAULT_CHAT_CONFIDENCE_THRESHOLD, PARAPHRASE_FLOOR + 0.04
        )

    def test_deployment_is_not_configured_above_the_paraphrase_floor(self):
        """A threshold above ~0.44 sends genuine paraphrases to a human."""
        self.assertLessEqual(
            settings.CHAT_CONFIDENCE_THRESHOLD,
            PARAPHRASE_FLOOR + 0.04,
            "CHAT_CONFIDENCE_THRESHOLD is set high enough that rephrased "
            "questions will escalate instead of being answered.",
        )


class VectorSearchTests(TestCase):
    """Exercises the real pgvector column and the real embedding model."""

    @classmethod
    def setUpTestData(cls):
        cls.company = Company.objects.create(
            name="Acme", email="acme@example.com", mobile="1", address="a"
        )
        cls.other = Company.objects.create(
            name="Other", email="other@example.com", mobile="2", address="b"
        )

        cls.faqs = [
            "What is your refund policy?",
            "How do I reset my password?",
            "What are your business hours?",
            "Do you ship internationally?",
        ]
        for text in cls.faqs:
            cls._add(cls.company, text, f"Answer to {text}")
        # Same question, different tenant — the isolation canary.
        cls._add(cls.other, cls.faqs[0], "Other company's answer.")

    @staticmethod
    def _add(company, text, answer):
        question = Question.objects.create(
            company=company, question=text, answer=answer
        )
        question.embedding = generate_embedding(build_retrieval_text(text))
        question.is_vectorized = True
        question.save(update_fields=["embedding", "is_vectorized"])
        return question

    def search(self, company, query, limit=3):
        """Mirrors ChatConsumer._top_matches: indexed, ordered by Postgres."""
        probe = generate_embedding(build_retrieval_text(query))
        rows = (
            Question.objects.filter(
                company=company, is_archived=False, is_vectorized=True
            )
            .annotate(distance=CosineDistance("embedding", probe))
            .order_by("distance")
            .values_list("distance", "question")[:limit]
        )
        return [(1.0 - float(distance), question) for distance, question in rows]

    def test_embedding_column_has_the_expected_width(self):
        stored = Question.objects.filter(company=self.company).first()
        self.assertEqual(len(stored.embedding), EMBEDDING_DIMENSIONS)

    def test_exact_question_scores_near_one(self):
        """The asymmetry fix: an identical query is no longer penalised."""
        similarity, question = self.search(self.company, self.faqs[0])[0]
        self.assertEqual(question, self.faqs[0])
        self.assertGreater(similarity, EXACT_FLOOR)

    def test_paraphrases_match_the_right_faq_above_the_threshold(self):
        cases = [
            ("Can I get my money back?", self.faqs[0]),
            ("how do refunds work", self.faqs[0]),
            ("I forgot my password, what now?", self.faqs[1]),
            ("when are you open", self.faqs[2]),
            ("can you deliver to Germany", self.faqs[3]),
        ]
        for query, expected in cases:
            with self.subTest(query=query):
                similarity, question = self.search(self.company, query)[0]
                self.assertEqual(question, expected)
                self.assertGreater(
                    similarity,
                    settings.DEFAULT_CHAT_CONFIDENCE_THRESHOLD,
                    f"{query!r} scored {similarity:.4f} and would escalate",
                )

    def test_unrelated_questions_stay_below_the_threshold(self):
        for query in (
            "What time does the moon rise?",
            "Who won the 1998 world cup?",
            "asdkjh qwe zxc",
        ):
            with self.subTest(query=query):
                similarity, _ = self.search(self.company, query)[0]
                self.assertLess(
                    similarity,
                    settings.DEFAULT_CHAT_CONFIDENCE_THRESHOLD,
                    f"{query!r} scored {similarity:.4f} and would be answered",
                )

    def test_search_never_crosses_companies(self):
        results = self.search(self.company, self.faqs[0], limit=10)
        self.assertEqual(len(results), len(self.faqs))

        matched = Question.objects.filter(
            company=self.company, question=results[0][1]
        ).first()
        self.assertIsNotNone(matched)
        self.assertNotEqual(matched.answer, "Other company's answer.")

    def test_archived_questions_are_excluded(self):
        Question.objects.filter(company=self.company).update(is_archived=True)
        self.assertEqual(self.search(self.company, self.faqs[0]), [])

    def test_editing_a_question_invalidates_its_embedding(self):
        question = Question.objects.get(company=self.company, question=self.faqs[1])
        question.question = "How do I change my password?"
        question.save()

        question.refresh_from_db()
        self.assertFalse(question.is_vectorized)
        self.assertIsNone(question.embedding)
