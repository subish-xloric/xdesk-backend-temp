""" One-time challenges for biometric login.

POST biometric-challenge/ issues a random challenge for a device; POST
biometric-authentication/ must return that challenge signed with the device's
private key. A challenge lives in the shared cache for a short time, belongs to
one device and is spent on its first use (right or wrong), so a captured
signature can never be replayed.
"""

import secrets

from django.core.cache import cache

CHALLENGE_SECONDS = 120
_KEY = 'biometric_challenge:{}'


def issue_challenge(key_identifier):
    challenge = secrets.token_urlsafe(32)
    cache.set(_KEY.format(challenge), key_identifier, timeout=CHALLENGE_SECONDS)
    return challenge


def consume_challenge(challenge, key_identifier):
    """ True only for an unexpired challenge issued to this device. Whatever the
    result, the challenge cannot be used again. """
    if not challenge or not isinstance(challenge, str):
        return False
    key = _KEY.format(challenge)
    issued_to = cache.get(key)
    # delete() reports whether this request removed it, so two concurrent
    # requests with the same challenge cannot both succeed.
    if issued_to is None or not cache.delete(key):
        return False
    return issued_to == key_identifier
