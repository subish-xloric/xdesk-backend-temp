
from rest_framework_simplejwt.authentication import JWTAuthentication as JSONWebTokenAuthentication
from rest_framework.permissions import IsAuthenticated
from rest_framework.response import Response
from rest_framework.views import APIView

from pTracker.api.app.app_biz import AppBL

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
        result = AppBL().get_version_status(request.META.get("HTTP_APP_VERSION", ""),
                                            request.META.get("HTTP_DEVICE_TYPE", ""))
        return Response(result, status =200)

