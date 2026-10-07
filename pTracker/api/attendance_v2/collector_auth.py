""" Authentication for external attendance collectors.

A collector sends two headers on every request:

    X-Collector-Id:  COL-001
    X-Collector-Key: <secret issued once by an administrator>

Only a SHA-256 hash of the key is stored (the key is 256 bits of randomness,
so a fast hash is appropriate), compared in constant time. The authenticated
principal is the collector, never an employee: ModuleGateMiddleware passes it
through, and the company comes from the collector row. The key never appears
in logs or responses.
"""

import hashlib
import hmac
import secrets

from rest_framework import permissions
from rest_framework.authentication import BaseAuthentication
from rest_framework.exceptions import AuthenticationFailed
from rest_framework.throttling import SimpleRateThrottle

from pTracker.api.attendance_v2.attendance_v2_helper import v2_setting
from pTracker.dataaccess.attendance_v2_access.device_da import CollectorDA

KEY_PREFIX = 'attv2_'
_INVALID = 'Invalid collector credentials'


def generate_collector_key():
    """ Returns (plain_key, key_hash, display_prefix). """
    plain = KEY_PREFIX + secrets.token_urlsafe(32)
    return plain, hash_key(plain), plain[:12]


def hash_key(plain):
    return hashlib.sha256(plain.encode('utf-8')).hexdigest()


class CollectorPrincipal:
    """ request.user for collector requests. Deliberately not an auth User. """
    is_authenticated = True
    is_active = True
    is_anonymous = False

    def __init__(self, collector):
        self.collector = collector
        self.pk = None

    def __str__(self):
        return f'collector:{self.collector.collector_id}'


class CollectorAuthentication(BaseAuthentication):

    def authenticate(self, request):
        collector_id = request.META.get('HTTP_X_COLLECTOR_ID')
        key = request.META.get('HTTP_X_COLLECTOR_KEY')
        if not collector_id and not key:
            return None
        if not collector_id or not key or len(collector_id) > 64 or len(key) > 200:
            raise AuthenticationFailed(_INVALID)

        collector = CollectorDA().get_collector_for_auth(collector_id)
        # Hash is always computed so response timing does not reveal whether
        # the collector id exists.
        supplied_hash = hash_key(key)
        stored_hash = collector.api_key_hash if collector else '0' * 64
        if not hmac.compare_digest(supplied_hash, stored_hash) or collector is None:
            raise AuthenticationFailed(_INVALID)
        if not collector.is_active or not collector.company.is_active:
            raise AuthenticationFailed('Collector is disabled')
        return CollectorPrincipal(collector), None

    def authenticate_header(self, request):
        return 'Collector realm="attendance-v2"'


class IsCollector(permissions.BasePermission):

    def has_permission(self, request, view):
        return isinstance(getattr(request, 'user', None), CollectorPrincipal)


class CollectorTransportIsSecure(permissions.BasePermission):
    """ Rejects plain-HTTP collector calls unless ATTENDANCE_V2['REQUIRE_HTTPS']
    is False (default: required whenever DEBUG is off). X-Forwarded-Proto is
    honoured for TLS terminated at the reverse proxy. """
    message = 'HTTPS is required for collector requests'

    def has_permission(self, request, view):
        if not v2_setting('REQUIRE_HTTPS'):
            return True
        return request.is_secure() or request.META.get('HTTP_X_FORWARDED_PROTO', '').lower() == 'https'


class CollectorRateThrottle(SimpleRateThrottle):
    scope = 'attendance_v2_collector'

    def get_rate(self):
        return v2_setting('COLLECTOR_RATE')

    def get_cache_key(self, request, view):
        user = getattr(request, 'user', None)
        if isinstance(user, CollectorPrincipal):
            return self.cache_format % {'scope': self.scope, 'ident': user.collector.pk}
        return self.cache_format % {'scope': self.scope, 'ident': self.get_ident(request)}
