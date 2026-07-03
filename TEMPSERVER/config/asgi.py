"""
ASGI config for config project.

It exposes the ASGI callable as a module-level variable named ``application``.

For more information on this file, see
https://docs.djangoproject.com/en/5.2/howto/deployment/asgi/
"""

import os

from django.core.asgi import get_asgi_application

os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'config.settings')

# Initialise Django (populate the app registry) before importing anything that
# touches models — the WebSocket routing imports consumers that use the ORM.
django_asgi_app = get_asgi_application()

from channels.routing import ProtocolTypeRouter, URLRouter  # noqa: E402

from questions.routing import websocket_urlpatterns  # noqa: E402

application = ProtocolTypeRouter(
    {
        # Regular HTTP requests keep going through the standard Django stack.
        "http": django_asgi_app,
        # WebSocket connections are matched against the chatbot routes.
        "websocket": URLRouter(websocket_urlpatterns),
    }
)
