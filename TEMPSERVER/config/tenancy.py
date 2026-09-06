"""Tenant scoping.

One rule, applied everywhere: **the company a request may touch is derived from
the authenticated token, never from the request.** Before this module, every
list endpoint took `?company_id=` on trust, which meant any caller could read
any tenant's data by changing a number in the URL.

`?company_id=` is still accepted on list endpoints, but only as a *narrowing*
filter inside the caller's own company — passing someone else's id returns an
empty page rather than their rows.
"""

from __future__ import annotations

from rest_framework.exceptions import PermissionDenied


def company_id_for(request) -> int | None:
    """The authenticated caller's company, or None when unauthenticated."""
    user = getattr(request, "user", None)
    if user is None or not getattr(user, "is_authenticated", False):
        return None
    return user.company_id


def require_company(request) -> int:
    company_id = company_id_for(request)
    if company_id is None:
        raise PermissionDenied("Authentication required.")
    return company_id


def assert_own_company(request, company_id) -> int:
    """Guard for endpoints that carry a company id in the URL path."""
    own = require_company(request)
    if company_id is None or int(company_id) != int(own):
        raise PermissionDenied("This resource belongs to another company.")
    return own


class CompanyScopedQuerysetMixin:
    """Confines a `ModelViewSet` to the caller's company, in both directions.

    Reads are filtered to the caller's company; writes have `company` forced to
    it, so a client cannot create or move a row into another tenant by putting a
    different id in the request body.
    """

    company_lookup = "company_id"

    def get_queryset(self):
        queryset = super().get_queryset()
        company_id = require_company(self.request)
        queryset = queryset.filter(**{self.company_lookup: company_id})

        # Optional narrowing within the caller's own company. Kept for client
        # compatibility; it can no longer widen access.
        requested = self.request.query_params.get("company_id")
        if requested not in (None, "", str(company_id)):
            return queryset.none()

        return queryset

    def perform_create(self, serializer):
        serializer.save(company_id=require_company(self.request))

    def perform_update(self, serializer):
        serializer.save(company_id=require_company(self.request))
