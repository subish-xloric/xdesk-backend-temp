""" Biometric registration (must be the logged-in user's own device key) and
challenge-response biometric login (one-time challenges, signature check,
unknown/inactive accounts, throttling).

auth_biometric is an unmanaged legacy table that does not exist in the SQLite
test database, so UserDA is replaced by an in-memory fake; users, URL routing,
DRF auth/permissions and the middleware are real. """

import base64
from types import SimpleNamespace
from unittest import mock

import rsa
from pyasn1.codec.der import encoder
from pyasn1.type import univ
from rsa.asn1 import OpenSSLPubKey
from rsa.asn1 import PubKeyHeader
from django.contrib.auth import get_user_model
from django.core.cache import cache
from django.test import TestCase
from rest_framework.test import APIClient

REGISTER_URL = '/v1/api/user/register-for-biometric-authentication/'
LOGIN_URL = '/v1/api/user/biometric-authentication/'
CHALLENGE_URL = '/v1/api/user/biometric-challenge/'


def public_key_body(public_key):
    """ The base64 body the app sends: PEM without header/footer lines. """
    pem = public_key.save_pkcs1(format='PEM')
    der = rsa.pem.load_pem(pem, 'RSA PUBLIC KEY')
    # The app sends an X.509 SubjectPublicKeyInfo key (load_pkcs1_openssl_pem).
    spki = OpenSSLPubKey()
    header = PubKeyHeader()
    header['oid'] = univ.ObjectIdentifier('1.2.840.113549.1.1.1')
    spki['header'] = header
    spki['key'] = univ.BitString.fromOctetString(der)
    return base64.b64encode(encoder.encode(spki)).decode('ascii')


def sign(private_key, message):
    return base64.b64encode(rsa.sign(message.encode('utf-8'), private_key, 'SHA-256')).decode('ascii')


class FakeUserDA():

    def __init__(self):
        self.rows = []
        self.users = {}

    def register_biometric_key(self, email, key_identifier, public_key):
        self.rows = [r for r in self.rows if r.keyIdentifier != key_identifier]
        self.rows.append(SimpleNamespace(email=email, keyIdentifier=key_identifier, publicKey=public_key))

    def get_biometric_data_by_keyidentifier(self, identifier):
        return next((r for r in self.rows if r.keyIdentifier == identifier), None)

    def get_user_by_email(self, email):
        return self.users.get(email)

    def get_user_role_by_id(self, user_id):
        return 6, 'Developer'


