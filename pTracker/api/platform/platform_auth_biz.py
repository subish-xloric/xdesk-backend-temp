from rest_framework_simplejwt.tokens import RefreshToken

from pTracker.dataaccess.platform_access.platform_user_da import PlatformUserDA
from pTracker.common.logs import Logs
from pTracker.common.exception_handler import ExceptionHandler


class PlatformAuthBL():

    def __init__(self):
        self.__log = Logs()
        self.__exception = ExceptionHandler()

    def login(self, email, password):
        if not email or not password:
            return {'error': 'Email and password are required', 'status': 400}

        user = PlatformUserDA().get_by_email(email)
        if not user or not user.check_password(password):
            return {'error': 'Credentials are not valid!', 'status': 403}

        token = str(RefreshToken.for_user(user).access_token)
        return {
            'token': token,
            'user': {
                'id': user.id,
                'email': user.email,
                'full_name': user.full_name,
            },
            'status': 200,
        }
