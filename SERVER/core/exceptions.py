"""Domain exceptions + a uniform DRF exception handler.

All API errors return the shape::

    {"success": false, "error": {"code": "...", "message": "...", "detail": ...}}
"""

import logging

from rest_framework import status
from rest_framework.exceptions import APIException
from rest_framework.views import exception_handler as drf_exception_handler

logger = logging.getLogger(__name__)


class ServiceError(APIException):
    """Base class for service-layer errors surfaced to the API."""

    status_code = status.HTTP_400_BAD_REQUEST
    default_detail = "A service error occurred."
    default_code = "service_error"


class ProviderError(ServiceError):
    status_code = status.HTTP_502_BAD_GATEWAY
    default_detail = "Upstream AI provider failed."
    default_code = "provider_error"


class TenantIsolationError(APIException):
    status_code = status.HTTP_403_FORBIDDEN
    default_detail = "Cross-tenant access is not allowed."
    default_code = "tenant_isolation"


def custom_exception_handler(exc, context):
    """Wrap DRF's default handler in a consistent envelope."""
    response = drf_exception_handler(exc, context)

    if response is None:
        # Unhandled -> log and return a generic 500 (never leak internals).
        logger.exception("Unhandled exception in %s", context.get("view"))
        from rest_framework.response import Response

        return Response(
            {
                "success": False,
                "error": {
                    "code": "internal_error",
                    "message": "An unexpected error occurred.",
                },
            },
            status=status.HTTP_500_INTERNAL_SERVER_ERROR,
        )

    code = getattr(exc, "default_code", "error")
    detail = response.data
    message = detail.get("detail") if isinstance(detail, dict) and "detail" in detail else None

    response.data = {
        "success": False,
        "error": {
            "code": code,
            "message": message or "Request failed.",
            "detail": detail,
        },
    }
    return response
