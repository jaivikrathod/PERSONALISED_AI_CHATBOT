"""Serializers for authentication and user management."""

from django.contrib.auth import get_user_model
from django.contrib.auth.password_validation import validate_password
from rest_framework import serializers
from rest_framework_simplejwt.serializers import TokenObtainPairSerializer

from core.enums import UserRole

User = get_user_model()


class UserSerializer(serializers.ModelSerializer):
    """Read representation of a user."""

    company_uuid = serializers.UUIDField(source="company.uuid", read_only=True, allow_null=True)
    company_name = serializers.CharField(source="company.name", read_only=True, allow_null=True)

    class Meta:
        model = User
        fields = [
            "uuid",
            "email",
            "full_name",
            "phone",
            "role",
            "company_uuid",
            "company_name",
            "is_active",
            "created_at",
        ]
        read_only_fields = ["uuid", "role", "is_active", "created_at"]


class RegisterSerializer(serializers.ModelSerializer):
    """Self-service registration. Creates a COMPANY_ADMIN by default; the
    companies module pairs this with company creation.
    """

    password = serializers.CharField(write_only=True, validators=[validate_password])
    password_confirm = serializers.CharField(write_only=True)

    class Meta:
        model = User
        fields = ["email", "full_name", "phone", "password", "password_confirm"]

    def validate(self, attrs):
        if attrs["password"] != attrs.pop("password_confirm"):
            raise serializers.ValidationError({"password_confirm": "Passwords do not match."})
        return attrs

    def create(self, validated_data):
        password = validated_data.pop("password")
        # Public sign-ups become company admins (they will create their company).
        validated_data.setdefault("role", UserRole.COMPANY_ADMIN)
        return User.objects.create_user(password=password, **validated_data)


class TeamMemberCreateSerializer(serializers.ModelSerializer):
    """Used by COMPANY_ADMIN/MANAGER to invite agents/managers to their company."""

    password = serializers.CharField(write_only=True, validators=[validate_password])

    class Meta:
        model = User
        fields = ["email", "full_name", "phone", "password", "role"]

    def validate_role(self, value):
        if value == UserRole.SUPER_ADMIN:
            raise serializers.ValidationError("Cannot create a super admin via this endpoint.")
        return value

    def create(self, validated_data):
        password = validated_data.pop("password")
        company = self.context["request"].user.company
        return User.objects.create_user(password=password, company=company, **validated_data)


class ChangePasswordSerializer(serializers.Serializer):
    old_password = serializers.CharField(write_only=True)
    new_password = serializers.CharField(write_only=True, validators=[validate_password])

    def validate_old_password(self, value):
        if not self.context["request"].user.check_password(value):
            raise serializers.ValidationError("Current password is incorrect.")
        return value

    def save(self, **kwargs):
        user = self.context["request"].user
        user.set_password(self.validated_data["new_password"])
        user.save(update_fields=["password"])
        return user


class CustomTokenObtainPairSerializer(TokenObtainPairSerializer):
    """Embed role + tenant info into the JWT and the login response."""

    @classmethod
    def get_token(cls, user):
        token = super().get_token(user)
        token["role"] = user.role
        token["company_id"] = user.company_id
        token["email"] = user.email
        return token

    def validate(self, attrs):
        data = super().validate(attrs)
        data["user"] = UserSerializer(self.user).data
        return data
