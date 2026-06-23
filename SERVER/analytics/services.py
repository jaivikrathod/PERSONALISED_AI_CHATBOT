"""Analytics service layer: metric aggregation + unanswered-question curation."""

from __future__ import annotations

import re
from datetime import date, timedelta

from django.db import transaction
from django.db.models import Count, F, Q
from django.db.models.functions import TruncDate
from django.utils import timezone

from core.enums import ConversationStatus, SenderType

from .models import ConversationMetrics, UnansweredQuestion

_WS = re.compile(r"\s+")


def _normalize(question: str) -> str:
    return _WS.sub(" ", question.strip().lower())[:512]


@transaction.atomic
def record_unanswered_question(company_id: int, question: str) -> UnansweredQuestion:
    """Upsert an unanswered question, incrementing its occurrence count."""
    normalized = _normalize(question)
    obj, created = UnansweredQuestion.objects.get_or_create(
        company_id=company_id,
        normalized=normalized,
        defaults={"question": question.strip()},
    )
    if not created:
        UnansweredQuestion.objects.filter(pk=obj.pk).update(
            occurrence_count=F("occurrence_count") + 1, updated_at=timezone.now()
        )
        obj.refresh_from_db()
    return obj


@transaction.atomic
def convert_unanswered_to_faq(unanswered: UnansweredQuestion, knowledge_base, answer: str):
    """Turn an unanswered question into a knowledge-base FAQ entry.

    Creating the QA triggers async embedding generation via the KB signals.
    """
    from knowledge_base.models import QuestionAnswer

    if knowledge_base.company_id != unanswered.company_id:
        from core.exceptions import TenantIsolationError

        raise TenantIsolationError("Knowledge base belongs to another company.")

    qa = QuestionAnswer.objects.create(
        knowledge_base=knowledge_base,
        question=unanswered.question,
        answer=answer,
    )
    unanswered.is_resolved = True
    unanswered.converted_qa = qa
    unanswered.save(update_fields=["is_resolved", "converted_qa", "updated_at"])
    return qa


def compute_daily_metrics(company_id: int, date=None) -> ConversationMetrics:
    """Aggregate a company's conversation KPIs for a given day (default: today)."""
    from conversations.models import Conversation, Message

    date = date or timezone.now().date()
    convos = Conversation.objects.filter(company_id=company_id, created_at__date=date)

    total = convos.count()
    resolved_by_ai = convos.filter(
        status=ConversationStatus.RESOLVED, assignments__isnull=True
    ).distinct().count()
    resolved_by_agent = convos.filter(
        status=ConversationStatus.RESOLVED, assignments__isnull=False
    ).distinct().count()
    escalated = convos.filter(
        status__in=[ConversationStatus.WAITING_AGENT, ConversationStatus.ACTIVE_AGENT]
    ).count()

    top_questions = list(
        Message.objects.filter(
            conversation__company_id=company_id,
            conversation__created_at__date=date,
            sender_type=SenderType.VISITOR,
        )
        .values("message")
        .annotate(count=Count("id"))
        .order_by("-count")[:10]
    )

    unanswered_count = UnansweredQuestion.objects.filter(
        company_id=company_id, is_resolved=False
    ).count()

    metrics, _ = ConversationMetrics.objects.update_or_create(
        company_id=company_id,
        date=date,
        defaults={
            "total_conversations": total,
            "resolved_by_ai": resolved_by_ai,
            "resolved_by_agent": resolved_by_agent,
            "escalated_chats": escalated,
            "top_questions": [
                {"question": q["message"], "count": q["count"]} for q in top_questions
            ],
            "unanswered_questions": unanswered_count,
        },
    )
    return metrics


# ---------------------------------------------------------------------------
# Dashboard / analytics-page aggregations (range based)
#
# These power the frontend dashboard which expects, respectively:
#   overview            -> { total_conversations, resolved_by_ai, resolved_by_agent,
#                            escalated, active_agents, unanswered, *_delta }
#   conversations_series-> [ { label, conversations, resolved }, ... ]
#   top_faqs            -> [ { question, count }, ... ]
# ---------------------------------------------------------------------------


def _range(date_from, date_to, default_days):
    """Resolve a (from, to) date window, defaulting to the last N days."""
    today = timezone.now().date()
    to = date_to or today
    frm = date_from or (to - timedelta(days=default_days - 1))
    return frm, to


def _pct_delta(cur: int, prev: int) -> int:
    """Integer percentage change of cur vs prev (frontend renders `<n>%`)."""
    if prev:
        return round((cur - prev) / prev * 100)
    return 100 if cur else 0


