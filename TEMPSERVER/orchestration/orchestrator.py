"""The turn loop (WORKFLOW.md B5).

`run_turn` is the only entry point the chat transport calls:

    resolve → live-agent check (first, always) → safety net → context →
    model → tool calls → gates G1/G2/G3/G7/G9 → execute → audit G10 → loop

Budgets come from `chatbot.get_policy()`. Nothing here branches on a preset or
an industry; tools are registry rows and executors are looked up by type.
"""

from __future__ import annotations

import json
import logging
import re
import time
from concurrent.futures import ThreadPoolExecutor
from concurrent.futures import TimeoutError as FutureTimeout
from dataclasses import dataclass, field

from django.conf import settings
from django.db import connection
from django.utils import timezone

from chat.models import ChatMessage, ChatSession, ToolExecution
from chat.services import ACTIVE_SESSION_STATUSES, agent_group, message_event, send_to_group_sync
from registry.models import Chatbot

from . import executors as executor_registry
from .context import build_history, build_system_prompt
from .executors import ExecutorResult, TurnContext, hand_off
from .providers import ProviderError, get_provider
from .validation import ValidationFailed, strip_tenant_keys, validate_arguments

logger = logging.getLogger(__name__)

AGENT_HANDOFF_MESSAGE = (
    "I'm not able to answer that from our FAQ right now. "
    "Let me connect you with one of our support agents who'll help you shortly."
)
SLOW_TURN_MESSAGE = (
    "Sorry, this is taking longer than it should. "
    "Let me connect you with one of our support agents who'll help you shortly."
)

# Safety net: an explicit request for a person never depends on the model.
HUMAN_REQUEST = re.compile(
    r"\b(talk|speak|chat|connect)\b.{0,25}\b(human|person|agent|representative|someone)\b"
    r"|\b(real|live|actual)\s+(person|human|agent)\b"
    r"|\bhuman\s+agent\b",
    re.IGNORECASE,
)

COUNTED_STATUSES = (
    ToolExecution.Status.OK,
    ToolExecution.Status.ERROR,
    ToolExecution.Status.TIMEOUT,
)


@dataclass
class TurnResult:
    frames: list[dict] = field(default_factory=list)


# --- Resolution --------------------------------------------------------------
def resolve_chatbot(company_id) -> Chatbot | None:
    return (
        Chatbot.objects.select_related("company")
        .filter(company_id=company_id, is_active=True)
        .order_by("id")
        .first()
    )


def resolve_session(company_id, session_id=None, *, visitor_id="") -> ChatSession:
    """Reuse a session only inside this company; otherwise start one."""
    if session_id:
        session = ChatSession.objects.filter(id=session_id, company_id=company_id).first()
        if session:
            return session
    chatbot = resolve_chatbot(company_id)
    return ChatSession.objects.create(
        company_id=company_id, chatbot=chatbot, visitor_id=visitor_id or ""
    )


