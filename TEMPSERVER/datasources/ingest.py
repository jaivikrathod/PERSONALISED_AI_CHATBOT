"""CSV / JSON ingestion into `data_records` (TASKS.md Phase 2.2).

Upserts on `(data_source, external_id)` and records every run in
`data_source_syncs`. Runs synchronously inside the request for now; moving it
to a background job is the same work as Phase 2b's ingestion job.
"""

from __future__ import annotations

import csv
import io
import json
import logging

from django.db import connection, transaction
from django.db.models.fields.json import KeyTextTransform
from django.utils import timezone

from . import types
from .models import DataRecord, DataSource, DataSourceField, DataSourceSync

logger = logging.getLogger(__name__)

MAX_UPLOAD_BYTES = 20 * 1024 * 1024
INFERENCE_SAMPLE = 1000
MAX_STORED_ERRORS = 50
BATCH = 1000
ID_CANDIDATES = ("external_id", "id", "ref", "reference", "sku", "code")


class UploadError(Exception):
    pass


# --- Reading ---------------------------------------------------------------------
def read_upload(filename: str, content: bytes) -> list:
    if len(content) > MAX_UPLOAD_BYTES:
        raise UploadError(f"File is larger than {MAX_UPLOAD_BYTES // (1024 * 1024)} MB.")
    try:
        text = content.decode("utf-8-sig")
    except UnicodeDecodeError:
        raise UploadError("File must be UTF-8 encoded.") from None

    if filename.lower().endswith(".json") or text.lstrip()[:1] in ("[", "{"):
        try:
            data = json.loads(text)
        except json.JSONDecodeError as exc:
            raise UploadError(f"Invalid JSON: {exc}") from None
        if isinstance(data, dict):
            data = data.get("records", data.get("data"))
        if not isinstance(data, list):
            raise UploadError('JSON must be a list of objects, or {"records": [...]}.')
        return data

    reader = csv.DictReader(io.StringIO(text))
    if not reader.fieldnames:
        raise UploadError("CSV has no header row.")
    return list(reader)


def normalise_rows(rows: list) -> tuple[dict[str, str], list[dict | None]]:
    """Normalise headers to identifiers. Returns ({original: name}, rows)."""
    header_map: dict[str, str] = {}
    taken: set[str] = set()
    for row in rows:
        if isinstance(row, dict):
            for key in row:
                if key is not None and key not in header_map:
                    header_map[key] = types.normalise_header(key, taken)

    normalised: list[dict | None] = []
    for row in rows:
        if not isinstance(row, dict):
            normalised.append(None)
            continue
        normalised.append(
            {
                header_map[k]: (None if types.is_blank(v) else v)
                for k, v in row.items()
                if k is not None
            }
        )
    return header_map, normalised


# --- Import ----------------------------------------------------------------------
def import_records(source: DataSource, filename: str, content: bytes, mode: str = "upsert") -> DataSourceSync:
    sync = DataSourceSync.objects.create(data_source=source, mode=mode, filename=filename[:255])
    try:
        raw_rows = read_upload(filename, content)
    except UploadError as exc:
        sync.errors = [str(exc)]
        sync.finished_at = timezone.now()
        sync.save()
        source.sync_status = DataSource.SyncStatus.FAILED
        source.save(update_fields=["sync_status", "updated_at"])
        return sync

    header_map, rows = normalise_rows(raw_rows)
    config = dict(source.config or {})
    id_field = config.get("id_field") or _pick_id_field(list(header_map.values()))
    config["id_field"] = id_field

    fields = {f.name: f for f in source.fields.all()}
    new_columns = [(orig, name) for orig, name in header_map.items() if name not in fields]
    if new_columns:
        fields.update(_create_inferred_fields(source, new_columns, rows, len(fields)))
        # New columns change the schema a human confirmed.
        source.schema_confirmed_at = None

    errors: list[str] = []
    rejected = 0
    prepared: dict[str, dict] = {}
    for number, row in enumerate(rows, start=1):
        if row is None:
            rejected += 1
            errors.append(f"Row {number}: not an object.")
            continue
        external_id = row.get(id_field)
        external_id = "" if external_id is None else str(external_id).strip()
        if not external_id:
            rejected += 1
            errors.append(f"Row {number}: missing {id_field}.")
            continue
        if external_id in prepared:
            rejected += 1
            errors.append(f"Row {number}: duplicate {id_field} {external_id!r}.")
            continue
        prepared[external_id] = _build_payload(row, fields, number, errors)

    now = timezone.now()
    with transaction.atomic():
        ids = list(prepared)
        for start in range(0, len(ids), BATCH):
            chunk = ids[start : start + BATCH]
            existing = dict(
                DataRecord.objects.filter(data_source=source, external_id__in=chunk).values_list(
                    "external_id", "id"
                )
            )
            DataRecord.objects.bulk_update(
                [
                    DataRecord(id=existing[ext], payload=prepared[ext], deleted_at=None, updated_at=now)
                    for ext in chunk
                    if ext in existing
                ],
                ["payload", "deleted_at", "updated_at"],
            )
            DataRecord.objects.bulk_create(
                [
                    DataRecord(data_source=source, external_id=ext, payload=prepared[ext])
                    for ext in chunk
                    if ext not in existing
                ]
            )
        if mode == DataSourceSync.Mode.REPLACE:
            DataRecord.objects.filter(data_source=source, deleted_at__isnull=True).exclude(
                external_id__in=ids
            ).update(deleted_at=now)

        source.config = config
        source.sync_status = DataSource.SyncStatus.READY
        source.last_synced_at = now
        source.save()
        refresh_statistics(source)

    from .warnings import analyze
    from .publishing import refresh_tool

    sync.rows_in = len(raw_rows)
    sync.rows_upserted = len(prepared)
    sync.rows_rejected = rejected
    sync.errors = errors[:MAX_STORED_ERRORS] + (
        [f"… and {len(errors) - MAX_STORED_ERRORS} more."] if len(errors) > MAX_STORED_ERRORS else []
    )
    sync.warnings = analyze(source)
    sync.finished_at = timezone.now()
    sync.save()

    refresh_tool(source)
    return sync


