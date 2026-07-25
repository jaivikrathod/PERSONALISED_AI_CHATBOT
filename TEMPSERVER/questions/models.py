from django.db import models

from company.models import Company


class Question(models.Model):
    """A question/answer pair that belongs to a Company."""

    id = models.AutoField(primary_key=True)

    company = models.ForeignKey(
        Company,
        on_delete=models.CASCADE,
        related_name="questions",
    )

    question = models.TextField()
    answer = models.TextField()

    # Soft-delete flag: archived rows are hidden from the default API queryset.
    is_archived = models.BooleanField(default=False)

    # --- Vectorization state ------------------------------------------------
    # `is_vectorized` says whether the embedding has been generated.
    # `embedding` stores the vector itself (a list of floats) right here on the
    # row, so there is no separate vector store to keep in sync.
    is_vectorized = models.BooleanField(default=False)
    embedding = models.JSONField(blank=True, null=True)

    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        db_table = "questions"
        ordering = ("-created_at",)

    def __str__(self):
        return self.question[:50]

    def save(self, *args, **kwargs):
        """Reset the embedding whenever the question/answer text changes.

        If the content changed, the stored embedding is stale, so we clear it
        and mark the row as needing re-vectorization. Editing unrelated fields
        (e.g. is_archived) leaves the embedding untouched.
        """
        if self.pk:
            previous = (
                Question.objects.filter(pk=self.pk)
                .values("question", "answer")
                .first()
            )
            if previous and (
                previous["question"] != self.question
                or previous["answer"] != self.answer
            ):
                self.is_vectorized = False
                self.embedding = None
                if kwargs.get("update_fields") is not None:
                    kwargs["update_fields"] = set(kwargs["update_fields"]) | {
                        "is_vectorized",
                        "embedding",
                    }

        super().save(*args, **kwargs)


class UnansweredMessage(models.Model):
    """A customer message the chatbot could not answer from the FAQ database.

    When the best FAQ match scores below the confidence threshold, the raw
    customer message is parked here so a human can later supply an answer,
    which turns it into a real Question and vectorizes it.
    """

    id = models.AutoField(primary_key=True)

    message = models.TextField()

    company = models.ForeignKey(
        Company,
        on_delete=models.CASCADE,
        related_name="unanswered_messages",
    )

    timestamp = models.DateTimeField(auto_now_add=True)

    class Meta:
        db_table = "unanswered_messages"
        ordering = ("-timestamp",)

    def __str__(self):
        return self.message[:50]
