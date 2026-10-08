""" Pending mobile logins between the password step and the OTP step.

The v1 mobile login is two-step: POST login/ checks the password and returns an
identityToken; POST 2fa/token-verify/ checks the OTP for that identityToken and
returns the JWT. Only identityToken -> user id is kept, in the shared cache, for
a few minutes and for a limited number of OTP attempts - never the password.
"""

import secrets
import time

from django.core.cache import cache

PENDING_LOGIN_SECONDS = 300
MAX_OTP_ATTEMPTS = 5
_KEY = 'mobile_login:{}'


def start_pending_login(user_id):
    """ A new random identityToken for a user whose password was just verified. """
    token = secrets.token_urlsafe(32)
    cache.set(_KEY.format(token), {'user_id': user_id, 'attempts': 0,
                                   'expires_at': time.time() + PENDING_LOGIN_SECONDS},
              timeout=PENDING_LOGIN_SECONDS)
    return token


def get_pending_login(token):
    """ The user id waiting for an OTP under this identityToken, or None. """
    if not token or not isinstance(token, str):
        return None
    pending = cache.get(_KEY.format(token))
    return pending['user_id'] if pending else None


def record_failed_otp(token):
    """ Counts a wrong OTP; the pending login is dropped after MAX_OTP_ATTEMPTS.
    Returns True while more attempts are allowed. """
    key = _KEY.format(token)
    pending = cache.get(key)
    if not pending:
        return False
    pending['attempts'] += 1
    if pending['attempts'] >= MAX_OTP_ATTEMPTS:
        cache.delete(key)
        return False
    remaining = int(pending['expires_at'] - time.time())
    if remaining <= 0:
        cache.delete(key)
        return False
    cache.set(key, pending, timeout=remaining)  # keeps the original expiry
    return True


def finish_pending_login(token):
    """ Single use: the identityToken is spent once the JWT has been issued. """
    cache.delete(_KEY.format(token))
