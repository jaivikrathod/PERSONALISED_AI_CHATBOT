"""WebSocket URL routing (imported by backend/asgi.py)."""

from django.urls import re_path

from . import consumers

websocket_urlpatterns = [
    # Public visitor widget socket: ws://host/ws/visitor/<conversation_uuid>/?token=<widget_token>
    re_path(
        r"ws/visitor/(?P<conversation_uuid>[0-9a-f-]+)/$",
        consumers.VisitorConsumer.as_asgi(),
    ),
    # Authenticated agent socket: ws://host/ws/agent/<conversation_uuid>/?token=<jwt_access>
    re_path(
        r"ws/agent/(?P<conversation_uuid>[0-9a-f-]+)/$",
        consumers.AgentConsumer.as_asgi(),
    ),
]
