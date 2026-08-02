from django.urls import re_path

from .consumers import AgentConsumer

# WebSocket routes for the human-agent console. Mounted by config/asgi.py.
websocket_urlpatterns = [
    re_path(r"^ws/agent/$", AgentConsumer.as_asgi()),
]
