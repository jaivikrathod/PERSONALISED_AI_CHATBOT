"""WebSocket JWT authentication middleware for Django Channels.

Authenticates the connecting socket from a `?token=<access_jwt>` query param
(browsers can't set Authorization headers on WebSocket handshakes). Populates
`scope["user"]`. Anonymous sockets are allowed through so consumers can decide
whether a given room (e.g. a public visitor widget) needs auth.
"""

from urllib.parse import parse_qs

from channels.db import database_sync_to_async
from channels.middleware import BaseMiddleware
from django.contrib.auth.models import AnonymousUser


@database_sync_to_async
def _get_user(validated_token):
    from rest_framework_simplejwt.authentication import JWTAuthentication

    auth = JWTAuthentication()
    try:
        return auth.get_user(validated_token)
    except Exception:
        return AnonymousUser()


class JWTAuthMiddleware(BaseMiddleware):
    async def __call__(self, scope, receive, send):
        from rest_framework_simplejwt.tokens import AccessToken
        from rest_framework_simplejwt.exceptions import TokenError

        scope["user"] = AnonymousUser()

        query = parse_qs(scope.get("query_string", b"").decode())
        token = (query.get("token") or [None])[0]

        if token:
            try:
                validated = AccessToken(token)
                scope["user"] = await _get_user(validated)
            except TokenError:
                scope["user"] = AnonymousUser()

        return await super().__call__(scope, receive, send)