class BiometricAuthTests(TestCase):

    @classmethod
    def setUpClass(cls):
        super().setUpClass()
        cls.public_key, cls.private_key = rsa.newkeys(1024)
        cls.attacker_public, cls.attacker_private = rsa.newkeys(1024)

    def setUp(self):
        cache.clear()
        User = get_user_model()
        self.alice = User.objects.create_user('alice', 'alice@example.com', 'x')
        self.bob = User.objects.create_user('bob', 'bob@example.com', 'x')
        self.user_da = FakeUserDA()
        self.user_da.users = {u.email: u for u in (self.alice, self.bob)}
        for target in ('pTracker.api.user.auth_biz.UserDA', 'pTracker.api.user.views.UserDA'):
            patcher = mock.patch(target, lambda: self.user_da)
            patcher.start()
            self.addCleanup(patcher.stop)
        for target, value in (
                ('pTracker.api.user.views.AccessBL', lambda: SimpleNamespace(get_login_access=lambda uid: {})),
                ('pTracker.api.user.views.TimeSheetBL_V1',
                 lambda: SimpleNamespace(prevent_login_by_timesheet=lambda uid: False))):
            patcher = mock.patch(target, value)
            patcher.start()
            self.addCleanup(patcher.stop)
        self.client = APIClient()

    def register(self, user, body):
        client = APIClient()
        if user is not None:
            client.force_authenticate(user)
        return client.post(REGISTER_URL, body, format='json')

    def challenge(self, key_identifier='dev-1'):
        response = self.client.post(CHALLENGE_URL, {'keyIdentifier': key_identifier}, format='json')
        self.assertEqual(response.status_code, 200)
        return response.data['challenge']

    def login(self, private_key, key_identifier='dev-1', challenge=None):
        challenge = challenge or self.challenge(key_identifier)
        return self.client.post(LOGIN_URL, {'keyIdentifier': key_identifier, 'challenge': challenge,
                                            'signature': sign(private_key, challenge)}, format='json')

    def test_registration_requires_login(self):
        response = self.register(None, {'email': 'alice@example.com', 'keyIdentifier': 'dev-1',
                                        'publicKey': public_key_body(self.attacker_public)})
        self.assertEqual(response.status_code, 401)
        self.assertEqual(self.user_da.rows, [])

    def test_registration_uses_token_user_not_body_email(self):
        response = self.register(self.bob, {'email': 'alice@example.com', 'keyIdentifier': 'dev-1',
                                            'publicKey': public_key_body(self.attacker_public)})
        self.assertEqual(response.status_code, 200)
        self.assertEqual([r.email for r in self.user_da.rows], ['bob@example.com'])

        # Bob's key logs in as Bob, never as Alice.
        login = self.login(self.attacker_private)
        self.assertEqual(login.status_code, 200)
        self.assertEqual(login.data['user']['email'], 'bob@example.com')

    def test_registration_rejects_bad_input(self):
        cases = [
            {},
            {'keyIdentifier': 'dev-1'},
            {'keyIdentifier': 'dev-1', 'publicKey': 'not-a-key'},
            {'keyIdentifier': '', 'publicKey': public_key_body(self.public_key)},
            {'keyIdentifier': 'x' * 501, 'publicKey': public_key_body(self.public_key)},
            {'keyIdentifier': ['dev-1'], 'publicKey': public_key_body(self.public_key)},
        ]
        for body in cases:
            response = self.register(self.alice, body)
            self.assertEqual(response.status_code, 400, body)
        self.assertEqual(self.user_da.rows, [])

    def test_extra_fields_are_ignored_and_errors_hide_details(self):
        response = self.register(self.alice, {'keyIdentifier': 'dev-1', 'id': 99, 'email': 'bob@example.com',
                                              'publicKey': public_key_body(self.public_key)})
        self.assertEqual(response.status_code, 200)
        self.assertEqual(vars(self.user_da.rows[0]), {
            'email': 'alice@example.com', 'keyIdentifier': 'dev-1',
            'publicKey': public_key_body(self.public_key)})

        with mock.patch.object(self.user_da, 'register_biometric_key', side_effect=RuntimeError('secret db detail')), \
                mock.patch('pTracker.api.user.auth_biz.Logs') as logs:
            logs.return_value.error.return_value = 'log-1'
            response = self.register(self.alice, {'keyIdentifier': 'dev-2',
                                                  'publicKey': public_key_body(self.public_key)})
        self.assertEqual(response.status_code, 500)
        self.assertNotIn('secret db detail', response.data['error'])
        self.assertIn('log-1', response.data['error'])

    def test_login_with_registered_key(self):
        self.register(self.alice, {'keyIdentifier': 'dev-1', 'publicKey': public_key_body(self.public_key)})
        response = self.login(self.private_key)
        self.assertEqual(response.status_code, 200)
        self.assertEqual(response.data['user']['email'], 'alice@example.com')
        self.assertTrue(response.data['token'])

    def test_challenge_is_single_use_and_bound_to_device(self):
        self.register(self.alice, {'keyIdentifier': 'dev-1', 'publicKey': public_key_body(self.public_key)})
        challenge = self.challenge()
        body = {'keyIdentifier': 'dev-1', 'challenge': challenge, 'signature': sign(self.private_key, challenge)}
        self.assertEqual(self.client.post(LOGIN_URL, body, format='json').status_code, 200)
        # Replaying the exact same request fails.
        self.assertEqual(self.client.post(LOGIN_URL, body, format='json').status_code, 403)

        # A challenge issued to another device is rejected, and spent.
        other = self.challenge('dev-2')
        self.assertEqual(self.login(self.private_key, challenge=other).status_code, 403)
        # A wrong signature spends the challenge too.
        challenge = self.challenge()
        bad = {'keyIdentifier': 'dev-1', 'challenge': challenge, 'signature': sign(self.attacker_private, challenge)}
        self.assertEqual(self.client.post(LOGIN_URL, bad, format='json').status_code, 403)
        self.assertEqual(self.login(self.private_key, challenge=challenge).status_code, 403)

    def test_old_email_signature_no_longer_logs_in(self):
        self.register(self.alice, {'keyIdentifier': 'dev-1', 'publicKey': public_key_body(self.public_key)})
        response = self.client.post(LOGIN_URL, {'keyIdentifier': 'dev-1',
                                                'signature': sign(self.private_key, 'alice@example.com')},
                                    format='json')
        self.assertEqual(response.status_code, 403)

    def test_expired_challenge_is_rejected(self):
        self.register(self.alice, {'keyIdentifier': 'dev-1', 'publicKey': public_key_body(self.public_key)})
        challenge = self.challenge()
        cache.delete('biometric_challenge:{}'.format(challenge))  # what the cache timeout does
        self.assertEqual(self.login(self.private_key, challenge=challenge).status_code, 403)

    def test_challenge_does_not_reveal_registered_devices(self):
        self.register(self.alice, {'keyIdentifier': 'dev-1', 'publicKey': public_key_body(self.public_key)})
        known = self.client.post(CHALLENGE_URL, {'keyIdentifier': 'dev-1'}, format='json')
        unknown = self.client.post(CHALLENGE_URL, {'keyIdentifier': 'nope'}, format='json')
        self.assertEqual((known.status_code, set(known.data)), (unknown.status_code, set(unknown.data)))
        for body in ({}, {'keyIdentifier': 7}, {'keyIdentifier': 'x' * 501}):
            self.assertEqual(self.client.post(CHALLENGE_URL, body, format='json').status_code, 403)

    def test_login_failures_return_403_not_500(self):
        self.register(self.alice, {'keyIdentifier': 'dev-1', 'publicKey': public_key_body(self.public_key)})
        cases = [
            {},
            {'keyIdentifier': 'dev-1'},
            {'keyIdentifier': 'unknown', 'challenge': self.challenge('unknown'), 'signature': 'x'},
            {'keyIdentifier': 'dev-1', 'challenge': self.challenge()},
            {'keyIdentifier': 'dev-1', 'challenge': self.challenge(), 'signature': '%%%not-base64'},
            {'keyIdentifier': 'dev-1', 'challenge': ['x'], 'signature': 'x'},
        ]
        for body in cases:
            response = self.client.post(LOGIN_URL, body, format='json')
            self.assertEqual(response.status_code, 403, body)

        # Deactivated account: get_user_by_email only returns active users.
        del self.user_da.users['alice@example.com']
        self.assertEqual(self.login(self.private_key).status_code, 403)

    def test_login_and_challenge_are_throttled(self):
        for url in (LOGIN_URL, CHALLENGE_URL):
            statuses = [self.client.post(url, {'keyIdentifier': 'nope'}, format='json').status_code
                        for _ in range(11)]
            self.assertNotIn(429, statuses[:10], url)
            self.assertEqual(statuses[10], 429, url)
