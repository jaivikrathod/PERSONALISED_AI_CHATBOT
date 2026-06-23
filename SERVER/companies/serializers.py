from django.db import transaction
from rest_framework import serializers

from accounts.serializers import RegisterSerializer, UserSerializer
from core.enums import UserRole

from .models import Company, UserCompany


class CompanySerializer(serializers.ModelSerializer):
    class Meta:
        model = Company
        fields = [
            "uuid",
            "name",
            "email",
            "phone",
            "website",
            "logo",
            "status",
            "created_at",
            "updated_at",
        ]
        read_only_fields = ["uuid", "status", "created_at", "updated_at"]


class CompanyOnboardSerializer(serializers.Serializer):
    """Single-call onboarding: create the company AND its first COMPANY_ADMIN."""

    company = CompanySerializer()
    admin = RegisterSerializer()

    @transaction.atomic
    def create(self, validated_data):
        company = Company.objects.create(**validated_data["company"])

        admin_data = validated_data["admin"]
        admin_data["role"] = UserRole.COMPANY_ADMIN
        admin = RegisterSerializer().create(admin_data)
        admin.company = company
        admin.save(update_fields=["company"])
        return {"company": company, "admin": admin}

    def to_representation(self, instance):
        return {
            "company": CompanySerializer(instance["company"]).data,
            "admin": UserSerializer(instance["admin"]).data,
        }


class UserCompanySerializer(serializers.ModelSerializer):
    user = UserSerializer(read_only=True)
    company_uuid = serializers.UUIDField(source="company.uuid", read_only=True)

    class Meta:
        model = UserCompany
        fields = ["uuid", "user", "company_uuid", "role", "created_at"]
        read_only_fields = ["uuid", "created_at"]
