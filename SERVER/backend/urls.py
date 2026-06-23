"""Root URL configuration.

All REST endpoints are namespaced under /api/v1/. OpenAPI schema + Swagger UI +
ReDoc are served for interactive documentation.
"""

from django.conf import settings
from django.conf.urls.static import static
from django.contrib import admin
from django.http import JsonResponse
from django.urls import include, path
from drf_spectacular.views import (
    SpectacularAPIView,
    SpectacularRedocView,
    SpectacularSwaggerView,
)


def health(_request):
    return JsonResponse({"status": "ok"})


api_v1 = [
    path("accounts/", include("accounts.urls")),
    path("companies/", include("companies.urls")),
    path("kb/", include("knowledge_base.urls")),
    path("chatbot/", include("chatbot.urls")),
    path("conversations/", include("conversations.urls")),
    path("agents/", include("agents.urls")),
    path("analytics/", include("analytics.urls")),
    path("integrations/", include("integrations.urls")),
]

urlpatterns = [
    path("admin/", admin.site.urls),
    path("health/", health, name="health"),
    # API
    path("api/v1/", include((api_v1, "api"), namespace="v1")),
    # OpenAPI / Swagger
    path("api/schema/", SpectacularAPIView.as_view(), name="schema"),
    path("api/docs/", SpectacularSwaggerView.as_view(url_name="schema"), name="swagger-ui"),
    path("api/redoc/", SpectacularRedocView.as_view(url_name="schema"), name="redoc"),
]

if settings.DEBUG:
    urlpatterns += static(settings.MEDIA_URL, document_root=settings.MEDIA_ROOT)