def _pick_id_field(names: list[str]) -> str:
    for candidate in ID_CANDIDATES:
        if candidate in names:
            return candidate
    return names[0] if names else "id"


def _build_payload(row: dict, fields: dict, number: int, errors: list[str]) -> dict:
    payload = {}
    for name, value in row.items():
        if value is None:
            continue
        try:
            coerced = types.coerce(value, fields[name].data_type)
        except types.CoercionError as exc:
            # Keep the row; drop the value. A key that is absent (not null)
            # is what keeps the adapter's casts safe.
            errors.append(f"Row {number}: {name}: {exc}.")
            continue
        if coerced is not None:
            payload[name] = coerced
    return payload


def _create_inferred_fields(source, columns, rows, order_start) -> dict[str, DataSourceField]:
    created = {}
    sample = [r for r in rows if r is not None][:INFERENCE_SAMPLE]
    for offset, (original, name) in enumerate(columns):
        values = [r.get(name) for r in sample if r.get(name) is not None]
        data_type = types.infer_type(values)
        sensitive = types.is_sensitive(name)
        long_text = data_type == types.STRING and values and (
            sum(len(str(v)) for v in values) / len(values) > 60
        )
        created[name] = DataSourceField.objects.create(
            data_source=source,
            name=name,
            label=str(original).strip() or name,
            path=str(original)[:255],
            data_type=data_type,
            is_exposed=not sensitive,
            is_returned=not sensitive,
            is_filterable=not long_text,
            is_sortable=data_type in types.ORDERED_TYPES,
            # Strings get theirs once cardinality is known (enum vs free text).
            allowed_operators=[] if data_type == types.STRING else types.default_operators(data_type),
            display_order=order_start + offset,
        )
    return created


# --- Statistics ------------------------------------------------------------------
def refresh_statistics(source: DataSource) -> None:
    """Row count, per-field cardinality and enum values (drives B3 enum vs text)."""
    active = DataRecord.objects.filter(data_source=source, deleted_at__isnull=True)
    source.row_count = active.count()
    source.save(update_fields=["row_count", "updated_at"])

    fields = list(source.fields.all())
    for field in fields:
        if field.data_type == types.STRING_ARRAY:
            cardinality, values = _array_distinct(source, field.name)
        else:
            distinct = (
                active.annotate(v=KeyTextTransform(field.name, "payload"))
                .filter(v__isnull=False)
                .order_by()
                .values_list("v", flat=True)
                .distinct()
            )
            cardinality = distinct.count()
            values = (
                sorted(distinct[: types.ENUM_MAX_CARDINALITY + 1])
                if cardinality <= types.ENUM_MAX_CARDINALITY
                else None
            )

        field.cardinality = cardinality
        is_text = field.data_type in (types.STRING, types.STRING_ARRAY)
        field.enum_values = values if is_text and values is not None else None
        if field.data_type == types.STRING and not field.allowed_operators:
            field.allowed_operators = types.default_operators(types.STRING, cardinality)
    DataSourceField.objects.bulk_update(fields, ["cardinality", "enum_values", "allowed_operators"])


def _array_distinct(source, name):
    elements = """
        SELECT DISTINCT elem FROM data_records,
        jsonb_array_elements_text(
            CASE WHEN jsonb_typeof(payload -> %s) = 'array' THEN payload -> %s ELSE '[]'::jsonb END
        ) AS elem
        WHERE data_source_id = %s AND deleted_at IS NULL
    """
    params = [name, name, source.id]
    with connection.cursor() as cursor:
        cursor.execute(f"SELECT count(*) FROM ({elements}) AS t", params)
        cardinality = cursor.fetchone()[0]
        values = None
        if cardinality <= types.ENUM_MAX_CARDINALITY:
            cursor.execute(elements, params)
            values = sorted(row[0] for row in cursor.fetchall())
    return cardinality, values


def recoerce_field(field: DataSourceField) -> int:
    """Re-cast one field's stored values after its type changed. Returns failures.

    Values that no longer cast are removed from the payload (still counted),
    so the adapter's casts stay safe.
    """
    failures = 0
    batch = []
    records = DataRecord.objects.filter(data_source=field.data_source).only("id", "payload")
    for record in records.iterator():
        if field.name not in record.payload:
            continue
        try:
            value = types.coerce(record.payload[field.name], field.data_type)
        except types.CoercionError:
            value = None
            failures += 1
        if value is None:
            record.payload.pop(field.name)
        else:
            record.payload[field.name] = value
        batch.append(record)
        if len(batch) >= BATCH:
            DataRecord.objects.bulk_update(batch, ["payload"])
            batch = []
    if batch:
        DataRecord.objects.bulk_update(batch, ["payload"])
    refresh_statistics(field.data_source)
    return failures
