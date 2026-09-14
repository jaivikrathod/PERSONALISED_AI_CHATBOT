"""One executor per `Tool.tool_type` (WORKFLOW.md B1, Part D rule 7).

An executor receives the server-side `TurnContext` and *validated* arguments.
It never reads a tenant from its arguments: `ctx.company_id` / `ctx.chatbot`
are the only tenant it knows (G1). A new capability is a new entry in
`EXECUTORS`, never a branch in the orchestrator.
"""

from __future__ import annotations

import logging
from dataclasses import dataclass, field
from typing import Any, Callable

from chat.services import agent_group, flag_agent_needed, send_to_group_sync, session_event
from datasources.search import structured_search
from knowledge.retrieval import search as search_knowledge_chunks
from questions.models import UnansweredMessage
from registry.models import Tool

from .results import ExecutorResult

logger = logging.getLogger(__name__)


@dataclass
class TurnContext:
    """Everything bound to a turn at resolve time (B5 step 1)."""

    session: Any
    chatbot: Any
    company_id: int
    user_message: str
    # Per-turn facts the transport frame needs; never read by a gate.
    handed_off: bool = False
    parked: bool = False
    sources: list[dict] = field(default_factory=list)
    best_score: float | None = None


def park_unanswered(ctx: TurnContext) -> None:
    """Queue the customer's message for a human to answer later (once per turn)."""
    if ctx.parked:
        return
    UnansweredMessage.objects.create(company_id=ctx.company_id, message=ctx.user_message)
    ctx.parked = True


def hand_off(ctx: TurnContext, reason: str) -> dict:
    """Flag the session for a human and ping a free agent's console.

    Shared by the `request_human_agent` tool and the server-side safety net, so
    both paths escalate identically.
    """
    logger.info("Session #%s handed off: %s", ctx.session.id, reason)
    park_unanswered(ctx)
    agent = flag_agent_needed(ctx.session)
    if agent is not None:
        send_to_group_sync(
            agent_group(agent.id),
            {"type": "chat.assigned", "session": session_event(ctx.session, agent_id=agent.id)},
        )
    ctx.handed_off = True
    return {"status": "handed_off", "agent_assigned": agent is not None}


def search_knowledge(ctx: TurnContext, tool: Tool, args: dict) -> ExecutorResult:
    """Hybrid retrieval over FAQ and document chunks behind the B4 gate.

    An empty result is a signal the model acts on, not a failure — three weak
    passages would be worse, because a capable model tries to answer from them.
    """
    query = args["query"]
    retrieval = search_knowledge_chunks(ctx.chatbot, query, args["top_k"])
    if retrieval.best_score is not None:
        ctx.best_score = (
            retrieval.best_score if ctx.best_score is None else max(ctx.best_score, retrieval.best_score)
        )
    audit = {
        "accepted_by": retrieval.accepted_by,
        "rejected_by": retrieval.rejected_by,
        "best_score": retrieval.best_score,
        **retrieval.diagnostics,
    }

    if not retrieval.chunks:
        park_unanswered(ctx)
        return ExecutorResult(
            result={"chunks": [], "reason": "no_relevant_content"},
            summary=f"No relevant content for {query!r}.",
            rows_returned=0,
            audit=audit,
        )

    ctx.sources.extend({"question": c["title"], "score": c["score"]} for c in retrieval.chunks)
    return ExecutorResult(
        result={"chunks": retrieval.chunks},
        summary=f"Returned {len(retrieval.chunks)} passage(s) for {query!r}: "
        + "; ".join(c["title"] for c in retrieval.chunks),
        rows_returned=len(retrieval.chunks),
        audit=audit,
    )


def request_human_agent(ctx: TurnContext, tool: Tool, args: dict) -> ExecutorResult:
    result = hand_off(ctx, f"model: {args['reason']}")
    return ExecutorResult(result=result, summary=f"Handed off to a human: {args['reason']}")


EXECUTORS: dict[str, Callable[[TurnContext, Tool, dict], ExecutorResult]] = {
    Tool.ToolType.KNOWLEDGE_SEARCH: search_knowledge,
    Tool.ToolType.HANDOFF: request_human_agent,
    Tool.ToolType.STRUCTURED_SEARCH: structured_search,
}
