from rest_framework import serializers

from company.models import Company
from .models import Question


class QuestionSerializer(serializers.ModelSerializer):
    """Serializer for Question with field-level validation.

    The `company` field is a PrimaryKeyRelatedField (DRF's default for a FK),
    so an unknown company id automatically produces a 400 "does not exist"
    error — this satisfies the "ensure the referenced company exists" rule.
    """

    # Read-only convenience field so responses include the company name.
    company_name = serializers.CharField(source="company.name", read_only=True)

    class Meta:
        model = Question
        fields = [
            "id",
            "company",
            "company_name",
            "question",
            "answer",
            "is_archived",
            "is_vectorized",
            "embedding",
            "created_at",
            "updated_at",
        ]
        # Managed by the DB/model & vectorization pipeline; clients can't set these.
        read_only_fields = [
            "id",
            "is_vectorized",
            "embedding",
            "created_at",
            "updated_at",
        ]

    def validate_question(self, value):
        """question cannot be empty or whitespace-only."""
        value = value.strip()
        if not value:
            raise serializers.ValidationError("Question cannot be empty.")
        return value

    def validate_answer(self, value):
        """answer cannot be empty or whitespace-only."""
        value = value.strip()
        if not value:
            raise serializers.ValidationError("Answer cannot be empty.")
        return value
