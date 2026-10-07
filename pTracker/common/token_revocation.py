import logging
import time

from django.core.cache import cache
from rest_framework_simplejwt.exceptions import TokenError
from rest_framework_simplejwt.settings import api_settings
from rest_framework_simplejwt.tokens import AccessToken

logger = logging.getLogger(__name__)

REVOKED_JTI_KEY = 'jwt:revoked:{}'


class RevocableAccessToken(AccessToken):
    """
    AccessToken that is rejected once its jti has been revoked (logout).

    Wired in via SIMPLE_JWT['AUTH_TOKEN_CLASSES'], so every
    JWTAuthentication subclass (incl. PlatformJWTAuthentication) checks it
    without per-view changes. Revoked jtis live in the cache only until the
    token would have expired anyway.
    """

    def verify(self) -> None:
        super().verify()
        jti = self.payload.get(api_settings.JTI_CLAIM)
        try:
            is_revoked = cache.get(REVOKED_JTI_KEY.format(jti)) is not None
        except Exception:
            # Fail open: a cache outage must not lock every user out. The
            # token is still signature-checked and expires normally.
            logger.exception('Token revocation cache unavailable')
            return
        if is_revoked:
            raise TokenError('Token has been revoked')


def revoke_access_token(token) -> bool:
    """Revoke a validated access token until its exp. Returns success."""
    jti = token.payload.get(api_settings.JTI_CLAIM)
    exp = token.payload.get('exp')
    if not jti or not exp:
        return False
    timeout = int(exp - time.time())
    if timeout <= 0:
        return True
    try:
        cache.set(REVOKED_JTI_KEY.format(jti), 1, timeout=timeout)
    except Exception:
        logger.exception('Failed to revoke access token')
        return False
    return True
