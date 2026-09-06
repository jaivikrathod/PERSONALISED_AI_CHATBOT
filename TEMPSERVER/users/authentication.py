"""Bearer-token authentication for the standalone `users.User` model.

The platform does not use `django.contrib.auth.User`, so DRF's bundled
`TokenAuthentication` (which is tied to the auth app) does not apply. This is
the equivalent for our model:

    Authorization: Bearer <raw token>

Only the SHA-256 digest of a token is stored (see `users.models.AuthToken`), so
a database dump does not hand out live sessions. The raw value is returned
exactly once, at login.
"""

from __future__ import annotations

from django.utils import timezone
from rest_framework import authentication, exceptions

from .models import AuthToken, hash_token


class BearerTokenAuthentication(authentication.BaseAuthentication):
    """Resolves `Authorization: Bearer <token>` to a `users.User`.

    Returning `None` (rather than raising) when the header is absent lets
    permission classes decide whether anonymous access is acceptable — that is
    what keeps the public chat widget endpoints reachable.
    """

    keyword = "Bearer"

    def authenticate(self, request):
        header = authentication.get_authorization_header(request).split()

        if not header or header[0].lower() != self.keyword.lower().encode():
            return None
        if len(header) != 2:
            raise exceptions.AuthenticationFailed("Malformed Authorization header.")

        raw = header[1].decode()
        token = (
            AuthToken.objects.select_related("user", "user__company")
            .filter(key_hash=hash_token(raw))
            .first()
        )

        # Same message for "no such token" and "expired": an attacker learns
        # nothing about which tokens exist.
        if token is None or token.is_expired:
            raise exceptions.AuthenticationFailed("Invalid or expired token.")

        user = token.user
        if not user.active or user.is_archived:
            raise exceptions.AuthenticationFailed("This account is no longer active.")

        # Cheap liveness stamp, skipped when it was already written this hour so
        # a chatty client doesn't turn every read into a write.
        now = timezone.now()
        if token.last_used_at is None or (now - token.last_used_at).total_seconds() > 3600:
            AuthToken.objects.filter(pk=token.pk).update(last_used_at=now)

        return (user, token)

    def authenticate_header(self, request):
        return self.keyword
