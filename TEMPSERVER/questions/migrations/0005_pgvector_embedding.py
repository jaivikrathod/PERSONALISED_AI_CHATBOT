"""Move `Question.embedding` from JSONB to a real pgvector column.

The old column stored the vector as JSON, which cannot be indexed, so every
chat message triggered a full scan plus a Python cosine loop. Converting to
`vector(384)` lets Postgres do the ranking against an HNSW index.

Existing embeddings are dropped rather than cast. Two reasons: the JSON->vector
cast is not something we want to hand-write per row, and the vectors are stale
anyway — `build_retrieval_text` now embeds the question alone rather than a
"Question: ... Answer: ..." block, so every row has to be regenerated to be
comparable with incoming queries. Rows are marked `is_vectorized=False`, which
is exactly what the existing "Convert to vector" button already knows how to
drain.
"""

import pgvector.django
from django.db import migrations, models
from pgvector.django import VectorExtension


class Migration(migrations.Migration):

    dependencies = [
        ("questions", "0004_unansweredmessage"),
    ]

    operations = [
        # CREATE EXTENSION IF NOT EXISTS vector
        VectorExtension(),
        migrations.RunSQL(
            sql="""
                ALTER TABLE questions
                    ALTER COLUMN embedding TYPE vector(384) USING NULL;
            """,
            reverse_sql="""
                ALTER TABLE questions
                    ALTER COLUMN embedding TYPE jsonb USING NULL;
            """,
            state_operations=[
                migrations.AlterField(
                    model_name="question",
                    name="embedding",
                    field=pgvector.django.VectorField(
                        blank=True, dimensions=384, null=True
                    ),
                ),
            ],
        ),
        migrations.AddIndex(
            model_name="question",
            index=pgvector.django.HnswIndex(
                ef_construction=64,
                fields=["embedding"],
                m=16,
                name="questions_embedding_hnsw",
                opclasses=["vector_cosine_ops"],
            ),
        ),
        migrations.AddIndex(
            model_name="question",
            index=models.Index(
                fields=["company", "is_archived", "is_vectorized"],
                name="questions_company_state_idx",
            ),
        ),
        # Last, deliberately: an UPDATE queues trigger events that block
        # CREATE INDEX inside the same transaction.
        migrations.RunSQL(
            sql="UPDATE questions SET is_vectorized = false;",
            reverse_sql="UPDATE questions SET is_vectorized = false;",
        ),
    ]
