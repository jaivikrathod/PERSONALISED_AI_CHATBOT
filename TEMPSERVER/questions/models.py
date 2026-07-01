from django.db import models

from company.models import Company


class Question(models.Model):
    """A question/answer pair that belongs to a Company."""

    # `id` is added automatically by Django; declared explicitly to match spec.
    id = models.AutoField(primary_key=True)

    # FK stored in the DB column `company_id`. CASCADE removes questions when
    # their company is deleted. related_name lets us do `company.questions.all()`.
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
    # Whether this Q/A pair has been embedded and stored in the vector DB.
    # New rows default to False; vector_id is populated once stored.
    is_vectorized = models.BooleanField(default=False)
    vector_id = models.CharField(max_length=255, blank=True, null=True)

    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        db_table = "questions"
        ordering = ("-created_at",)

    def __str__(self):
        # Return the first 50 characters of the question for readable display.
        return self.question[:50]

    # --- Custom persistence behaviour --------------------------------------
    def save(self, *args, **kwargs):
        """Invalidate the vector whenever question/answer content changes.

        On update, if the `question` or `answer` text differs from what is
        stored in the DB, the previously computed embedding is stale, so we
        reset `is_vectorized=False` and clear `vector_id`. Changes to
        unrelated fields (e.g. is_archived) leave the vector state intact.
        New objects keep the model defaults (False / None).
        """
        if self.pk:
            # Compare only the content fields against the persisted row.
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
                self.vector_id = None
                # Ensure the reset is persisted even on partial saves.
                if "update_fields" in kwargs and kwargs["update_fields"] is not None:
                    kwargs["update_fields"] = set(kwargs["update_fields"]) | {
                        "is_vectorized",
                        "vector_id",
                    }

        super().save(*args, **kwargs)

    def delete(self, *args, **kwargs):
        """Remove the associated vector (if any) before deleting the row."""
        self._cleanup_vector()
        return super().delete(*args, **kwargs)

    def _cleanup_vector(self):
        """Best-effort removal of this question's vector from the vector DB.

        Imported lazily to avoid a circular import between `questions` and
        `vector_question` at module load time.
        """
        if self.vector_id:
            from vector_question.services import delete_vector

            delete_vector(self.vector_id)
