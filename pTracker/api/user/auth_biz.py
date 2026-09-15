import rsa
import base64

from pTracker.dataaccess.ptracker_access.user_da import UserDA

from pTracker.common.utility import Utility
from pTracker.common.exception_handler import ExceptionHandler
from pTracker.common.logs import Logs

from django.conf import settings

class BiometricAuthBL():
    def __init__(self):
        self.__exception = ExceptionHandler()
        self.__utility = Utility()
        self.__logs = Logs()

    def verify_biometric_signature(self, public_key, signature, message):
        pem_prefix = '-----BEGIN PUBLIC KEY-----\n'
        pem_suffix = '\n-----END PUBLIC KEY-----'
        key = '{}{}{}'.format(pem_prefix, public_key, pem_suffix)

        public_key = rsa.PublicKey.load_pkcs1_openssl_pem(key)

        signature_bytes = base64.b64decode(signature)

        try:
            result = rsa.verify(
                    message.encode('utf-8'), signature_bytes, public_key)

            is_verified = True

            if result is None:
                    is_verified = False

        except rsa.VerificationError:
                is_verified = False

        return is_verified
    
    def register_bio_metric_authrntication(self, data):
        try:
            response = {}
            email = data.get('email',0)
            if email:
                user = UserDA().get_user_by_email(email)
                if not user:
                    response['status'] = 403
                    response['error'] = settings.ERROR_MSG['access_denied']
                    return response
            device_identifier = data.get('keyIdentifier', 0)
            if email and device_identifier:
                obj = UserDA().create_or_update_auth_biometric_authentication(data)
                if obj:
                    response['status'] = 200
                    response['message'] = "Successfully registered for biometric authentication"
                else:
                    response['status'] = 403
                    response['error'] = "An error occurred. Please try again."
            else:
                response['status'] = 403
                response['error'] = "An error occurred. Please try again."
            return response
        except Exception as err:
            response = {}
            response['status'] = 403
            response["error"] = settings.ERROR_MSG['application_error']\
                .format(err, self.__logs.error(self.__exception.get_exception()))
            return response
