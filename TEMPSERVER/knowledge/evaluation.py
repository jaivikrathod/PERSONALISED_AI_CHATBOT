"""The B4 measurement harness: labelled questions in, gate settings out.

An unmeasured threshold is a guess — that is how 0.90 got there. Each pilot
tenant supplies ~50 questions tagged answerable or not:

    {"cases": [
        {"question": "can I get my money back", "answerable": true, "expect": "refund"},
        {"question": "who won the 1998 world cup", "answerable": false}
    ]}

`expect` (optional) is a substring that must appear in a returned passage's
title or content. Tuning optimises for **precision on the `not` set** first —
a bot that answers what it does not know is the failure that matters — then
recall on the answerable set.
"""

from __future__ import annotations

from dataclasses import dataclass

from .retrieval import search

THRESHOLDS = [round(0.30 + 0.025 * i, 3) for i in range(13)]  # 0.30 … 0.60
MARGINS = [0.0, 0.05, 0.10, 0.15, 0.20]


@dataclass
class Report:
    answerable_total: int
    answerable_found: int
    not_total: int
    not_rejected: int
    failures: list[dict]
    settings: dict

    @property
    def not_set_precision(self) -> float:
        return self.not_rejected / self.not_total if self.not_total else 1.0

    @property
    def recall(self) -> float:
        return self.answerable_found / self.answerable_total if self.answerable_total else 1.0

    def as_dict(self) -> dict:
        return {
            "settings": self.settings,
            "not_set_precision": round(self.not_set_precision, 4),
            "recall": round(self.recall, 4),
            "answerable": f"{self.answerable_found}/{self.answerable_total}",
            "not_answerable_rejected": f"{self.not_rejected}/{self.not_total}",
            "failures": self.failures,
        }


def evaluate(chatbot, cases: list[dict], overrides: dict | None = None) -> Report:
    found = rejected = answerable_total = not_total = 0
    failures = []
    for case in cases:
        retrieval = search(chatbot, case["question"], overrides=overrides)
        returned = bool(retrieval.chunks)
        if case["answerable"]:
            answerable_total += 1
            expect = (case.get("expect") or "").lower()
            hit = returned and (
                not expect
                or any(expect in f"{c['title']} {c['content']}".lower() for c in retrieval.chunks)
            )
            found += hit
            if not hit:
                failures.append({"question": case["question"], "expected": "an answer", "best_score": retrieval.best_score, "rejected_by": retrieval.rejected_by})
        else:
            not_total += 1
            rejected += not returned
            if returned:
                failures.append({"question": case["question"], "expected": "nothing", "best_score": retrieval.best_score, "accepted_by": retrieval.accepted_by})
    settings = {k: (overrides or {}).get(k, chatbot.get_policy(k)) for k in ("accept_threshold", "margin_rule", "retrieval_floor")}
    return Report(answerable_total, found, not_total, rejected, failures, settings)


def tune(chatbot, cases: list[dict], *, target_precision: float = 0.95) -> Report | None:
    """Best (accept_threshold, margin_rule) meeting the `not`-set target.

    Maximises recall; ties go to the stricter threshold. None if no setting
    reaches the target — the fixture or the content needs work, not the knob.
    """
    best = None
    for threshold in THRESHOLDS:
        for margin in MARGINS:
            report = evaluate(chatbot, cases, {"accept_threshold": threshold, "margin_rule": margin})
            if report.not_set_precision < target_precision:
                continue
            if best is None or report.recall > best.recall:
                best = report
    return best
