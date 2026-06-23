"""Analytics models.

ConversationMetrics is a per-company daily rollup (cheap to query for the
dashboard). UnansweredQuestion captures questions the bot answered with low
confidence so managers can curate them into the knowledge base.
"""

from django.db import models

from core.models import BaseModel


class ConversationMetrics(BaseModel):
    """A daily snapshot of conversation KPIs for one company."""

    company = models.ForeignKey(
        "companies.Company",
        on_delete=models.CASCADE,
        related_name="metrics",
    )
    date = models.DateField(db_index=True)

    total_conversations = models.PositiveIntegerField(default=0)
    resolved_by_ai = models.PositiveIntegerField(default=0)
    resolved_by_agent = models.PositiveIntegerField(default=0)
    escalated_chats = models.PositiveIntegerField(default=0)

    # Seconds.
    avg_response_time = models.FloatField(default=0.0)
    avg_resolution_time = models.FloatField(default=0.0)

    # [{question, count}, ...]
    top_questions = models.JSONField(default=list, blank=True)
    unanswered_questions = models.PositiveIntegerField(default=0)

    class Meta:
        db_table = "analytics_conversation_metrics"
        ordering = ["-date"]
        constraints = [
            models.UniqueConstraint(fields=["company", "date"], name="uniq_company_date_metrics"),
        ]

    def __str__(self):
        return f"Metrics<{self.company_id} {self.date}>"

    def get_object_company_id(self):
        return self.company_id


class UnansweredQuestion(BaseModel):
    """A question the bot could not confidently answer.

    Deduplicated per company by normalised text; each recurrence bumps
    occurrence_count. Managers convert these into QuestionAnswer entries.
    """

    company = models.ForeignKey(
        "companies.Company",
        on_delete=models.CASCADE,
        related_name="unanswered_questions",
    )
    question = models.TextField()
    normalized = models.CharField(max_length=512, db_index=True)
    occurrence_count = models.PositiveIntegerField(default=1)
    is_resolved = models.BooleanField(default=False, db_index=True)
    converted_qa = models.ForeignKey(
        "knowledge_base.QuestionAnswer",
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name="+",
    )

    class Meta:
        db_table = "analytics_unanswered_question"
        ordering = ["-occurrence_count", "-updated_at"]
        constraints = [
            models.UniqueConstraint(
                fields=["company", "normalized"], name="uniq_company_unanswered"
            ),
        ]

    def __str__(self):
        return f"{self.question[:60]} (x{self.occurrence_count})"

    def get_object_company_id(self):
        return self.company_id
