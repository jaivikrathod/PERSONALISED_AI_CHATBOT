"""Hybrid knowledge retrieval with a three-signal gate (WORKFLOW.md B4).

    query ─┬─ pgvector HNSW cosine, top 30 ──┐
           └─ Postgres full text, top 30 ────┴─ RRF Σ 1/(60+rank) ─ gate ─ top_k, token cap

Gate, per chatbot (`chatbots.policy`), all tuned by `evaluation.py`:
- `retrieval_floor`: vector candidates below this cosine are noise.
- `accept_threshold`: the best cosine must reach this, or nothing is returned.
- `margin_rule`: if rank 1 and rank 5 are within this relative margin, the query
  is off-domain (everything is equally, weakly similar) — unless the best score
  is already at `margin_bypass_score`.
- Lexical acceptance: a query carrying a *specific token* (a clause number,
  plan or SKU code — anything with a digit, or an all-caps word) is accepted
  when a full-text hit contains that token, even at low cosine. This is the
  case vectors are weak at and policy documents are full of.

Nothing clearing the gate returns zero chunks — never weak ones.
"""

from __future__ import annotations

import re
from dataclasses import dataclass, field
from functools import lru_cache

from django.contrib.postgres.search import SearchQuery, SearchRank
from django.db.models import F
from pgvector.django import CosineDistance

from vector_question.services import EMBEDDING_MODEL_NAME, build_retrieval_text, generate_embedding

from .models import KnowledgeChunk

RECALL_DEPTH = 30
RRF_K = 60
WORD = re.compile(r"[A-Za-z0-9]+(?:[.\-][A-Za-z0-9]+)*")


@dataclass
class Retrieval:
    chunks: list[dict]
    best_score: float | None = None
    accepted_by: str | None = None
    rejected_by: str | None = None
    diagnostics: dict = field(default_factory=dict)


@lru_cache(maxsize=1024)
def _cached_embedding(text: str) -> tuple:
    return tuple(generate_embedding(text))


def embed_query(query: str) -> list[float]:
    """Identical queries are embedded once per process (B4 step 1)."""
    return list(_cached_embedding(build_retrieval_text(query)))


def specific_tokens(query: str) -> set[str]:
    tokens = set()
    for word in WORD.findall(query):
        if any(ch.isdigit() for ch in word) or (len(word) >= 2 and word.isupper()):
            tokens.add(word.lower())
    return tokens


def _text_query(query: str) -> SearchQuery | None:
    words = WORD.findall(query)
    if not words:
        return None
    # OR the terms: customers ask in sentences, and AND-ing every word of a
    # sentence matches almost nothing. RRF ranking does the rest.
    return SearchQuery(" | ".join(words), search_type="raw", config="english")


def search(chatbot, query: str, top_k: int = 3, *, overrides: dict | None = None) -> Retrieval:
    overrides = overrides or {}

    def policy(key):
        return overrides[key] if key in overrides else chatbot.get_policy(key)

    chunks = KnowledgeChunk.objects.filter(chatbot=chatbot)

    probe = embed_query(query)
    vector_rows = list(
        chunks.filter(embedding__isnull=False, embedding_model=EMBEDDING_MODEL_NAME)
        .annotate(distance=CosineDistance("embedding", probe))
        .order_by("distance")
        .values_list("id", "distance")[:RECALL_DEPTH]
    )
    similarity = {chunk_id: 1.0 - float(distance) for chunk_id, distance in vector_rows}
    floor = policy("retrieval_floor")
    vector_ranked = [chunk_id for chunk_id, _ in vector_rows if similarity[chunk_id] >= floor]

    text_query = _text_query(query)
    text_ranked = []
    if text_query is not None:
        text_ranked = list(
            chunks.filter(content_tsv=text_query)
            .annotate(rank=SearchRank(F("content_tsv"), text_query))
            .order_by("-rank", "id")
            .values_list("id", flat=True)[:RECALL_DEPTH]
        )

    fused: dict[int, float] = {}
    for ranked in (vector_ranked, text_ranked):
        for rank, chunk_id in enumerate(ranked, start=1):
            fused[chunk_id] = fused.get(chunk_id, 0.0) + 1.0 / (RRF_K + rank)
    order = sorted(fused, key=lambda cid: (-fused[cid], cid))

    best = max(similarity.values(), default=None)
    scores = sorted(similarity.values(), reverse=True)
    result = Retrieval(chunks=[], best_score=best, diagnostics={
        "vector_candidates": len(vector_ranked),
        "text_candidates": len(text_ranked),
    })

    specific = specific_tokens(query)
    content = {}
    if specific and text_ranked:
        content = {
            cid: f"{embed} {body}".lower()
            for cid, embed, body in chunks.filter(id__in=text_ranked).values_list("id", "embed_text", "content")
        }
    lexical_hits = {cid for cid in text_ranked if any(t in content.get(cid, "") for t in specific)}

    if best is not None and best >= policy("accept_threshold"):
        margin = (scores[0] - scores[4]) / scores[0] if len(scores) >= 5 and scores[0] > 0 else None
        if margin is not None and best < policy("margin_bypass_score") and margin < policy("margin_rule"):
            result.rejected_by = "margin_rule"
        else:
            result.accepted_by = "semantic"
    if result.accepted_by is None and lexical_hits:
        result.accepted_by, result.rejected_by = "lexical", None

    if result.accepted_by is None:
        result.rejected_by = result.rejected_by or "accept_threshold"
        return result

    eligible = [
        cid for cid in order
        if (cid in similarity and similarity[cid] >= floor and result.accepted_by == "semantic")
        or cid in lexical_hits
    ]

    ceiling = policy("max_context_tokens")
    selected, used = [], 0
    by_id = KnowledgeChunk.objects.select_related("document", "source").in_bulk(eligible[: top_k * 3])
    for cid in eligible:
        chunk = by_id.get(cid)
        if chunk is None:
            continue
        cost = chunk.token_count or max(1, len(chunk.content) // 4)
        if selected and used + cost > ceiling:
            break
        selected.append(chunk)
        used += cost
        if len(selected) >= top_k:
            break

    result.chunks = [_shape(chunk, similarity.get(chunk.id)) for chunk in selected]
    return result


def _shape(chunk, score) -> dict:
    meta = chunk.metadata or {}
    shaped = {
        "title": chunk.document.title,
        "content": chunk.content,
        "score": round(score, 4) if score is not None else None,
    }
    if meta.get("kind") != "faq":
        shaped["section"] = meta.get("section_heading") or None
        shaped["page"] = meta.get("page")
    return shaped
