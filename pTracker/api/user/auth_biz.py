import binascii
import rsa
import base64

from pTracker.dataaccess.ptracker_access.user_da import UserDA

from pTracker.common.utility import Utility
from pTracker.common.exception_handler import ExceptionHandler
from pTracker.common.logs import Logs

from django.conf import settings

# auth_biometric column sizes
MAX_KEY_IDENTIFIER_LENGTH = 500
MAX_PUBLIC_KEY_LENGTH = 2500


class BiometricAuthBL():
    def __init__(self):
        self.__exception = ExceptionHandler()
        self.__utility = Utility()
        self.__logs = Logs()

    def load_public_key(self, public_key):
        """ Parses the base64 key body the app sends (no PEM header/footer);
        None when it is not a valid RSA public key. """
        pem_prefix = '-----BEGIN PUBLIC KEY-----\n'
        pem_suffix = '\n-----END PUBLIC KEY-----'
        key = '{}{}{}'.format(pem_prefix, public_key, pem_suffix)
        try:
            return rsa.PublicKey.load_pkcs1_openssl_pem(key.encode('utf-8'))
        except Exception:
            return None

    def verify_biometric_signature(self, public_key, signature, message):
        key = self.load_public_key(public_key)
        if key is None or not isinstance(signature, str) or not signature:
            return False
        try:
            signature_bytes = base64.b64decode(signature, validate=True)
            rsa.verify(message.encode('utf-8'), signature_bytes, key)
        except (rsa.VerificationError, binascii.Error, ValueError):
            return False
        return True

    def register_bio_metric_authrntication(self, user, data):
        """ Registers a device key for the logged-in user. The account always
        comes from the token, never from the request body. """
        try:
            key_identifier = data.get('keyIdentifier')
            public_key = data.get('publicKey')
            if not isinstance(key_identifier, str) or not isinstance(public_key, str):
                return {'status': 400, 'error': 'keyIdentifier and publicKey are required.'}
            key_identifier = key_identifier.strip()
            public_key = public_key.strip()
            if not key_identifier or len(key_identifier) > MAX_KEY_IDENTIFIER_LENGTH:
                return {'status': 400, 'error': 'Invalid keyIdentifier.'}
            if len(public_key) > MAX_PUBLIC_KEY_LENGTH or self.load_public_key(public_key) is None:
                return {'status': 400, 'error': 'Invalid publicKey.'}

            UserDA().register_biometric_key(user.email, key_identifier, public_key)
            return {'status': 200, 'message': "Successfully registered for biometric authentication"}
        except Exception:
            log_id = self.__logs.error(self.__exception.get_exception())
            return {'status': 500, 'error': settings.ERROR_MSG['application_error'].format(
                'an unexpected error occurred', log_id)}
