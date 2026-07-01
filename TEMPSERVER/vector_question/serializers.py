from rest_framework import serializers

from .models import VectorJob


class VectorJobSerializer(serializers.ModelSerializer):
    """Read-oriented serializer for VectorJob records.

    Jobs are created/updated by the service layer, never directly by clients,
    so all fields are effectively read-only from the API's perspective.
    """

    company_name = serializers.CharField(source="company.name", read_only=True)

    class Meta:
        model = VectorJob
        fields = [
            "id",
            "company",
            "company_name",
            "status",
            "total_questions",
            "processed_questions",
            "failed_questions",
            "started_at",
            "completed_at",
            "error_message",
            "created_at",
            "updated_at",
        ]
        read_only_fields = fields
