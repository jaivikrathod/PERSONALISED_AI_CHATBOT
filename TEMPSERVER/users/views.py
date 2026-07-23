from rest_framework import viewsets, filters, status
from rest_framework.response import Response
from rest_framework.views import APIView

from .models import User
from .permissions import IsAdminOrManager
from .serializers import UserSerializer, LoginSerializer


class UserViewSet(viewsets.ModelViewSet):
    """Full CRUD API for User via DRF's ModelViewSet.

    Provides list, retrieve, create, update, partial_update and destroy.
    `select_related("company")` avoids N+1 queries when serializing
    the related company name.
    """

    queryset = User.objects.select_related("company").all()
    serializer_class = UserSerializer
    permission_classes = [IsAdminOrManager]

    # Enable search and ordering query params, e.g.
    #   /api/users/?search=john
    #   /api/users/?ordering=name
    filter_backends = [filters.SearchFilter, filters.OrderingFilter]
    search_fields = ["name", "email"]
    ordering_fields = ["name", "created_at", "updated_at"]
    ordering = ["-created_at"]


class ManagedUserViewSet(viewsets.ModelViewSet):
    queryset = User.objects.select_related("company").all()
    serializer_class = UserSerializer
    permission_classes = [IsAdminOrManager]
    filter_backends = [filters.SearchFilter, filters.OrderingFilter]
    search_fields = ["name", "email"]
    ordering_fields = ["name", "created_at", "updated_at"]
    ordering = ["-created_at"]


class LoginView(APIView):
    """POST /api/auth/login/  -> authenticate a user by email + password.

    On success returns the user's public profile (including company id/name)
    which the frontend stores to gate the app. No JWT is issued here; the
    response shape is stable so a token can be added later without breaking
    the client.
    """

    def post(self, request):
        serializer = LoginSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        email = serializer.validated_data["email"].lower()
        password = serializer.validated_data["password"]

        # Generic error message avoids leaking which part was wrong.
        invalid = Response(
            {"error": "Invalid email or password."},
            status=status.HTTP_401_UNAUTHORIZED,
        )

        user = (
            User.objects.select_related("company")
            .filter(email=email, active=True, is_archived=False)
            .first()
        )
        if user is None or not user.check_password(password):
            return invalid

        return Response(UserSerializer(user).data, status=status.HTTP_200_OK)
