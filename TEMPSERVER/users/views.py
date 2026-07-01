from rest_framework import viewsets, filters

from .models import User
from .serializers import UserSerializer


class UserViewSet(viewsets.ModelViewSet):
    """Full CRUD API for User via DRF's ModelViewSet.

    Provides list, retrieve, create, update, partial_update and destroy.
    `select_related("company")` avoids N+1 queries when serializing
    the related company name.
    """

    queryset = User.objects.select_related("company").all()
    serializer_class = UserSerializer

    # Enable search and ordering query params, e.g.
    #   /api/users/?search=john
    #   /api/users/?ordering=name
    filter_backends = [filters.SearchFilter, filters.OrderingFilter]
    search_fields = ["name", "email"]
    ordering_fields = ["name", "created_at", "updated_at"]
    ordering = ["-created_at"]
