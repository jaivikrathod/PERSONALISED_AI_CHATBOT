"""Publishing a source: checks, indexes, and the generated `search_<name>` tool.

`Tool.input_schema` *is* the compiled-declaration cache (TASKS.md 2.3): it is
compiled here, stored once, and read by the orchestrator on every turn without
recompiling. `refresh_tool` is the invalidation — called on every write to a
source or its fields (see `signals.py`, plus explicit calls after bulk writes),
and it bumps `schema_version` only when the compiled output actually changed.
"""

from __future__ import annotations

import hashlib
import re

from django.db import connection, transaction

from registry.models import Tool

from . import types
from .declarations import DeclarationError, compile_input_schema, tool_description
from .models import DataSource
from .search import fixed_filter_errors

SAFE_NAME = re.compile(r"^[a-z][a-z0-9_]*$")


class PublishError(Exception):
    def __init__(self, errors: list[dict]):
        super().__init__("; ".join(e["message"] for e in errors))
        self.errors = errors


def publish_errors(source: DataSource) -> list[dict]:
    errors = []
    fields = list(source.fields.all())
    by_name = {f.name: f for f in fields}

    if source.adapter != DataSource.Adapter.RECORDS:
        errors.append({"field": "adapter", "code": "unsupported", "message": "Only uploaded records can be published yet."})
    if source.row_count == 0:
        errors.append({"field": None, "code": "no_records", "message": "Import data before publishing."})
    if source.schema_confirmed_at is None:
        errors.append({"field": None, "code": "schema_not_confirmed", "message": "Review and confirm the detected column types first."})
    if not source.description.strip():
        errors.append({"field": "description", "code": "description_required", "message": "Describe what this data is and when the assistant should search it."})

    exposed = [f for f in fields if f.is_exposed]
    if not exposed:
        errors.append({"field": None, "code": "no_exposed_fields", "message": "Expose at least one field."})
    for field in exposed:
        if not field.description.strip():
            errors.append({
                "field": field.name,
                "code": "description_required",
                "message": f"Describe {field.label!r} the way customers talk about it.",
            })

    errors.extend(fixed_filter_errors(source, by_name))

    clash = Tool.objects.filter(chatbot=source.chatbot, name=source.tool_name).exclude(
        tool_type=Tool.ToolType.STRUCTURED_SEARCH, configuration__data_source_id=source.id
    )
    if clash.exists():
        errors.append({"field": "name", "code": "tool_name_taken", "message": f"The assistant already has a tool named {source.tool_name!r}."})

    try:
        compile_input_schema(source, fields, max_rows=source.chatbot.get_policy("max_rows_returned"))
    except DeclarationError as exc:
        errors.append({"field": None, "code": "declaration_error", "message": str(exc)})
    return errors


@transaction.atomic
def publish(source: DataSource) -> Tool:
    errors = publish_errors(source)
    if errors:
        raise PublishError(errors)
    ensure_indexes(source)
    source.is_published = True
    source.save(update_fields=["is_published", "updated_at"])
    return refresh_tool(source)


@transaction.atomic
def unpublish(source: DataSource) -> None:
    source.is_published = False
    source.save(update_fields=["is_published", "updated_at"])
    _tool_for(source).update(is_active=False)


def refresh_tool(source: DataSource) -> Tool | None:
    if not source.is_published:
        return None
    fields = list(source.fields.all())
    schema = compile_input_schema(source, fields, max_rows=source.chatbot.get_policy("max_rows_returned"))
    description = tool_description(source)

    tool = _tool_for(source).first()
    if tool is None:
        return Tool.objects.create(
            chatbot=source.chatbot,
            name=source.tool_name,
            tool_type=Tool.ToolType.STRUCTURED_SEARCH,
            description=description,
            configuration={"data_source_id": source.id},
            input_schema=schema,
        )

    changed = (tool.input_schema, tool.description, tool.name) != (schema, description, source.tool_name)
    if changed or not tool.is_active:
        if changed:
            tool.schema_version += 1
        tool.input_schema = schema
        tool.description = description
        tool.name = source.tool_name
        tool.is_active = True
        tool.save()
    return tool


def _tool_for(source):
    return Tool.objects.filter(
        chatbot=source.chatbot,
        tool_type=Tool.ToolType.STRUCTURED_SEARCH,
        configuration__data_source_id=source.id,
    )


def ensure_indexes(source: DataSource) -> list[str]:
    """B-tree expression indexes on numeric/date fields, created once at publish.

    Partial on `data_source_id`, so one tenant's indexes never cover another's
    rows. Field names are validated identifiers, so inlining them is safe.
    """
    created = []
    with connection.cursor() as cursor:
        # Postgres refuses CREATE INDEX on a table with deferred FK checks still
        # pending in this transaction (rows written earlier in it). Run them now.
        cursor.execute("SET CONSTRAINTS ALL IMMEDIATE")
        for field in source.fields.all():
            if not (field.is_exposed and (field.is_filterable or field.is_sortable)):
                continue
            if field.data_type not in types.ORDERED_TYPES or not SAFE_NAME.match(field.name):
                continue
            digest = hashlib.md5(field.name.encode()).hexdigest()[:12]
            name = f"dr_s{int(source.id)}_{digest}"
            key = f"(payload ->> '{field.name}')"
            expression = f"({key}::double precision)" if field.data_type in types.NUMERIC_TYPES else f"({key})"
            cursor.execute(
                f"CREATE INDEX IF NOT EXISTS {name} ON data_records ({expression}) "
                f"WHERE data_source_id = {int(source.id)}"
            )
            created.append(name)
    return created
