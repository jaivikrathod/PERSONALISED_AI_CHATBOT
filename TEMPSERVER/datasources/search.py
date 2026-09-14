"""Compiler, validator (G4/G5/G6/G7), `records` adapter and result shaping (B3).

    flat model arguments ──compile_ir──▶ IR ──validate_ir──▶ IR ──records──▶ rows

The model never emits IR (D3). The IR is logged on every call (G10
`tool_executions.compiled_query`) and is the seam a later `rest_api` or
per-tenant-table adapter plugs into without touching the compiler or validator.
"""

from __future__ import annotations

import logging

from django.db.models import BooleanField, F, FloatField, Q
from django.db.models.fields.json import KeyTextTransform, KeyTransform
from django.db.models.functions import Cast

from orchestration.results import ExecutorResult
from orchestration.validation import ValidationFailed

from . import types
from .declarations import DEFAULT_LIMIT, parameter_specs
from .models import DataRecord, DataSource

logger = logging.getLogger(__name__)

MAX_FILTERS = 20
MAX_OFFSET = 200
MAX_TEXT_CHARS = 300
# relaxable_filters re-runs the query once per filter; bound the cost.
MAX_RELAXATION_QUERIES = 6


# --- Compile -------------------------------------------------------------------------
def compile_ir(source, fields, args: dict, *, max_rows: int) -> tuple[dict, list[str]]:
    """Flat parameters → IR. Returns (ir, the parameter behind each filter)."""
    specs = {spec.param: spec for spec in parameter_specs(source, fields)}
    filters, params = [], []
    for param, value in args.items():
        spec = specs.get(param)
        if spec is None or types.is_blank(value):
            continue
        filters.append({"field": spec.field.name, "operator": spec.operator, "value": value})
        params.append(param)

    sort = []
    if args.get("sort_by"):
        name, _, direction = str(args["sort_by"]).rpartition("_")
        sort = [{"field": name, "direction": direction}]

    ir = {
        "data_source": source.name,
        "filters": filters,
        "sort": sort,
        "limit": args.get("limit") or min(DEFAULT_LIMIT, max_rows),
        "offset": 0,
    }
    return ir, params


# --- Validate ------------------------------------------------------------------------
def validate_ir(ir: dict, fields_by_name: dict, *, max_rows: int) -> dict:
    """Gates G4–G7 over an IR. Raises ValidationFailed naming field and allowed values."""
    errors = []
    # G7: caps clamp silently.
    filters = ir["filters"][:MAX_FILTERS]

    for f in filters:
        field = fields_by_name.get(f["field"])
        # G4. One message for "no such field" and "hidden field", so a probe
        # cannot tell a hidden column exists.
        if field is None or not field.is_exposed or not field.is_filterable:
            errors.append({"field": f["field"], "code": "unknown_field", "message": f"{f['field']!r} cannot be searched."})
            continue
        # G5.
        if f["operator"] not in (field.allowed_operators or []):
            errors.append({
                "field": field.name,
                "code": "operator_not_allowed",
                "allowed": list(field.allowed_operators or []),
                "message": f"{field.name!r} does not support {f['operator']!r}.",
            })
            continue
        # G6.
        try:
            f["value"] = cast_value(field, f["operator"], f["value"])
        except types.CoercionError as exc:
            errors.append({"field": field.name, "code": "wrong_type", "expected": field.data_type, "message": f"{field.name!r}: {exc}."})
            continue
        enum = field.enum_values if field.data_type in (types.STRING, types.STRING_ARRAY) else None
        if enum and f["operator"] in (types.EQUALS, types.CONTAINS_ANY):
            wanted = f["value"] if isinstance(f["value"], list) else [f["value"]]
            bad = [v for v in wanted if v not in enum]
            if bad:
                errors.append({
                    "field": field.name,
                    "code": "not_allowed",
                    "allowed": enum,
                    "message": f"{field.name!r} must be one of the allowed values; got {bad}.",
                })

    for s in ir["sort"]:
        field = fields_by_name.get(s["field"])
        if field is None or not (field.is_exposed and field.is_sortable) or s["direction"] not in ("asc", "desc"):
            errors.append({"field": "sort_by", "code": "not_allowed", "message": "Unsupported sort order."})

    if errors:
        raise ValidationFailed(errors)

    return {
        **ir,
        "filters": filters,
        "limit": max(1, min(int(ir["limit"]), max_rows)),
        "offset": max(0, min(int(ir.get("offset") or 0), MAX_OFFSET)),
    }


def cast_value(field, operator: str, value):
    if operator == types.CONTAINS_ANY:
        items = value if isinstance(value, list) else [value]
        cast = [types.coerce(item, types.STRING) for item in items]
        cast = [c for c in cast if c is not None]
        if not cast:
            raise types.CoercionError("expected at least one value")
        return cast
    if operator == types.ILIKE:
        cast = types.coerce(value, types.STRING)
    else:
        cast = types.coerce(value, field.data_type)
    if cast is None:
        raise types.CoercionError("a value is required")
    return cast


def fixed_filter_errors(source, fields_by_name) -> list[dict]:
    """Fixed filters may target hidden fields, but must be well-formed."""
    errors = []
    for index, f in enumerate(source.fixed_filters):
        if not isinstance(f, dict) or not {"field", "operator", "value"} <= set(f):
            errors.append({"field": f"fixed_filters[{index}]", "code": "malformed", "message": "Each fixed filter needs field, operator and value."})
            continue
        field = fields_by_name.get(f["field"])
        if field is None:
            errors.append({"field": f["field"], "code": "unknown_field", "message": f"Fixed filter on unknown field {f['field']!r}."})
            continue
        if f["operator"] not in types.OPERATORS_BY_TYPE[field.data_type]:
            errors.append({"field": field.name, "code": "operator_not_allowed", "allowed": types.OPERATORS_BY_TYPE[field.data_type], "message": f"{f['operator']!r} does not apply to {field.data_type} fields."})
            continue
        try:
            cast_value(field, f["operator"], f["value"])
        except types.CoercionError as exc:
            errors.append({"field": field.name, "code": "wrong_type", "message": f"Fixed filter on {field.name!r}: {exc}."})
    return errors


