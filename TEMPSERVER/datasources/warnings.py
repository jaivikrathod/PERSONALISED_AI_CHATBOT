"""Import-time warnings for the three modelling traps (WORKFLOW.md E2).

Warn, never block — the company decides. Every check is generic: it looks at
the shape of the data, never at what the columns are called in one industry.
"""

from __future__ import annotations

import re
from statistics import median

from . import types
from .models import DataRecord

SAMPLE = 2000
DEPENDENT_RATIO = 20
HIERARCHY_SHARE = 0.6
HIERARCHY_SPLIT = re.compile(r"\s*(?:>|/|\||,)\s*")


def analyze(source) -> list[dict]:
    fields = list(source.fields.all())
    payloads = list(
        DataRecord.objects.filter(data_source=source, deleted_at__isnull=True)
        .order_by("id")
        .values_list("payload", flat=True)[:SAMPLE]
    )
    return (
        _split_by_category(source, fields, payloads)
        + _dependent_columns(fields, payloads)
        + _collapsed_hierarchy(fields, payloads)
    )


def _split_by_category(source, fields, payloads) -> list[dict]:
    """Trap 1: one dataset per *kind of thing*, never per category."""
    warnings = []
    if len(payloads) >= 5:
        for field in fields:
            if field.data_type == types.STRING and field.cardinality == 1 and field.enum_values:
                warnings.append(
                    {
                        "code": "looks_split_by_category",
                        "fields": [field.name],
                        "message": (
                            f"Every row has {field.label} = {field.enum_values[0]!r}. If rows "
                            f"with other {field.label} values live in a separate upload, put "
                            "them in this data source instead of creating another one."
                        ),
                    }
                )

    names = {f.name for f in fields}
    siblings = source.chatbot.data_sources.exclude(id=source.id).prefetch_related("fields")
    for sibling in siblings:
        other = {f.name for f in sibling.fields.all()}
        if names and other and len(names & other) / len(names | other) >= 0.8:
            warnings.append(
                {
                    "code": "looks_split_by_category",
                    "fields": [],
                    "message": (
                        f"This data has almost the same columns as {sibling.display_name!r}. "
                        "If they are the same kind of thing, keep them in one data source "
                        "with a column that tells them apart."
                    ),
                }
            )
    return warnings


def _dependent_columns(fields, payloads) -> list[dict]:
    """Trap 2: a column whose meaning depends on another column."""
    warnings = []
    groupers = [
        f for f in fields
        if f.data_type == types.STRING and f.cardinality and 2 <= f.cardinality <= 10
    ]
    # Only columns a customer can filter on: the trap is a filter that means two
    # things. A hidden bookkeeping column (a margin that naturally differs
    # between sales and rentals) is not one.
    numbers = [
        f for f in fields
        if f.data_type in types.NUMERIC_TYPES and f.is_exposed and f.is_filterable
    ]
    for number in numbers:
        for grouper in groupers:
            groups: dict[str, list[float]] = {}
            for payload in payloads:
                value, key = payload.get(number.name), payload.get(grouper.name)
                if isinstance(value, (int, float)) and value > 0 and key is not None:
                    groups.setdefault(str(key), []).append(value)
            medians = {k: median(v) for k, v in groups.items() if len(v) >= 2}
            if len(medians) < 2:
                continue
            low, high = min(medians, key=medians.get), max(medians, key=medians.get)
            if medians[high] / medians[low] >= DEPENDENT_RATIO:
                warnings.append(
                    {
                        "code": "column_meaning_depends_on_another",
                        "fields": [number.name, grouper.name],
                        "message": (
                            f"{number.label} looks like it means different things depending on "
                            f"{grouper.label} (typically {medians[high]:g} for {high!r} but "
                            f"{medians[low]:g} for {low!r}). Split it into one column per "
                            "meaning and leave the irrelevant one blank."
                        ),
                    }
                )
                break
    return warnings


def _collapsed_hierarchy(fields, payloads) -> list[dict]:
    """Trap 3: several levels of a hierarchy joined into one column."""
    warnings = []
    for field in fields:
        if field.data_type != types.STRING or not field.is_filterable:
            continue
        distinct = {str(p[field.name]) for p in payloads if field.name in p}
        if len(distinct) < 3:
            continue
        joined = [v for v in distinct if len([p for p in HIERARCHY_SPLIT.split(v) if p]) >= 2]
        if len(joined) / len(distinct) >= HIERARCHY_SHARE:
            warnings.append(
                {
                    "code": "collapsed_hierarchy",
                    "fields": [field.name],
                    "message": (
                        f"{field.label} looks like several levels joined together "
                        f"(e.g. {sorted(joined)[0]!r}). Keep each level — city and "
                        "locality, category and sub-category — as its own column."
                    ),
                }
            )
    return warnings
