"""Document ingestion: extract → chunk → embed → store, with progress."""

from __future__ import annotations

import hashlib

from django.db import transaction
from django.utils import timezone

from vector_question.services import EMBEDDING_MODEL_NAME, count_tokens, generate_embeddings

from . import jobs
from .chunking import chunk_blocks
from .extraction import extract, file_type_for, raw_text
from .models import IngestionJob, KnowledgeChunk, KnowledgeDocument, KnowledgeSource

EMBED_BATCH = 32


def checksum(content: bytes) -> str:
    return hashlib.sha256(content).hexdigest()


def submit_document(source: KnowledgeSource, filename: str, content: bytes) -> tuple[KnowledgeDocument, IngestionJob | None]:
    """Queue a document. Returns (document, job); job is None when unchanged."""
    digest = checksum(content)
    document = KnowledgeDocument.objects.filter(source=source, external_ref=filename).first()
    if document and document.checksum == digest and document.status == KnowledgeDocument.Status.READY:
        return document, None

    with transaction.atomic():
        document, _ = KnowledgeDocument.objects.update_or_create(
            source=source,
            external_ref=filename,
            defaults={
                "checksum": digest,
                "file_type": file_type_for(filename) or "",
                "status": KnowledgeDocument.Status.PENDING,
                "error": "",
            },
        )
        source.status = KnowledgeSource.Status.INDEXING
        source.save(update_fields=["status", "updated_at"])
        job = IngestionJob.objects.create(
            company_id=source.company_id,
            source=source,
            document=document,
            kind=IngestionJob.Kind.DOCUMENT,
            payload=content,
            filename=filename,
            message="Queued",
        )
        jobs.enqueue(job)
    job.refresh_from_db()
    return document, job


def ingest_document(job: IngestionJob) -> None:
    document, source = job.document, job.source

    jobs.report(job, message="Extracting text")
    title, blocks = extract(job.filename, bytes(job.payload))

    jobs.report(job, message="Splitting into passages")
    pieces = chunk_blocks(blocks, count_tokens)
    # One step per embedding batch, plus one for storing.
    batches = [pieces[i : i + EMBED_BATCH] for i in range(0, len(pieces), EMBED_BATCH)]
    jobs.report(job, done=0, total=len(batches) + 1, message=f"Embedding {len(pieces)} passages")

    # The section heading leads the chunk: it is where clause numbers and plan
    # names live, so both full-text and the embedding must see it.
    texts = [
        f"{piece.section_heading}\n\n{piece.content}" if piece.section_heading else piece.content
        for piece in pieces
    ]
    embeddings = []
    for number, start in enumerate(range(0, len(texts), EMBED_BATCH), start=1):
        embeddings.extend(generate_embeddings(texts[start : start + EMBED_BATCH]))
        jobs.report(job, done=number)

    jobs.report(job, message="Saving")
    with transaction.atomic():
        document.chunks.all().delete()
        KnowledgeChunk.objects.bulk_create(
            KnowledgeChunk(
                chatbot_id=source.chatbot_id,
                source=source,
                document=document,
                ordinal=ordinal,
                content=text,
                embed_text=text,
                embedding=embedding,
                embedding_model=EMBEDDING_MODEL_NAME,
                token_count=count_tokens(text),
                metadata={
                    "document_title": title,
                    "section_heading": piece.section_heading,
                    "page": piece.page,
                },
            )
            for ordinal, (piece, text, embedding) in enumerate(zip(pieces, texts, embeddings))
        )
        document.title = title
        document.raw_text = raw_text(blocks)
        document.status = KnowledgeDocument.Status.READY
        document.error = ""
        document.save()
        source.status = KnowledgeSource.Status.READY
        source.last_indexed_at = timezone.now()
        source.save(update_fields=["status", "last_indexed_at", "updated_at"])
    jobs.report(job, message=f"Indexed {len(pieces)} passages")


def mark_failed(job: IngestionJob, error: str) -> None:
    if job.document_id:
        KnowledgeDocument.objects.filter(id=job.document_id).update(
            status=KnowledgeDocument.Status.FAILED, error=error[:2000]
        )
    KnowledgeSource.objects.filter(id=job.source_id).update(status=KnowledgeSource.Status.FAILED)


HANDLERS = {
    IngestionJob.Kind.DOCUMENT: ingest_document,
}
