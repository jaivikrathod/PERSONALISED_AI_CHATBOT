"""Widget token authentication for public (unauthenticated-user) endpoints.

The browser widget identifies itself with the chatbot's `widget_token`, sent as
`Authorization: Widget <token>` or an `X-Widget-Token` header. There is no user;
instead we attach the resolved Chatbot to `request.auth` for the view to use.
"""

from rest_framework import authentication, exceptions

from chatbot.models import Chatbot


class WidgetTokenAuthentication(authentication.BaseAuthentication):
    keyword = "Widget"

    def authenticate(self, request):
        token = self._extract_token(request)
        if not token:
            return None  # let other authenticators / AllowAny handle it

        try:
            chatbot = Chatbot.objects.select_related("company").get(
                widget_token=token, active=True
            )
        except Chatbot.DoesNotExist:
            raise exceptions.AuthenticationFailed("Invalid or inactive widget token.")

        # (user, auth) — user stays None (AnonymousUser); chatbot is the credential.
        return (None, chatbot)

    def _extract_token(self, request):
        header = authentication.get_authorization_header(request).decode("utf-8")
        if header.startswith(f"{self.keyword} "):
            return header.split(" ", 1)[1].strip()
        return request.headers.get("X-Widget-Token")


# Teach drf-spectacular how to document the widget token scheme.
try:
    from drf_spectacular.extensions import OpenApiAuthenticationExtension

    class WidgetTokenScheme(OpenApiAuthenticationExtension):
        target_class = "integrations.authentication.WidgetTokenAuthentication"
        name = "WidgetToken"

        def get_security_definition(self, auto_schema):
            return {
                "type": "apiKey",
                "in": "header",
                "name": "Authorization",
                "description": "Widget token, e.g. `Authorization: Widget <widget_token>`.",
            }
except ImportError:  # drf-spectacular optional at runtime
    pass