# --- The turn ----------------------------------------------------------------
def run_turn(session, message, *, customer=None, provider=None, emit=None, clock=time.monotonic):
    customer = customer or {}
    emit = emit or (lambda frame: None)
    started = clock()

    user_row = _store(session, customer, role=ChatMessage.Role.USER, message=message)

    # B5 step 2 / Part D rule 4: a human owns the chat, the model is skipped.
    live_agent_id = _live_agent_id(session)
    if live_agent_id:
        send_to_group_sync(
            agent_group(live_agent_id),
            {"type": "chat.message", "message": message_event(user_row)},
        )
        return TurnResult(
            frames=[{"type": "delivered", "agent_needed": True, "agent_handling": True}]
        )

    # B5 step 1: bind tenant and bot now. Nothing downstream reads them elsewhere.
    # Re-read every turn: a socket holds its session for the whole chat, and a
    # policy or tool edit must apply to the next message, not the next chat.
    chatbot = None
    if session.chatbot_id:
        chatbot = Chatbot.objects.select_related("company").filter(id=session.chatbot_id).first()
    chatbot = chatbot or resolve_chatbot(session.company_id)
    if chatbot is not None and session.chatbot_id != chatbot.id:
        session.chatbot = chatbot
        session.save(update_fields=["chatbot", "updated_at"])
    ctx = TurnContext(
        session=session,
        chatbot=chatbot,
        company_id=session.company_id,
        user_message=message,
    )

    if chatbot is None or not chatbot.is_active:
        hand_off(ctx, "no active chatbot for this company")
        return _finish(ctx, customer, AGENT_HANDOFF_MESSAGE)

    if HUMAN_REQUEST.search(message):
        hand_off(ctx, "customer asked for a human")
        return _finish(ctx, customer, AGENT_HANDOFF_MESSAGE)

    provider = provider or get_provider()
    tools = {t.name: t for t in chatbot.tools.filter(is_active=True)}
    declarations = [t.declaration() for t in tools.values()]
    policy = chatbot.get_policy
    model = chatbot.model or settings.GEMINI_MODEL

    calls_made = 0
    round_trips = 0
    call_cache: dict[str, ExecutorResult] = {}
    attempted = succeeded = False
    answer = None
    tokens = None
    out_of_time = False

    while answer is None:
        if _elapsed_ms(started, clock) > policy("wall_clock_ms"):
            out_of_time = True
            break
        if round_trips >= policy("model_round_trips") or calls_made >= policy("tool_calls_per_turn"):
            break

        try:
            response = provider.generate(
                system=build_system_prompt(chatbot, session),
                history=build_history(session),
                tools=declarations,
                model=model,
                temperature=chatbot.temperature,
            )
        except ProviderError as exc:
            return TurnResult(frames=[{"type": "error", "error": str(exc)}])
        round_trips += 1

        if not response.tool_calls:
            answer, tokens = response.text, response.tokens
            break

        for call in response.tool_calls:
            if calls_made >= policy("tool_calls_per_turn"):
                break
            calls_made += 1
            attempted = True
            outcome = _execute_call(ctx, tools, call, call_cache, customer, emit)
            succeeded = succeeded or outcome
            if ctx.handed_off:
                break
        if ctx.handed_off:
            break

    if out_of_time:
        if not ctx.handed_off:
            hand_off(ctx, "wall clock budget exhausted")
        return _finish(ctx, customer, SLOW_TURN_MESSAGE)

    if answer is None:
        # B5 step 7: degrade deliberately — one final call with tools withheld.
        try:
            response = provider.generate(
                system=build_system_prompt(chatbot, session, final=True),
                history=build_history(session),
                tools=[],
                model=model,
                temperature=chatbot.temperature,
            )
            answer, tokens = response.text, response.tokens
        except ProviderError:
            logger.exception("Final degraded call failed for session #%s", session.id)
            answer = ""

    if not answer and not ctx.handed_off:
        hand_off(ctx, "no answer produced within budget")

    if attempted and not succeeded and not ctx.handed_off:
        if _barren_turns(session) >= policy("handoff_after_barren_turns"):
            hand_off(ctx, "consecutive turns without a successful tool result")
            answer = AGENT_HANDOFF_MESSAGE

    return _finish(
        ctx,
        customer,
        answer or AGENT_HANDOFF_MESSAGE,
        tokens=tokens,
        latency_ms=_elapsed_ms(started, clock),
    )


