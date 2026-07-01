from rest_framework import serializers

from .models import User


class UserSerializer(serializers.ModelSerializer):
    """Serializer for the User model with read/write validation."""

    # A nested, read-only convenience field so responses show the company name
    # without an extra request. Writes still use the `company` id field.
    company_name = serializers.CharField(source="company.name", read_only=True)

    class Meta:
        model = User
        fields = [
            "id",
            "name",
            "email",
            "gender",
            "dob",
            "company",
            "company_name",
            "type",
            "active",
            "is_archived",
            "created_at",
            "updated_at",
        ]
        # These are managed by the DB/model and must never be set by clients.
        read_only_fields = ["id", "created_at", "updated_at"]

    def validate_name(self, value):
        """Ensure the name is not blank/whitespace only."""
        value = value.strip()
        if not value:
            raise serializers.ValidationError("Name cannot be empty.")
        return value

    def validate_email(self, value):
        """Normalise email to lowercase for consistent uniqueness checks."""
        return value.lower()
