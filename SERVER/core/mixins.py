"""ViewSet mixins that enforce tenant isolation automatically."""

from core.enums import UserRole


class CompanyScopedQuerysetMixin:
    """Restrict a ViewSet's queryset to the requesting user's company.

    The model (or a related lookup) must be reachable by a company filter.
    Set `company_field` on the view if it differs from the default "company".
    SUPER_ADMIN sees everything (optionally narrowed by ?company=<uuid>).
    """

    company_field = "company"

    def get_queryset(self):
        qs = super().get_queryset()
        user = self.request.user

        if not user.is_authenticated:
            return qs.none()

        if user.role == UserRole.SUPER_ADMIN:
            company_uuid = self.request.query_params.get("company")
            if company_uuid:
                return qs.filter(**{f"{self.company_field}__uuid": company_uuid})
            return qs

        if user.company_id is None:
            return qs.none()
        return qs.filter(**{f"{self.company_field}_id": user.company_id})


class CompanyCreateMixin:
    """Inject the user's company on create so clients can't spoof tenancy."""

    def perform_create(self, serializer):
        user = self.request.user
        if user.role == UserRole.SUPER_ADMIN and "company" in serializer.validated_data:
            serializer.save()
        else:
            serializer.save(company_id=user.company_id)
