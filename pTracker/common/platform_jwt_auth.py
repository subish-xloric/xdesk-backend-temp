from rest_framework_simplejwt.authentication import JWTAuthentication
from rest_framework.exceptions import AuthenticationFailed
from rest_framework_simplejwt.exceptions import InvalidToken
from rest_framework_simplejwt.settings import api_settings
from rest_framework_simplejwt.utils import get_md5_hash_password

from pTracker.dataaccess.platform_access.platform_user_da import PlatformUserDA


class PlatformJWTAuthentication(JWTAuthentication):
    """
    JWTAuthentication resolves the token's user id against
    django.contrib.auth's AUTH_USER_MODEL (auth_user, the employee
    identity) by default. Platform users are a separate identity
    (PlatformUser), so this subclass resolves against that instead.
    Token signing/verification is unchanged - same SIMPLE_JWT settings
    as the rest of the app.
    """

    def get_user(self, validated_token):
        user_id = validated_token.get('user_id')
        if user_id is None:
            raise InvalidToken('Token contained no recognizable user identification')

        user = PlatformUserDA().get_by_id(user_id)
        if user is None or not user.is_active:
            raise InvalidToken('Platform user not found or inactive')

        # same password-change revocation as JWTAuthentication.get_user
        if api_settings.CHECK_REVOKE_TOKEN and \
                validated_token.get(api_settings.REVOKE_TOKEN_CLAIM) != get_md5_hash_password(user.password):
            raise AuthenticationFailed("The user's password has been changed.", code="password_changed")

        return user