# --- One tool call through the gates ------------------------------------------
def _execute_call(ctx, tools, call, call_cache, customer, emit) -> bool:
    """Run one model tool call through the gates. Returns True on success."""
    call_row = _store(
        ctx.session,
        customer,
        role=ChatMessage.Role.ASSISTANT,
        tool_name=call.name,
        tool_call_id=call.id,
        tool_args=call.args,
        attachments={"provider_meta": call.meta} if call.meta else None,
    )
    started = time.monotonic()
    tool = tools.get(call.name)
    validated = None

    if tool is None:
        # G2: the tool must exist, be active and belong to this chatbot.
        status, code = ToolExecution.Status.REJECTED, "unknown_tool"
        outcome = ExecutorResult(
            result={
                "error": {
                    "code": code,
                    "message": f"There is no tool named {call.name!r}.",
                    "available_tools": sorted(tools),
                }
            },
            summary=f"Rejected: unknown tool {call.name!r}.",
            rows_returned=0,
        )
    else:
        emit({"type": "tool_started", "tool": tool.name, "label": _progress_label(tool)})
        args, dropped = strip_tenant_keys(call.args)
        if dropped:
            # G1: ignored, not honoured. Logged loudly — this is either a
            # confused model or an injection attempt.
            logger.warning(
                "G1: dropped model-supplied tenant keys %s on %s (session #%s, company %s)",
                dropped, tool.name, ctx.session.id, ctx.company_id,
            )
        try:
            validated = validate_arguments(tool.input_schema, args)  # G3
        except ValidationFailed as exc:
            status, code = ToolExecution.Status.REJECTED, "invalid_arguments"
            outcome = ExecutorResult(
                result={"error": {"code": code, "errors": exc.errors}},
                summary=f"Rejected: {exc}",
                rows_returned=0,
            )
        else:
            status, code, outcome = _run_validated(ctx, tool, validated, call_cache)

    duration_ms = int((time.monotonic() - started) * 1000)
    ToolExecution.objects.create(  # G10
        company_id=ctx.company_id,
        conversation=ctx.session,
        message=call_row,
        tool=tool,
        tool_name=call.name,
        raw_arguments=call.args,
        validated_arguments=validated,
        status=status,
        error_code=code,
        rows_returned=outcome.rows_returned,
        compiled_query=outcome.audit,
        duration_ms=duration_ms,
    )
    _store(
        ctx.session,
        customer,
        role=ChatMessage.Role.TOOL,
        tool_name=call.name,
        tool_call_id=call.id,
        tool_result=outcome.result,
        tool_result_summary=outcome.summary,
        latency_ms=duration_ms,
    )
    return status in (ToolExecution.Status.OK, ToolExecution.Status.CACHED) and outcome.successful


def _run_validated(ctx, tool, validated, call_cache):
    policy = ctx.chatbot.get_policy
    key = f"{tool.name}:{json.dumps(validated, sort_keys=True, default=str)}"

    # B5 repeat_identical_call: serve the cached result, do not re-execute.
    if key in call_cache and policy("repeat_identical_call") <= 1:
        return ToolExecution.Status.CACHED, "", call_cache[key]

    limited = _rate_limited(ctx, tool)  # G9
    if limited:
        return (
            ToolExecution.Status.RATE_LIMITED,
            "rate_limited",
            ExecutorResult(
                result={"error": {"code": "rate_limited", "message": limited}},
                summary=f"Rate limited: {limited}",
                rows_returned=0,
            ),
        )

    executor = executor_registry.EXECUTORS.get(tool.tool_type)
    if executor is None:
        return (
            ToolExecution.Status.REJECTED,
            "tool_unavailable",
            ExecutorResult(
                result={"error": {"code": "tool_unavailable", "message": "This tool is not available yet."}},
                summary="Rejected: no executor for this tool type.",
                rows_returned=0,
            ),
        )

    timeout_s = policy("single_tool_timeout_ms") / 1000
    try:
        outcome = _call_with_timeout(executor, ctx, tool, validated, timeout_s)
    except ValidationFailed as exc:
        # G4/G5/G6 run inside executors that know their own fields. Same
        # informed-retry contract as G3.
        return (
            ToolExecution.Status.REJECTED,
            "invalid_arguments",
            ExecutorResult(
                result={"error": {"code": "invalid_arguments", "errors": exc.errors}},
                summary=f"Rejected: {exc}",
                rows_returned=0,
            ),
        )
    except FutureTimeout:
        # A timeout is a *result* the model can talk about, never an exception.
        return (
            ToolExecution.Status.TIMEOUT,
            "timeout",
            ExecutorResult(
                result={"error": {"code": "timeout", "message": "That lookup did not respond in time."}},
                summary="Timed out.",
                rows_returned=0,
            ),
        )
    except Exception:
        logger.exception("Executor %s failed (session #%s)", tool.name, ctx.session.id)
        return (
            ToolExecution.Status.ERROR,
            "executor_error",
            ExecutorResult(
                result={"error": {"code": "executor_error", "message": "That lookup failed."}},
                summary="Failed with an internal error.",
                rows_returned=0,
            ),
        )

    call_cache[key] = outcome
    return ToolExecution.Status.OK, "", outcome


