"""Structured data — the universality layer (WORKFLOW.md B2.3).

Structure is rows, data is JSON:

- `DataSourceField` is the header row, and **the security boundary**. It is the
  only list of names the validator accepts; `is_exposed = False` makes a field
  invisible in both directions (cannot be filtered on, never returned).
- `DataRecord.payload` is the data. It stores *every* column, hidden ones
  included, so a company can expose a field later without re-uploading.

Nothing here knows what a "property" or a "product" is (Part D rule 3).
"""

from django.contrib.postgres.fields import ArrayField
from django.contrib.postgres.indexes import GinIndex
from django.contrib.postgres.search import SearchVectorField
from django.core.validators import RegexValidator
from django.db import models

from company.models import Company

from . import types

IDENTIFIER = RegexValidator(
    r"^[a-z][a-z0-9_]*$",
    "Use lowercase letters, digits and underscores, starting with a letter.",
)


class DataSource(models.Model):
    class Adapter(models.TextChoices):
        RECORDS = "records", "Records (uploaded rows)"
        REST_API = "rest_api", "REST API"
        SQL_READONLY = "sql_readonly", "Read-only SQL"

    class SyncStatus(models.TextChoices):
        EMPTY = "empty", "No data yet"
        READY = "ready", "Ready"
        FAILED = "failed", "Last import failed"

    # Denormalised from `chatbot.company` so tenancy scoping is one lookup,
    # the same shape as every other tenant table (A3).
    company = models.ForeignKey(Company, on_delete=models.CASCADE, related_name="data_sources")
    chatbot = models.ForeignKey(
        "registry.Chatbot", on_delete=models.CASCADE, related_name="data_sources"
    )

    # Becomes the tool name `search_<name>`, so it must be a valid identifier.
    name = models.CharField(max_length=48, validators=[IDENTIFIER])
    display_name = models.CharField(max_length=255)

    # Becomes the tool description the model reads to choose between tools.
    description = models.TextField(blank=True)

    adapter = models.CharField(max_length=16, choices=Adapter.choices, default=Adapter.RECORDS)

    # {"fixed_filters": [{"field", "operator", "value"}], "id_field": "ref"}
    # Fixed filters are applied server-side on every query and never offered to
    # the model (E4.2): `status = available`, `in_stock = true`.
    config = models.JSONField(default=dict, blank=True)

    row_count = models.PositiveIntegerField(default=0)
    sync_status = models.CharField(
        max_length=16, choices=SyncStatus.choices, default=SyncStatus.EMPTY
    )
    last_synced_at = models.DateTimeField(null=True, blank=True)

    # Inferred types are a suggestion (Phase 2.2). A human confirms them before
    # the source can be published; importing new columns clears this.
    schema_confirmed_at = models.DateTimeField(null=True, blank=True)
    is_published = models.BooleanField(default=False)

    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        db_table = "data_sources"
        ordering = ("id",)
        constraints = [
            models.UniqueConstraint(
                fields=["chatbot", "name"], name="data_sources_unique_name_per_chatbot"
            ),
        ]

    def __str__(self):
        return f"{self.display_name} ({self.name})"

    @property
    def tool_name(self) -> str:
        return f"search_{self.name}"

    @property
    def fixed_filters(self) -> list[dict]:
        return list((self.config or {}).get("fixed_filters") or [])


class DataSourceField(models.Model):
    data_source = models.ForeignKey(DataSource, on_delete=models.CASCADE, related_name="fields")

    # The payload key and the stem of the generated parameter names.
    name = models.CharField(max_length=64, validators=[IDENTIFIER])
    label = models.CharField(max_length=255, blank=True)
    data_type = models.CharField(max_length=16, choices=types.DATA_TYPE_CHOICES)

    # The column header as uploaded, before normalisation to `name`.
    path = models.CharField(max_length=255, blank=True)

    # Required on every exposed field before publishing (E4.3). This is what
    # maps "flat" → apartment and "2bhk" → bedrooms = 2.
    description = models.TextField(blank=True)
    unit = models.CharField(max_length=32, blank=True)

    is_exposed = models.BooleanField(default=True)
    is_filterable = models.BooleanField(default=True)
    is_sortable = models.BooleanField(default=False)
    # Reserved for full-text search over records; not compiled in Phase 2.
    is_searchable = models.BooleanField(default=False)
    is_returned = models.BooleanField(default=True)

    allowed_operators = ArrayField(models.CharField(max_length=16), default=list, blank=True)

    # Distinct values, kept only while cardinality <= ENUM_MAX_CARDINALITY.
    enum_values = models.JSONField(null=True, blank=True)
    cardinality = models.PositiveIntegerField(null=True, blank=True)
    display_order = models.PositiveIntegerField(default=0)

    class Meta:
        db_table = "data_source_fields"
        ordering = ("display_order", "id")
        constraints = [
            models.UniqueConstraint(
                fields=["data_source", "name"], name="data_source_fields_unique_name"
            ),
        ]

    def __str__(self):
        return f"{self.data_source.name}.{self.name} ({self.data_type})"


class DataRecord(models.Model):
    data_source = models.ForeignKey(DataSource, on_delete=models.CASCADE, related_name="records")
    external_id = models.CharField(max_length=255)
    payload = models.JSONField(default=dict)
    search_tsv = SearchVectorField(null=True, blank=True)
    updated_at = models.DateTimeField(auto_now=True)
    deleted_at = models.DateTimeField(null=True, blank=True)

    class Meta:
        db_table = "data_records"
        constraints = [
            models.UniqueConstraint(
                fields=["data_source", "external_id"], name="data_records_unique_external_id"
            ),
        ]
        indexes = [
            GinIndex(
                fields=["payload"], name="data_records_payload_gin", opclasses=["jsonb_path_ops"]
            ),
            models.Index(fields=["data_source", "deleted_at"], name="data_records_active_idx"),
        ]

    def __str__(self):
        return f"{self.external_id} @ source {self.data_source_id}"


class DataSourceSync(models.Model):
    class Mode(models.TextChoices):
        UPSERT = "upsert", "Upsert (keep rows not in the file)"
        REPLACE = "replace", "Replace (remove rows not in the file)"

    data_source = models.ForeignKey(DataSource, on_delete=models.CASCADE, related_name="syncs")
    mode = models.CharField(max_length=16, choices=Mode.choices, default=Mode.UPSERT)
    filename = models.CharField(max_length=255, blank=True)
    rows_in = models.PositiveIntegerField(default=0)
    rows_upserted = models.PositiveIntegerField(default=0)
    rows_rejected = models.PositiveIntegerField(default=0)
    errors = models.JSONField(default=list, blank=True)
    # The E2 modelling-trap warnings. Advisory: they never block an import.
    warnings = models.JSONField(default=list, blank=True)
    started_at = models.DateTimeField(auto_now_add=True)
    finished_at = models.DateTimeField(null=True, blank=True)

    class Meta:
        db_table = "data_source_syncs"
        ordering = ("-started_at", "-id")
