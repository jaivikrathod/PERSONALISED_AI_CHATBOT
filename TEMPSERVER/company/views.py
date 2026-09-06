from rest_framework import mixins, viewsets

from config.tenancy import require_company
from users.permissions import IsAdmin, IsAuthenticatedUser

from .models import Company
from .serializers import CompanySerializer


class CompanyViewSet(
    mixins.RetrieveModelMixin,
    mixins.ListModelMixin,
    mixins.UpdateModelMixin,
    viewsets.GenericViewSet,
):
    """The caller's own company — read and update only.

    Creation moved to `POST /api/auth/register/`, which makes a company and its
    first Admin atomically; deletion is not exposed over the API at all. The
    queryset is a single row by construction, so there is no id to guess.
    """

    serializer_class = CompanySerializer
    queryset = Company.objects.all()

    def get_permissions(self):
        if self.action in {"update", "partial_update"}:
            return [IsAdmin()]
        return [IsAuthenticatedUser()]

    def get_queryset(self):
        return super().get_queryset().filter(id=require_company(self.request))
