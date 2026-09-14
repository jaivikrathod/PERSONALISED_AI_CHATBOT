"""Chunker: heading- and paragraph-aware, never mid-sentence.

**Sizing deviates from TASKS.md on purpose.** The task says ~300–500 tokens,
but all-MiniLM-L6-v2 reads at most 256 wordpiece tokens and silently ignores
the rest, so a 500-token chunk would be embedded from its first half only.
Chunks therefore target ~200 and never exceed `MAX_TOKENS` (240, leaving room
for the model's special tokens), with ~15% overlap. If the embedding model
changes, these constants change with it.

The one exception to "never mid-sentence": a single sentence longer than
`MAX_TOKENS` is split at word boundaries, since it cannot be embedded whole.
"""

from __future__ import annotations

import re
from dataclasses import dataclass
from typing import Callable

from .extraction import Block

TARGET_TOKENS = 200
MAX_TOKENS = 240
OVERLAP_RATIO = 0.15

SENTENCE_END = re.compile(r"(?<=[.!?])[\"')\]]*\s+(?=[\"'(\[]?[A-Z0-9])")


@dataclass
class Unit:
    text: str
    tokens: int
    page: int | None
    ends_paragraph: bool


@dataclass
class Piece:
    content: str
    section_heading: str
    page: int | None
    token_count: int


def split_sentences(text: str) -> list[str]:
    return [s.strip() for s in SENTENCE_END.split(text.strip()) if s.strip()]


def chunk_blocks(
    blocks: list[Block],
    count_tokens: Callable[[str], int],
    *,
    target: int = TARGET_TOKENS,
    maximum: int = MAX_TOKENS,
    overlap_ratio: float = OVERLAP_RATIO,
) -> list[Piece]:
    pieces: list[Piece] = []
    for heading, section in _sections(blocks):
        # Ingestion prefixes each chunk with its heading ("Clause 4.2 Damaged
        # items") so clause numbers are searchable; reserve room for it.
        reserved = count_tokens(heading) + 2 if heading else 0
        budget = max(maximum - reserved, maximum // 2)
        section_target = min(target, budget)
        units = []
        for block in section:
            sentences = split_sentences(block.text)
            for index, sentence in enumerate(sentences):
                last = index == len(sentences) - 1
                for part in _fit(sentence, count_tokens, budget):
                    units.append(Unit(part, count_tokens(part), block.page, last))
        pieces.extend(_pack(units, heading, section_target, budget, overlap_ratio))
    return pieces


def _sections(blocks):
    current, heading = [], None
    for block in blocks:
        if heading is not None and block.heading != heading and current:
            yield heading, current
            current = []
        heading = block.heading
        current.append(block)
    if current:
        yield heading or "", current


def _fit(sentence, count_tokens, maximum):
    if count_tokens(sentence) <= maximum:
        return [sentence]
    parts, words = [], []
    for word in sentence.split():
        if words and count_tokens(" ".join(words + [word])) > maximum:
            parts.append(" ".join(words))
            words = []
        words.append(word)
    if words:
        parts.append(" ".join(words))
    return parts


def _pack(units, heading, target, maximum, overlap_ratio):
    pieces, current = [], []
    overlap_budget = int(maximum * overlap_ratio)

    def total(items):
        return sum(u.tokens for u in items)

    def emit(items):
        pieces.append(
            Piece(
                content=" ".join(u.text for u in items),
                section_heading=heading,
                page=items[0].page,
                token_count=total(items),
            )
        )

    def overlap_from(items):
        carried = []
        for unit in reversed(items):
            if total(carried) + unit.tokens > overlap_budget:
                break
            carried.insert(0, unit)
        return carried

    for unit in units:
        if current and total(current) + unit.tokens > maximum:
            emit(current)
            carried = overlap_from(current)
            current = carried if total(carried) + unit.tokens <= maximum else []
        current.append(unit)
        # Prefer to close at a paragraph boundary once the chunk is big enough.
        if unit.ends_paragraph and total(current) >= target:
            emit(current)
            current = overlap_from(current)

    fresh = [u for u in current if not pieces or u.text not in pieces[-1].content]
    if fresh:
        emit(current)
    return pieces
