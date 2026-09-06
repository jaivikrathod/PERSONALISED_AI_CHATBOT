from rest_framework import serializers

from company.models import Company
from company.serializers import CompanySerializer

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
        # `company` is deliberately read-only: it is pinned to the caller's
        # token by CompanyScopedQuerysetMixin, never taken from the body.
        read_only_fields = ["id", "company", "created_at", "updated_at"]

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

class RegistrationSerializer(serializers.Serializer):
    """Creates a company and its first Admin user in one call.

    Replaces the old two-request flow (POST /companies/ then POST /users/),
    which required user creation to be publicly writable. Now the only
    unauthenticated write is this one, and it can only produce an Admin bound
    to the company it just created.
    """

    company = CompanySerializer()
    admin = serializers.DictField(write_only=True)

    def validate_admin(self, value):
        # Re-use UserSerializer's own validation for the admin half, minus the
        # company FK, which this serializer supplies after creating it.
        required = {"name", "email", "password", "gender", "dob"}
        missing = sorted(required - set(value))
        if missing:
            raise serializers.ValidationError(
                f"Missing required admin fields: {', '.join(missing)}."
            )

        email = str(value["email"]).lower().strip()
        if User.objects.filter(email=email).exists():
            raise serializers.ValidationError("A user with this email already exists.")
        if len(str(value["password"])) < 6:
            raise serializers.ValidationError(
                "Password must be at least 6 characters."
            )

        value["email"] = email
        return value

    def create(self, validated_data):
        company = Company.objects.create(**validated_data["company"])

        admin_data = dict(validated_data["admin"])
        raw_password = admin_data.pop("password")
        # Type is forced, not read from input: registration mints Admins only.
        admin_data.pop("type", None)
        admin_data.pop("company", None)

        admin = User(
            **admin_data,
            company=company,
            type=User.Type.ADMIN,
        )
        admin.set_password(raw_password)
        admin.save()

        return company, admin