# --- The records adapter ------------------------------------------------------------
def _expression(field):
    """Typed expression over the payload. Numbers cast exactly as the publish
    index is built (`(payload ->> 'f')::double precision`); dates compare as
    ISO text, which orders correctly."""
    if field.data_type in types.NUMERIC_TYPES:
        return Cast(KeyTextTransform(field.name, "payload"), FloatField())
    if field.data_type == types.BOOLEAN:
        return Cast(KeyTextTransform(field.name, "payload"), BooleanField())
    if field.data_type == types.STRING_ARRAY:
        return KeyTransform(field.name, "payload")
    return KeyTextTransform(field.name, "payload")


def apply_filters(queryset, fields_by_name, filters, *, prefix="f"):
    for index, f in enumerate(filters):
        field = fields_by_name[f["field"]]
        alias = f"{prefix}{index}"
        queryset = queryset.alias(**{alias: _expression(field)})
        operator, value = f["operator"], f["value"]
        if operator == types.EQUALS:
            queryset = queryset.filter(**{alias: value})
        elif operator == types.ILIKE:
            queryset = queryset.filter(**{f"{alias}__icontains": value})
        elif operator == types.GTE:
            queryset = queryset.filter(**{f"{alias}__gte": value})
        elif operator == types.LTE:
            queryset = queryset.filter(**{f"{alias}__lte": value})
        elif operator == types.CONTAINS_ANY:
            match = Q()
            for item in value:
                match |= Q(**{f"{alias}__contains": [item]})
            queryset = queryset.filter(match)
    return queryset


def run_records(source, fields, ir: dict, params: list[str]) -> dict:
    fields_by_name = {f.name: f for f in fields}
    base = DataRecord.objects.filter(data_source=source, deleted_at__isnull=True)
    fixed = [
        {**f, "value": cast_value(fields_by_name[f["field"]], f["operator"], f["value"])}
        for f in source.fixed_filters
    ]
    base = apply_filters(base, fields_by_name, fixed, prefix="x")
    queryset = apply_filters(base, fields_by_name, ir["filters"])

    order = []
    for index, s in enumerate(ir["sort"]):
        alias = f"s{index}"
        queryset = queryset.alias(**{alias: _expression(fields_by_name[s["field"]])})
        column = F(alias)
        order.append(column.asc(nulls_last=True) if s["direction"] == "asc" else column.desc(nulls_last=True))
    queryset = queryset.order_by(*order, "id")

    matched = queryset.count()
    start = ir["offset"]
    page = queryset.values_list("external_id", "payload")[start : start + ir["limit"]]
    rows = [_shape(external_id, payload, fields) for external_id, payload in page]

    result = {
        "matched": matched,
        "returned": len(rows),
        "truncated": matched > start + len(rows),
        "rows": rows,
    }
    if matched == 0 and 0 < len(ir["filters"]) <= MAX_RELAXATION_QUERIES:
        result["relaxable_filters"] = [
            params[index]
            for index in range(len(ir["filters"]))
            if apply_filters(
                base, fields_by_name, ir["filters"][:index] + ir["filters"][index + 1 :]
            ).exists()
        ]
    return result


def _shape(external_id, payload, fields) -> dict:
    """Only exposed, returned fields leave the database (G4 outbound, G7 token cap)."""
    row = {"ref": external_id}
    for field in fields:
        if field.is_exposed and field.is_returned and field.name in payload:
            value = payload[field.name]
            if isinstance(value, str) and len(value) > MAX_TEXT_CHARS:
                value = value[:MAX_TEXT_CHARS].rstrip() + "…"
            row[field.name] = value
    return row


# --- The executor ---------------------------------------------------------------------
def structured_search(ctx, tool, args: dict) -> ExecutorResult:
    """STRUCTURED_SEARCH executor. The source is resolved through the turn's
    chatbot (G1) — a tool row pointing at another tenant's source finds nothing."""
    source_id = (tool.configuration or {}).get("data_source_id")
    source = DataSource.objects.filter(
        id=source_id, chatbot=ctx.chatbot, is_published=True
    ).first()
    if source is None:
        return ExecutorResult(
            result={"error": {"code": "tool_unavailable", "message": "This search is not available."}},
            summary="Unavailable: data source missing or unpublished.",
            rows_returned=0,
        )

    fields = list(source.fields.all())
    max_rows = ctx.chatbot.get_policy("max_rows_returned")
    ir, params = compile_ir(source, fields, args, max_rows=max_rows)
    ir = validate_ir(ir, {f.name: f for f in fields}, max_rows=max_rows)
    params = params[: len(ir["filters"])]

    result = run_records(source, fields, ir, params)
    logger.info("IR %s → matched=%s returned=%s", ir, result["matched"], result["returned"])

    described = ", ".join(f"{p}={args[p]!r}" for p in params) or "no filters"
    return ExecutorResult(
        result=result,
        summary=(
            f"Matched {result['matched']}, returned {result['returned']} "
            f"{source.display_name} ({described})."
        ),
        rows_returned=result["returned"],
        audit={"ir": ir, "fixed_filters": source.fixed_filters},
    )
