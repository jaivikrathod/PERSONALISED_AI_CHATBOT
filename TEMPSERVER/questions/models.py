from django.db import models
from pgvector.django import HnswIndex, VectorField

from company.models import Company

# all-MiniLM-L6-v2 output width. Changing the embedding model changes this
# column's type, so a swap is a migration, not a config flip.
EMBEDDING_DIMENSIONS = 384


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
    # `embedding` is a real pgvector column, not JSON: that is what lets the
    # similarity search run as an indexed query instead of a Python loop over
    # every row in the table.
    is_vectorized = models.BooleanField(default=False)
    embedding = VectorField(dimensions=EMBEDDING_DIMENSIONS, blank=True, null=True)

    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        db_table = "questions"
        ordering = ("-created_at",)
        indexes = [
            # Cosine HNSW: embeddings are normalized at generation time, so
            # cosine and inner product rank identically — cosine is kept
            # because the stored scores are read by humans in the logs.
            HnswIndex(
                name="questions_embedding_hnsw",
                fields=["embedding"],
                m=16,
                ef_construction=64,
                opclasses=["vector_cosine_ops"],
            ),
            models.Index(
                fields=["company", "is_archived", "is_vectorized"],
                name="questions_company_state_idx",
            ),
        ]

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
