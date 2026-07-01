from rest_framework import serializers

from .models import User


class UserSerializer(serializers.ModelSerializer):
    """Serializer for the User model with read/write validation.

    `password` is write-only: accepted on create/update but never returned.
    It is hashed before being stored.
    """

    # A nested, read-only convenience field so responses show the company name
    # without an extra request. Writes still use the `company` id field.
    company_name = serializers.CharField(source="company.name", read_only=True)

    password = serializers.CharField(write_only=True, min_length=6)

    class Meta:
        model = User
        fields = [
            "id",
            "name",
            "email",
            "password",
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

    def create(self, validated_data):
        """Create a user, hashing the raw password before saving."""
        raw_password = validated_data.pop("password")
        user = User(**validated_data)
        user.set_password(raw_password)
        user.save()
        return user

    def update(self, instance, validated_data):
        """Update a user, re-hashing the password only if one was supplied."""
        raw_password = validated_data.pop("password", None)
        for attr, value in validated_data.items():
            setattr(instance, attr, value)
        if raw_password:
            instance.set_password(raw_password)
        instance.save()
        return instance


class LoginSerializer(serializers.Serializer):
    """Validates login credentials (email + password)."""

    email = serializers.EmailField()
    password = serializers.CharField(write_only=True)
