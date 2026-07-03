from django.urls import re_path

from .consumers import ChatConsumer

# WebSocket URL patterns for the chatbot. Mounted by config/asgi.py.
websocket_urlpatterns = [
    re_path(r"^ws/chat/$", ChatConsumer.as_asgi()),
]
