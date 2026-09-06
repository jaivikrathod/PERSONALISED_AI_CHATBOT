from django.db import transaction
from rest_framework import filters, status, viewsets
from rest_framework.permissions import AllowAny
from rest_framework.response import Response
from rest_framework.views import APIView

from config.tenancy import CompanyScopedQuerysetMixin, require_company

from .models import AuthToken, User
from .permissions import IsAdminOrManager, IsAuthenticatedUser
from .serializers import (
    LoginSerializer,
    RegistrationSerializer,
    UserSerializer,
)


def _session_payload(user, raw_token, expires_at):
    """The shape every authentication endpoint returns."""
    return {
        "token": raw_token,
        "expires_at": expires_at,
        "user": UserSerializer(user).data,
    }


class UserViewSet(CompanyScopedQuerysetMixin, viewsets.ModelViewSet):
    """CRUD for the users of the caller's own company.

    The queryset and every write are pinned to the token's company by
    `CompanyScopedQuerysetMixin`, so `company` in a request body is ignored
    rather than trusted.
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


class ManagedUserViewSet(UserViewSet):
    """Kept as a separate route for client compatibility.

    It used to differ by honouring `?company_id=`; that filter is now applied by
    the scoping mixin against the caller's own company, so the two viewsets are
    deliberately identical.
    """


class RegisterView(APIView):
    """POST /api/auth/register/ -> create a company plus its first Admin.

    Open by necessity: this is how a tenant comes into existence. It is the
    *only* unauthenticated way to create a user, and it can only ever create an
    Admin attached to a brand-new company — which is why user creation itself
    is now behind `IsAdminOrManager`.
    """

    authentication_classes: list = []
    permission_classes = [AllowAny]

    def post(self, request):
        serializer = RegistrationSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)

        with transaction.atomic():
            company, admin = serializer.save()

        token, raw = AuthToken.issue(admin)
        return Response(
            {
                **_session_payload(admin, raw, token.expires_at),
                "company": {"id": company.id, "name": company.name},
            },
            status=status.HTTP_201_CREATED,
        )


class LoginView(APIView):
    """POST /api/auth/login/ -> authenticate by email + password.

    Returns a bearer token alongside the profile. The token is the only thing
    that grants access from here on; the profile is for display.
    """

    authentication_classes: list = []
    permission_classes = [AllowAny]

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

        token, raw = AuthToken.issue(user)
        return Response(
            _session_payload(user, raw, token.expires_at),
            status=status.HTTP_200_OK,
        )


class LogoutView(APIView):
    """POST /api/auth/logout/ -> revoke the token used for this request."""

    permission_classes = [IsAuthenticatedUser]

    def post(self, request):
        token = getattr(request, "auth", None)
        if token is not None:
            AuthToken.objects.filter(pk=token.pk).delete()
        return Response(status=status.HTTP_204_NO_CONTENT)


class MeView(APIView):
    """GET /api/auth/me/ -> the profile behind the current token.

    Lets the client verify a stored token on boot instead of trusting a cached
    profile in localStorage.
    """

    permission_classes = [IsAuthenticatedUser]

    def get(self, request):
        require_company(request)
        return Response(UserSerializer(request.user).data)