def _conversation_counts(company_id, frm, to) -> dict:
    from conversations.models import Conversation

    convos = Conversation.objects.filter(
        company_id=company_id, created_at__date__gte=frm, created_at__date__lte=to
    )
    return {
        "total_conversations": convos.count(),
        "resolved_by_ai": convos.filter(
            status=ConversationStatus.RESOLVED, assignments__isnull=True
        ).distinct().count(),
        "resolved_by_agent": convos.filter(
            status=ConversationStatus.RESOLVED, assignments__isnull=False
        ).distinct().count(),
        "escalated": convos.filter(
            status__in=[ConversationStatus.WAITING_AGENT, ConversationStatus.ACTIVE_AGENT]
        ).count(),
    }


def overview_metrics(company_id, date_from=None, date_to=None) -> dict:
    """KPI cards for the dashboard, with deltas vs the preceding equal window."""
    from agents.models import AgentAvailability

    frm, to = _range(date_from, date_to, 30)
    span = (to - frm).days + 1
    prev_to = frm - timedelta(days=1)
    prev_frm = prev_to - timedelta(days=span - 1)

    cur = _conversation_counts(company_id, frm, to)
    prev = _conversation_counts(company_id, prev_frm, prev_to)

    return {
        **cur,
        "total_conversations_delta": _pct_delta(
            cur["total_conversations"], prev["total_conversations"]
        ),
        "resolved_by_ai_delta": _pct_delta(cur["resolved_by_ai"], prev["resolved_by_ai"]),
        "resolved_by_agent_delta": _pct_delta(
            cur["resolved_by_agent"], prev["resolved_by_agent"]
        ),
        "escalated_delta": _pct_delta(cur["escalated"], prev["escalated"]),
        "active_agents": AgentAvailability.objects.filter(
            user__company_id=company_id, online=True
        ).count(),
        "unanswered": UnansweredQuestion.objects.filter(
            company_id=company_id, is_resolved=False
        ).count(),
    }


def _daily_counts(company_id, frm, to) -> dict:
    from conversations.models import Conversation

    rows = (
        Conversation.objects.filter(
            company_id=company_id, created_at__date__gte=frm, created_at__date__lte=to
        )
        .annotate(bucket=TruncDate("created_at"))
        .values("bucket")
        .annotate(
            conversations=Count("id"),
            resolved=Count("id", filter=Q(status=ConversationStatus.RESOLVED)),
        )
    )
    return {r["bucket"]: (r["conversations"], r["resolved"]) for r in rows}


def conversations_series(company_id, granularity="day", date_from=None, date_to=None) -> list:
    """Time series of conversations vs resolutions, bucketed by day or week.

    Zero-filled so the chart has a continuous x-axis even on sparse data.
    """
    default_days = 28 if granularity == "week" else 7
    frm, to = _range(date_from, date_to, default_days)
    daily = _daily_counts(company_id, frm, to)

    days = []
    cursor = frm
    while cursor <= to:
        conv, res = daily.get(cursor, (0, 0))
        days.append((cursor, conv, res))
        cursor += timedelta(days=1)

    if granularity == "week":
        weeks: dict[date, list[int]] = {}
        order: list[date] = []
        for d, conv, res in days:
            wk = d - timedelta(days=d.weekday())  # Monday of that week
            if wk not in weeks:
                weeks[wk] = [0, 0]
                order.append(wk)
            weeks[wk][0] += conv
            weeks[wk][1] += res
        return [
            {"label": wk.strftime("%b %d"), "conversations": weeks[wk][0], "resolved": weeks[wk][1]}
            for wk in order
        ]

    short = (to - frm).days <= 7
    return [
        {
            "label": d.strftime("%a") if short else d.strftime("%m/%d"),
            "conversations": conv,
            "resolved": res,
        }
        for d, conv, res in days
    ]


def top_faqs(company_id, date_from=None, date_to=None, limit=5) -> list:
    """Most frequently asked visitor questions in the window."""
    from conversations.models import Message

    frm, to = _range(date_from, date_to, 30)
    rows = (
        Message.objects.filter(
            conversation__company_id=company_id,
            sender_type=SenderType.VISITOR,
            created_at__date__gte=frm,
            created_at__date__lte=to,
        )
        .values("message")
        .annotate(count=Count("id"))
        .order_by("-count")[:limit]
    )
    return [{"question": r["message"], "count": r["count"]} for r in rows]
