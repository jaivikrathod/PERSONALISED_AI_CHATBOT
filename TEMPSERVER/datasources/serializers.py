import re

from rest_framework import serializers

from . import types
from .models import DataSource, DataSourceField, DataSourceSync
from .search import fixed_filter_errors

CONFIG_KEYS = {"fixed_filters", "id_field"}


def unique_source_name(chatbot, display_name: str) -> str:
    base = re.sub(r"[^a-z0-9]+", "_", display_name.lower()).strip("_")[:40] or "items"
    if not base[0].isalpha():
        base = f"items_{base}"[:40]
    candidate, n = base, 2
    while DataSource.objects.filter(chatbot=chatbot, name=candidate).exists():
        candidate = f"{base}_{n}"
        n += 1
    return candidate


class DataSourceSerializer(serializers.ModelSerializer):
    tool_name = serializers.CharField(read_only=True)

    class Meta:
        model = DataSource
        fields = [
            "id", "name", "display_name", "description", "adapter", "config",
            "row_count", "sync_status", "last_synced_at", "schema_confirmed_at",
            "is_published", "tool_name", "created_at", "updated_at",
        ]
        read_only_fields = [
            "adapter", "row_count", "sync_status", "last_synced_at",
            "schema_confirmed_at", "is_published", "created_at", "updated_at",
        ]
        extra_kwargs = {"name": {"required": False}}

    def validate_name(self, value):
        if self.instance and self.instance.is_published and value != self.instance.name:
            raise serializers.ValidationError("Unpublish before renaming: the name is the tool name.")
        return value

    def validate_config(self, value):
        if not isinstance(value, dict) or set(value) - CONFIG_KEYS:
            raise serializers.ValidationError(f"Allowed keys: {sorted(CONFIG_KEYS)}.")
        merged = {**((self.instance.config or {}) if self.instance else {}), **value}
        if "fixed_filters" in value and self.instance is not None:
            probe = DataSource(config=merged)
            errors = fixed_filter_errors(probe, {f.name: f for f in self.instance.fields.all()})
            if errors:
                raise serializers.ValidationError(errors)
        return merged


class DataSourceFieldSerializer(serializers.ModelSerializer):
    class Meta:
        model = DataSourceField
        fields = [
            "id", "data_source", "name", "label", "data_type", "path", "description",
            "unit", "is_exposed", "is_filterable", "is_sortable", "is_searchable",
            "is_returned", "allowed_operators", "enum_values", "cardinality",
            "display_order",
        ]
        read_only_fields = ["data_source", "name", "path", "enum_values", "cardinality"]

    def validate(self, attrs):
        field = self.instance
        data_type = attrs.get("data_type", field.data_type)
        operators = attrs.get("allowed_operators")

        if "data_type" in attrs and data_type != field.data_type and operators is None:
            # Strings pick enum vs free text once cardinality is recomputed.
            attrs["allowed_operators"] = [] if data_type == types.STRING else types.default_operators(data_type)
        elif operators is not None:
            invalid = sorted(set(operators) - set(types.OPERATORS_BY_TYPE[data_type]))
            if invalid:
                raise serializers.ValidationError({
                    "allowed_operators": f"{invalid} do not apply to {data_type} fields. "
                    f"Allowed: {types.OPERATORS_BY_TYPE[data_type]}."
                })

        exposed = attrs.get("is_exposed", field.is_exposed)
        description = attrs.get("description", field.description)
        if field.data_source.is_published and exposed and not description.strip():
            raise serializers.ValidationError({"description": "Exposed fields of a published source need a description."})
        return attrs

    def update(self, instance, validated_data):
        type_changed = "data_type" in validated_data and validated_data["data_type"] != instance.data_type
        instance = super().update(instance, validated_data)
        if type_changed:
            from .ingest import recoerce_field
            from .publishing import refresh_tool

            recoerce_field(instance)
            refresh_tool(instance.data_source)
            instance.refresh_from_db()
        return instance


class DataSourceSyncSerializer(serializers.ModelSerializer):
    class Meta:
        model = DataSourceSync
        fields = [
            "id", "mode", "filename", "rows_in", "rows_upserted", "rows_rejected",
            "errors", "warnings", "started_at", "finished_at",
        ]
        read_only_fields = fields
