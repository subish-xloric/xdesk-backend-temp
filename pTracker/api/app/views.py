
from rest_framework_simplejwt.authentication import JWTAuthentication as JSONWebTokenAuthentication
from rest_framework.permissions import IsAuthenticated
from rest_framework.response import Response
from rest_framework.views import APIView

from rest_framework.status import (
    HTTP_204_NO_CONTENT,
    HTTP_206_PARTIAL_CONTENT,
    HTTP_400_BAD_REQUEST,
    HTTP_503_SERVICE_UNAVAILABLE,
)

class GetVersionStatus(APIView):
    authentication_classes = []
    permission_classes = []

    def get(self, request):
        result = {"isUpdateAvailable" : False,
                "isForceUpdate" : False,
        }
        user_app_version = request.META.get("HTTP_APP_VERSION", "")
        user_device_type = request.META.get("HTTP_DEVICE_TYPE", "")

        if user_device_type.upper() == "ANDROID":
            latest_version = "0.0.3"
            release_note = "android release note"
        else:
            latest_version = "0.0.2"
            release_note = "ios release note"

        

        result['releaseNote'] = release_note
        result['newVersion'] = latest_version
        result['isForceUpdate'] = False
        return Response(result, status =200)

