from django.db import models

from company.models import Company


class VectorJob(models.Model):
    """Tracks a single vectorization run for a Company.

    One row is created each time vectorization is triggered for a company.
    It records progress counters and status so the operation is observable
    and can later be driven asynchronously (Celery/RabbitMQ/Redis) without
    changing this schema.
    """

    class Status(models.TextChoices):
        PENDING = "pending", "Pending"
        PROCESSING = "processing", "Processing"
        COMPLETED = "completed", "Completed"
        FAILED = "failed", "Failed"

    id = models.AutoField(primary_key=True)

    company = models.ForeignKey(
        Company,
        on_delete=models.CASCADE,
        related_name="vector_jobs",
    )

    status = models.CharField(
        max_length=20,
        choices=Status.choices,
        default=Status.PENDING,
    )

    # Progress counters, updated as the job runs.
    total_questions = models.PositiveIntegerField(default=0)
    processed_questions = models.PositiveIntegerField(default=0)
    failed_questions = models.PositiveIntegerField(default=0)

    # Timing + diagnostics.
    started_at = models.DateTimeField(blank=True, null=True)
    completed_at = models.DateTimeField(blank=True, null=True)
    error_message = models.TextField(blank=True, null=True)

    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        db_table = "vector_jobs"
        ordering = ["-created_at"]

    def __str__(self):
        return f"VectorJob #{self.id} ({self.company_id}) - {self.status}"
