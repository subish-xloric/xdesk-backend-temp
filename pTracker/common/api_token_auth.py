from django.contrib.auth.models import User
from rest_framework.authentication import BaseAuthentication, get_authorization_header
from rest_framework.exceptions import AuthenticationFailed

from pTracker.dataaccess.ptracker_access.user_da import UserDA


class ApiTokenAuthentication(BaseAuthentication):
    """
    Custom DRF authentication backend for API-token-based external integrations.

    External applications (e.g. ClickUp, Linear, Jira-style tools) authenticate
    by including the user's API token in the standard Authorization header:

        Authorization: Token <api_token>

    How it works:
      1. The client sends the header with the scheme 'Token' followed by the
         token value that was previously generated via the token-generation endpoint.
      2. This class extracts the raw token and delegates to UserDA to look up
         the corresponding user_id in the user_profile.api_token column.
      3. The active Django User for that user_id is loaded and returned as
         the authenticated principal for the request.

    If no Authorization header with scheme 'Token' is present the authenticator
    returns None, allowing other authenticators (e.g. JWT) to try next.
    Any header present but malformed, or with an unknown token, raises
    AuthenticationFailed (HTTP 401).
    """

    keyword = b'token'

    def authenticate(self, request):
        """
        Parses and validates the 'Authorization: Token <value>' header.

        Returns (user, token) on success, None if the header is absent or
        uses a different scheme, or raises AuthenticationFailed for malformed
        or unrecognised tokens.

        Args:
            request: The incoming DRF Request object.

        Returns:
            tuple(User, str) | None
        """
        auth = get_authorization_header(request).split()

        if not auth or auth[0].lower() != self.keyword:
            # No matching Authorization header — let other authenticators try.
            return None

        if len(auth) != 2:
            raise AuthenticationFailed(
                'Invalid token header. The token value must not contain spaces.'
            )

        try:
            token = auth[1].decode('utf-8')
        except UnicodeDecodeError:
            raise AuthenticationFailed(
                'Invalid token header. Token string contains non-ASCII characters.'
            )

        return self._authenticate_credentials(token)

    def _authenticate_credentials(self, token):
        """
        Resolves the raw token string to an active Django User.

        Queries user_profile.api_token via UserDA. Returns (user, token) on
        success, or raises AuthenticationFailed if the token is unknown or
        the associated user is inactive/deleted.

        Args:
            token (str): The raw token value extracted from the header.

        Returns:
            tuple(User, str)

        Raises:
            AuthenticationFailed: If the token is invalid or the user is inactive.
        """
        user_id = UserDA().get_user_id_by_api_token(token)
        if user_id is None:
            raise AuthenticationFailed(
                'Invalid API token. Generate a new one from the token endpoint.'
            )

        try:
            user = User.objects.get(id=user_id, is_active=True)
        except User.DoesNotExist:
            raise AuthenticationFailed(
                'The user associated with this token is inactive or has been removed.'
            )

        return (user, token)

    def authenticate_header(self, request):
        """
        Returns the value for the WWW-Authenticate header on 401 responses.
        This tells the client which authentication scheme is expected.
        """
        return 'Token realm="DM Desk API"'
