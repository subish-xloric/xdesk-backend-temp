from rest_framework.authentication import SessionAuthentication, BasicAuthentication, TokenAuthentication
from rest_framework.permissions import IsAuthenticated
from rest_framework.response import Response
from rest_framework.views import APIView
from rest_framework_simplejwt.authentication import JWTAuthentication as JSONWebTokenAuthentication
from rest_framework.parsers import MultiPartParser, FormParser, JSONParser

from pTracker.api.resource.resources_biz import ResourceBL


class GetProjectAccountMappings(APIView):
    authentication_classes = [JSONWebTokenAuthentication]
    permission_classes = [IsAuthenticated]
    def get(self,request,year_and_month,map_status,billable,account):
        result = ResourceBL().get_all_project_accnt_emp_mapping(request.user.id,year_and_month,map_status,billable,account)
        return Response(result)

class GetAllProjectAccounts(APIView):
    authentication_classes = [JSONWebTokenAuthentication]
    permission_classes = [IsAuthenticated]
    def get(self, request):
        result = ResourceBL().get_all_project_accounts()
        return Response(result)