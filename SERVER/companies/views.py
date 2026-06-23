"""Company management endpoints."""

from drf_spectacular.utils import extend_schema
from rest_framework import status, viewsets
from rest_framework.decorators import action
from rest_framework.permissions import AllowAny, IsAuthenticated
from rest_framework.response import Response

from core.enums import UserRole
from core.permissions import IsSuperAdmin

from .models import Company, UserCompany
from .permissions import IsCompanyAdminOrSuperAdmin
from .serializers import (
    CompanyOnboardSerializer,
    CompanySerializer,
    UserCompanySerializer,
)


@extend_schema(tags=["companies"])
class CompanyViewSet(viewsets.ModelViewSet):
    """CRUD for companies.

    - SUPER_ADMIN sees/manages all companies.
    - Other roles see only their own company (read), admins can update it.
    """

    serializer_class = CompanySerializer
    permission_classes = [IsAuthenticated]
    lookup_field = "uuid"
    search_fields = ["name", "email"]
    filterset_fields = ["status"]

    def get_queryset(self):
        user = self.request.user
        qs = Company.objects.all()
        if getattr(self, "swagger_fake_view", False) or not user.is_authenticated:
            return qs.none()
        if user.role == UserRole.SUPER_ADMIN:
            return qs
        if user.company_id:
            return qs.filter(id=user.company_id)
        return qs.none()

    def get_permissions(self):
        if self.action in {"create", "destroy"}:
            return [IsSuperAdmin()]
        if self.action in {"update", "partial_update"}:
            return [IsCompanyAdminOrSuperAdmin()]
        return [IsAuthenticated()]

    @extend_schema(request=CompanyOnboardSerializer, responses=CompanyOnboardSerializer)
    @action(detail=False, methods=["post"], permission_classes=[AllowAny])
    def onboard(self, request):
        """Public self-service: create a company + its first admin in one call."""
        serializer = CompanyOnboardSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        result = serializer.save()
        return Response(
            {"success": True, **CompanyOnboardSerializer(result).data},
            status=status.HTTP_201_CREATED,
        )

    @action(detail=True, methods=["get"])
    def members(self, request, uuid=None):
        """List membership records for a company."""
        company = self.get_object()
        memberships = (
            UserCompany.objects.filter(company=company)
            .select_related("user", "company")
            .order_by("role")
        )
        page = self.paginate_queryset(memberships)
        serializer = UserCompanySerializer(page or memberships, many=True)
        if page is not None:
            return self.get_paginated_response(serializer.data)
        return Response({"success": True, "results": serializer.data})


@extend_schema(tags=["companies"])
class UserCompanyViewSet(viewsets.ReadOnlyModelViewSet):
    serializer_class = UserCompanySerializer
    permission_classes = [IsAuthenticated]
    lookup_field = "uuid"

    def get_queryset(self):
        user = self.request.user
        qs = UserCompany.objects.select_related("user", "company")
        if getattr(self, "swagger_fake_view", False) or not user.is_authenticated:
            return qs.none()
        if user.role == UserRole.SUPER_ADMIN:
            return qs
        return qs.filter(company_id=user.company_id)
