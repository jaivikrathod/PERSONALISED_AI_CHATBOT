"""Knowledge base models.

A KnowledgeBase groups QuestionAnswer (FAQ) pairs for one company. Each QA has a
companion QuestionEmbedding storing the pgvector representation of its question,
used for semantic retrieval at chat time.
"""

from django.conf import settings
from django.db import models
from pgvector.django import HnswIndex, VectorField

from core.models import BaseModel, SoftDeleteModel


class KnowledgeBase(BaseModel, SoftDeleteModel):
    company = models.ForeignKey(
        "companies.Company",
        on_delete=models.CASCADE,
        related_name="knowledge_bases",
    )
    title = models.CharField(max_length=255)
    description = models.TextField(blank=True)
    is_active = models.BooleanField(default=True)

    class Meta:
        db_table = "kb_knowledge_base"
        ordering = ["-created_at"]
        indexes = [models.Index(fields=["company", "is_active"])]

    def __str__(self):
        return self.title

    def get_object_company_id(self):
        return self.company_id


class QuestionAnswer(BaseModel, SoftDeleteModel):
    """A single FAQ entry (question + canonical answer)."""

    EMBEDDING_PENDING = "PENDING"
    EMBEDDING_READY = "READY"
    EMBEDDING_FAILED = "FAILED"
    EMBEDDING_STATUS = [
        (EMBEDDING_PENDING, "Pending"),
        (EMBEDDING_READY, "Ready"),
        (EMBEDDING_FAILED, "Failed"),
    ]

    knowledge_base = models.ForeignKey(
        KnowledgeBase,
        on_delete=models.CASCADE,
        related_name="qa_pairs",
    )
    question = models.TextField()
    answer = models.TextField()
    embedding_status = models.CharField(
        max_length=16, choices=EMBEDDING_STATUS, default=EMBEDDING_PENDING, db_index=True
    )

    class Meta:
        db_table = "kb_question_answer"
        ordering = ["-created_at"]
        indexes = [models.Index(fields=["knowledge_base", "embedding_status"])]

    def __str__(self):
        return self.question[:80]

    @property
    def company_id(self):
        return self.knowledge_base.company_id

    def get_object_company_id(self):
        return self.knowledge_base.company_id


class QuestionEmbedding(BaseModel):
    """pgvector embedding of a QuestionAnswer's question text."""

    qa = models.OneToOneField(
        QuestionAnswer,
        on_delete=models.CASCADE,
        related_name="embedding",
    )
    # Denormalised company FK so similarity search can filter by tenant cheaply.
    company = models.ForeignKey(
        "companies.Company",
        on_delete=models.CASCADE,
        related_name="question_embeddings",
    )
    embedding = VectorField(dimensions=settings.EMBEDDING_DIM)
    model_name = models.CharField(max_length=128, blank=True)

    class Meta:
        db_table = "kb_question_embedding"
        indexes = [
            # Approximate-nearest-neighbour index for fast cosine search.
            HnswIndex(
                name="qa_embedding_hnsw",
                fields=["embedding"],
                m=16,
                ef_construction=64,
                opclasses=["vector_cosine_ops"],
            ),
            models.Index(fields=["company"]),
        ]

    def __str__(self):
        return f"embedding<qa={self.qa_id}>"