def _call_with_timeout(executor, ctx, tool, args, timeout_s):
    if not getattr(settings, "ORCHESTRATION_TOOL_THREADS", True):
        return executor(ctx, tool, args)

    def target():
        try:
            return executor(ctx, tool, args)
        finally:
            connection.close()

    pool = ThreadPoolExecutor(max_workers=1)
    try:
        return pool.submit(target).result(timeout=timeout_s)
    finally:
        # Do not wait on a hung executor; its thread finishes on its own.
        pool.shutdown(wait=False)


def _rate_limited(ctx, tool) -> str | None:
    limits = tool.rate_limit or {}
    per_conversation = limits.get("per_conversation")
    if per_conversation is not None:
        used = ToolExecution.objects.filter(
            conversation=ctx.session, tool=tool, status__in=COUNTED_STATUSES
        ).count()
        if used >= per_conversation:
            return f"{tool.name} may be used {per_conversation} times per conversation."

    per_minute = limits.get("per_company_per_minute")
    if per_minute is not None:
        used = ToolExecution.objects.filter(
            company_id=ctx.company_id,
            tool_name=tool.name,
            status__in=COUNTED_STATUSES,
            created_at__gte=timezone.now() - timezone.timedelta(minutes=1),
        ).count()
        if used >= per_minute:
            return f"{tool.name} is busy right now. Try again shortly."
    return None


# --- Safety net ---------------------------------------------------------------
def _barren_turns(session) -> int:
    """Consecutive most-recent turns that tried tools and got nothing useful.

    Read from the log (G10 rows), not a counter, so it survives restarts and
    agrees with what the audit shows. Turns with no tool call — greetings — do
    not count, and neither break the streak.
    """
    user_ids = list(
        ChatMessage.objects.filter(session=session, role=ChatMessage.Role.USER)
        .order_by("-id")
        .values_list("id", flat=True)[:20]
    )
    executions = list(
        ToolExecution.objects.filter(conversation=session, message__isnull=False)
        .order_by("message_id")
        .values_list("message_id", "status", "rows_returned")
    )
    barren = 0
    upper = None
    for user_id in user_ids:
        in_turn = [
            (status, rows)
            for message_id, status, rows in executions
            if message_id > user_id and (upper is None or message_id < upper)
        ]
        upper = user_id
        if not in_turn:
            continue
        useful = any(
            status in (ToolExecution.Status.OK, ToolExecution.Status.CACHED)
            and (rows is None or rows > 0)
            for status, rows in in_turn
        )
        if useful:
            break
        barren += 1
    return barren


# --- Helpers --------------------------------------------------------------------
def _finish(ctx, customer, answer, *, tokens=None, latency_ms=None) -> TurnResult:
    _store(
        ctx.session,
        customer,
        role=ChatMessage.Role.ASSISTANT,
        message=answer,
        tokens=tokens,
        latency_ms=latency_ms,
    )
    frame = {
        "type": "answer",
        "answer": answer,
        "is_answer_found": not ctx.handed_off,
        "agent_needed": ctx.handed_off,
        "sources": ctx.sources,
    }
    if ctx.best_score is not None:
        frame["score"] = round(ctx.best_score, 4)
    return TurnResult(frames=[frame])


def _store(session, customer, *, role, message="", **fields) -> ChatMessage:
    from_us = role != ChatMessage.Role.USER
    return ChatMessage.objects.create(
        company_id=session.company_id,
        session=session,
        role=role,
        message=message,
        sent_by_us=from_us,
        is_ai=from_us,
        customer_user_id=customer.get("customer_user_id") or None,
        customer_user_name=customer.get("customer_user_name") or "",
        customer_user_email=customer.get("customer_user_email") or "",
        message_type=ChatMessage.MessageType.TEXT,
        **fields,
    )


def _live_agent_id(session):
    # Re-read: the agent may have been attached after this socket connected.
    row = ChatSession.objects.filter(id=session.id).values("agent_id", "status").first()
    if row and row["agent_id"] and row["status"] in ACTIVE_SESSION_STATUSES:
        return row["agent_id"]
    return None


def _progress_label(tool) -> str:
    return (tool.configuration or {}).get("progress_label") or "Checking…"


def _elapsed_ms(started, clock) -> int:
    return int((clock() - started) * 1000)
