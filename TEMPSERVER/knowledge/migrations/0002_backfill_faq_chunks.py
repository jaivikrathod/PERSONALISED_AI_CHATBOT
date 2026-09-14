"""Copy every live `questions` row into `knowledge_chunks` as `kind='faq'`.

`embed_text` = question, `content` = answer, embedding reused as-is (it was
computed from the bare question, which is exactly the FAQ embed_text).
`questions` stays the authoring surface; `knowledge.faq` keeps them in sync
from here on.

Frozen on purpose: no import of `knowledge.faq`, which will keep changing.
"""

import hashlib

from django.db import migrations

EMBEDDING_MODEL = "all-MiniLM-L6-v2"


def forwards(apps, schema_editor):
    Chatbot = apps.get_model("registry", "Chatbot")
    Question = apps.get_model("questions", "Question")
    Source = apps.get_model("knowledge", "KnowledgeSource")
    Document = apps.get_model("knowledge", "KnowledgeDocument")
    Chunk = apps.get_model("knowledge", "KnowledgeChunk")

    for chatbot in Chatbot.objects.all():
        source, _ = Source.objects.get_or_create(
            chatbot=chatbot,
            kind="faq",
            defaults={"company_id": chatbot.company_id, "name": "FAQ", "status": "ready"},
        )
        questions = Question.objects.filter(company_id=chatbot.company_id, is_archived=False)
        for question in questions.iterator():
            ref = f"question:{question.id}"
            if Document.objects.filter(source=source, external_ref=ref).exists():
                continue
            text = f"{question.question}\n\n{question.answer}"
            document = Document.objects.create(
                source=source,
                external_ref=ref,
                title=question.question[:500],
                raw_text=text,
                checksum=hashlib.sha256(text.encode()).hexdigest(),
                file_type="faq",
                status="ready",
            )
            has_embedding = question.embedding is not None
            Chunk.objects.create(
                chatbot=chatbot,
                source=source,
                document=document,
                ordinal=0,
                content=question.answer,
                embed_text=(question.question or "").strip(),
                embedding=question.embedding if has_embedding else None,
                embedding_model=EMBEDDING_MODEL if has_embedding else "",
                metadata={"kind": "faq", "question_id": question.id},
            )


class Migration(migrations.Migration):

    dependencies = [
        ("knowledge", "0001_initial"),
        ("questions", "0005_pgvector_embedding"),
        ("registry", "0002_backfill_chatbots"),
    ]

    operations = [
        migrations.RunPython(forwards, migrations.RunPython.noop),
    ]
