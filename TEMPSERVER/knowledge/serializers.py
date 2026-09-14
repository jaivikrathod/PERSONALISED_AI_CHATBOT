from rest_framework import serializers

from .models import IngestionJob, KnowledgeDocument, KnowledgeSource


class KnowledgeSourceSerializer(serializers.ModelSerializer):
    document_count = serializers.IntegerField(source="documents.count", read_only=True)

    class Meta:
        model = KnowledgeSource
        fields = ["id", "name", "kind", "status", "last_indexed_at", "document_count", "created_at", "updated_at"]
        read_only_fields = ["status", "last_indexed_at", "document_count", "created_at", "updated_at"]

    def validate_kind(self, value):
        if self.instance is not None and value != self.instance.kind:
            raise serializers.ValidationError("A source's kind cannot change.")
        if value == KnowledgeSource.Kind.FAQ:
            raise serializers.ValidationError("The FAQ source is managed from the Knowledge Base questions.")
        if value == KnowledgeSource.Kind.URL:
            # Fetching a company-supplied URL is an SSRF primitive; it waits for
            # the Phase 3 egress guard (B6).
            raise serializers.ValidationError("Web page sources are not available yet.")
        return value


class KnowledgeDocumentSerializer(serializers.ModelSerializer):
    chunk_count = serializers.IntegerField(source="chunks.count", read_only=True)

    class Meta:
        model = KnowledgeDocument
        fields = ["id", "source", "external_ref", "title", "file_type", "status", "error", "chunk_count", "created_at", "updated_at"]
        read_only_fields = fields


class IngestionJobSerializer(serializers.ModelSerializer):
    progress = serializers.IntegerField(read_only=True)

    class Meta:
        model = IngestionJob
        fields = [
            "id", "source", "document", "kind", "status", "progress", "done_steps",
            "total_steps", "message", "error", "filename", "created_at", "started_at", "finished_at",
        ]
        read_only_fields = fields
