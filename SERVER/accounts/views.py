"""Authentication and user-management endpoints."""

from django.contrib.auth import get_user_model
from drf_spectacular.utils import extend_schema
from rest_framework import status, viewsets
from rest_framework.decorators import action
from rest_framework.permissions import AllowAny, IsAuthenticated
from rest_framework.response import Response
from rest_framework_simplejwt.views import TokenObtainPairView

from core.enums import UserRole
from core.mixins import CompanyScopedQuerysetMixin

from .permissions import CanManageTeam
from .serializers import (
    ChangePasswordSerializer,
    CustomTokenObtainPairSerializer,
    RegisterSerializer,
    TeamMemberCreateSerializer,
    UserSerializer,
)

User = get_user_model()


class LoginView(TokenObtainPairView):
    """POST email + password -> {access, refresh, user}."""

    serializer_class = CustomTokenObtainPairSerializer
    permission_classes = [AllowAny]


@extend_schema(tags=["auth"])
class RegisterView(viewsets.GenericViewSet):
    serializer_class = RegisterSerializer
    permission_classes = [AllowAny]

    @action(detail=False, methods=["post"])
    def register(self, request):
        serializer = self.get_serializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        user = serializer.save()
        return Response(
            {"success": True, "user": UserSerializer(user).data},
            status=status.HTTP_201_CREATED,
        )


@extend_schema(tags=["users"])
class UserViewSet(CompanyScopedQuerysetMixin, viewsets.ModelViewSet):
    """Team-member management, scoped to the requesting user's company."""

    queryset = User.objects.select_related("company").all()
    serializer_class = UserSerializer
    permission_classes = [IsAuthenticated, CanManageTeam]
    filterset_fields = ["role", "is_active"]
    search_fields = ["email", "full_name"]
    ordering_fields = ["created_at", "email"]

    def get_serializer_class(self):
        if self.action == "create":
            return TeamMemberCreateSerializer
        return UserSerializer

    def create(self, request, *args, **kwargs):
        serializer = self.get_serializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        user = serializer.save()
        return Response(
            {"success": True, "user": UserSerializer(user).data},
            status=status.HTTP_201_CREATED,
        )

    @extend_schema(responses=UserSerializer)
    @action(detail=False, methods=["get", "patch"], permission_classes=[IsAuthenticated])
    def me(self, request):
        """Get or update the authenticated user's own profile."""
        if request.method == "PATCH":
            serializer = UserSerializer(request.user, data=request.data, partial=True)
            serializer.is_valid(raise_exception=True)
            serializer.save()
            return Response({"success": True, "user": serializer.data})
        return Response({"success": True, "user": UserSerializer(request.user).data})

    @action(detail=False, methods=["post"], permission_classes=[IsAuthenticated])
    def change_password(self, request):
        serializer = ChangePasswordSerializer(data=request.data, context={"request": request})
        serializer.is_valid(raise_exception=True)
        serializer.save()
        return Response({"success": True, "message": "Password updated."})

    @action(detail=True, methods=["post"])
    def deactivate(self, request, pk=None):
        user = self.get_object()
        if user.role == UserRole.SUPER_ADMIN:
            return Response(
                {"success": False, "message": "Cannot deactivate a super admin."},
                status=status.HTTP_403_FORBIDDEN,
            )
        user.is_active = False
        user.save(update_fields=["is_active"])
        return Response({"success": True, "message": "User deactivated."})
