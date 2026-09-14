"""Mirror `questions` into `knowledge_chunks` as `kind='faq'`.

`questions` stays the authoring surface (Part D rule 6). This runs on every
save, and reuses the question's own embedding — `build_retrieval_text` of the
question is exactly the FAQ `embed_text` — so no model runs in the request.
A question that is not vectorized yet still gets a chunk: full-text recall
finds it, vector recall picks it up once "Vectorize" fills the embedding.
"""

from __future__ import annotations

import hashlib

from vector_question.services import EMBEDDING_MODEL_NAME, build_retrieval_text

from .models import KnowledgeChunk, KnowledgeDocument, KnowledgeSource


def faq_source(chatbot) -> KnowledgeSource:
    source, _ = KnowledgeSource.objects.get_or_create(
        chatbot=chatbot,
        kind=KnowledgeSource.Kind.FAQ,
        defaults={"company_id": chatbot.company_id, "name": "FAQ", "status": KnowledgeSource.Status.READY},
    )
    return source


def question_ref(question_id) -> str:
    return f"question:{question_id}"


def sync_question(question) -> None:
    from registry.models import Chatbot

    for chatbot in Chatbot.objects.filter(company_id=question.company_id):
        source = faq_source(chatbot)
        ref = question_ref(question.id)
        if question.is_archived:
            KnowledgeDocument.objects.filter(source=source, external_ref=ref).delete()
            continue

        text = f"{question.question}\n\n{question.answer}"
        document, _ = KnowledgeDocument.objects.update_or_create(
            source=source,
            external_ref=ref,
            defaults={
                "title": question.question[:500],
                "raw_text": text,
                "checksum": hashlib.sha256(text.encode()).hexdigest(),
                "file_type": "faq",
                "status": KnowledgeDocument.Status.READY,
            },
        )
        has_embedding = question.embedding is not None
        KnowledgeChunk.objects.update_or_create(
            document=document,
            ordinal=0,
            defaults={
                "chatbot": chatbot,
                "source": source,
                "content": question.answer,
                "embed_text": build_retrieval_text(question.question),
                "embedding": question.embedding if has_embedding else None,
                "embedding_model": EMBEDDING_MODEL_NAME if has_embedding else "",
                "metadata": {"kind": "faq", "question_id": question.id},
            },
        )


def remove_question(question) -> None:
    KnowledgeDocument.objects.filter(
        source__kind=KnowledgeSource.Kind.FAQ,
        source__company_id=question.company_id,
        external_ref=question_ref(question.id),
    ).delete()


def backfill_chatbot(chatbot) -> None:
    """A bot created after its company already had FAQs."""
    from questions.models import Question

    for question in Question.objects.filter(company_id=chatbot.company_id, is_archived=False):
        sync_question(question)
