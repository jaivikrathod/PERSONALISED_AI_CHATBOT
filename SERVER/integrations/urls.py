from django.urls import include, path
from rest_framework.routers import DefaultRouter

from .views import (
    WidgetBootstrapView,
    WidgetChatView,
    WidgetConfigViewSet,
    WidgetStartView,
)

router = DefaultRouter()
router.register("widget-configs", WidgetConfigViewSet, basename="widget-config")

urlpatterns = [
    path("", include(router.urls)),
    # Public, token-authenticated widget endpoints.
    path("widget/config/", WidgetBootstrapView.as_view(), name="widget-bootstrap"),
    path("widget/start/", WidgetStartView.as_view(), name="widget-start"),
    path("widget/chat/", WidgetChatView.as_view(), name="widget-chat"),
]
