"""Declaration generator: `data_source_fields` → flat JSON Schema (WORKFLOW.md B3).

`parameter_specs` is the single mapping between model-facing parameters and
(field, operator). The declaration is generated from it, and the compiler in
`search.py` reads it back — so a parameter cannot exist in one and not the other.

The output never contains a data source id, an operator, a field path or a
table name. The model sees a business capability.

Deviation from the B3 table, deliberate: an integer/number field whose
`allowed_operators` include `equals` also gets an exact parameter (`bedrooms`),
because the B0/E2 worked examples filter "2BHK" as `bedrooms = 2`.
"""

from __future__ import annotations

from dataclasses import dataclass

from . import types

RESERVED = {"sort_by", "limit"}
DEFAULT_LIMIT = 10

NARROWING_HINT = (
    " Results say how many matched in total. If they are truncated, ask the "
    "customer to narrow down rather than listing everything; if nothing matched, "
    "`relaxable_filters` names the filters that would find results if dropped."
)


class DeclarationError(Exception):
    pass


@dataclass(frozen=True)
class ParamSpec:
    param: str
    field: object  # DataSourceField
    operator: str
    schema: dict


def parameter_specs(source, fields) -> list[ParamSpec]:
    fixed = {f.get("field") for f in source.fixed_filters}
    specs: list[ParamSpec] = []
    for field in fields:
        # Fixed-filter fields are applied server-side, never offered (E4.2).
        if not (field.is_exposed and field.is_filterable) or field.name in fixed:
            continue
        ops = set(field.allowed_operators or [])
        about = _describe(field)
        kind = field.data_type

        if kind == types.STRING:
            enum = field.enum_values if (field.cardinality or 0) <= types.ENUM_MAX_CARDINALITY else None
            if types.EQUALS in ops and enum:
                specs.append(ParamSpec(field.name, field, types.EQUALS, {"type": "string", "enum": enum, "description": about}))
            elif types.ILIKE in ops:
                specs.append(ParamSpec(field.name, field, types.ILIKE, {"type": "string", "description": f"{about} Matches partial text."}))
            elif types.EQUALS in ops:
                specs.append(ParamSpec(field.name, field, types.EQUALS, {"type": "string", "description": about}))

        elif kind in types.NUMERIC_TYPES:
            json_type = "integer" if kind == types.INTEGER else "number"
            if types.EQUALS in ops:
                specs.append(ParamSpec(field.name, field, types.EQUALS, {"type": json_type, "description": about}))
            if types.GTE in ops:
                specs.append(ParamSpec(f"min_{field.name}", field, types.GTE, {"type": json_type, "description": f"Minimum {field.label}. {about}"}))
            if types.LTE in ops:
                specs.append(ParamSpec(f"max_{field.name}", field, types.LTE, {"type": json_type, "description": f"Maximum {field.label}. {about}"}))

        elif kind == types.BOOLEAN and types.EQUALS in ops:
            specs.append(ParamSpec(field.name, field, types.EQUALS, {"type": "boolean", "description": about}))

        elif kind in (types.DATE, types.DATETIME):
            fmt = "date" if kind == types.DATE else "date-time"
            if types.GTE in ops:
                specs.append(ParamSpec(f"{field.name}_after", field, types.GTE, {"type": "string", "format": fmt, "description": f"On or after this {fmt}. {about}"}))
            if types.LTE in ops:
                specs.append(ParamSpec(f"{field.name}_before", field, types.LTE, {"type": "string", "format": fmt, "description": f"On or before this {fmt}. {about}"}))

        elif kind == types.STRING_ARRAY and types.CONTAINS_ANY in ops:
            items = {"type": "string"}
            if field.enum_values and (field.cardinality or 0) <= types.ENUM_MAX_CARDINALITY:
                items["enum"] = field.enum_values
            specs.append(ParamSpec(field.name, field, types.CONTAINS_ANY, {"type": "array", "items": items, "description": f"{about} Matches items having any of these."}))
    return specs


def sort_options(fields) -> list[str]:
    return [
        f"{field.name}_{direction}"
        for field in fields
        if field.is_exposed and field.is_sortable
        for direction in ("asc", "desc")
    ]


def compile_input_schema(source, fields, *, max_rows: int) -> dict:
    fields = list(fields)
    specs = parameter_specs(source, fields)
    properties: dict[str, dict] = {}
    for spec in specs:
        if spec.param in properties or spec.param in RESERVED:
            raise DeclarationError(
                f"Parameter {spec.param!r} is generated twice. Rename the field "
                f"{spec.field.name!r} so its parameters do not collide."
            )
        properties[spec.param] = spec.schema

    sorts = sort_options(fields)
    if sorts:
        properties["sort_by"] = {"type": "string", "enum": sorts, "description": "How to order the results."}
    properties["limit"] = {
        "type": "integer",
        "minimum": 1,
        "maximum": max_rows,
        "default": min(DEFAULT_LIMIT, max_rows),
        "description": "How many results to return.",
    }
    return {"type": "object", "properties": properties}


def tool_description(source) -> str:
    base = source.description.strip() or f"Search {source.display_name}."
    return base + NARROWING_HINT


def _describe(field) -> str:
    text = field.description.strip() or field.label or field.name
    if field.unit:
        text = f"{text} Unit: {field.unit}."
    return text
