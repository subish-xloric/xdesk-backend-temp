from rest_framework.permissions import IsAuthenticated
from rest_framework.response import Response
from rest_framework.views import APIView
from rest_framework_simplejwt.authentication import JWTAuthentication as JSONWebTokenAuthentication
from rest_framework.parsers import MultiPartParser, FormParser, JSONParser

from pTracker.api.induction.induction_biz import InductionBL

class CreateInduction(APIView):
    authentication_classes = [JSONWebTokenAuthentication]
    permission_classes = [IsAuthenticated]
    parser_classes = (MultiPartParser,FormParser,JSONParser)

    def put(self, request):
        response = InductionBL().create_induction(request)
        return Response(response)

class GetInductions(APIView):
    authentication_classes = [JSONWebTokenAuthentication]
    permission_classes = [IsAuthenticated]

    def get(self, request, filter):
        response = InductionBL().get_induction(request, filter)
        return Response(response)
        

class GetInductionDetails(APIView):
    authentication_classes = [JSONWebTokenAuthentication]
    permission_classes = [IsAuthenticated]

    def get(self, request, induction_id):
        response = InductionBL().get_induction_details(request, induction_id)
        return Response(response)
        

class UpdateInductionDetails(APIView):
    authentication_classes = [JSONWebTokenAuthentication]
    permission_classes = [IsAuthenticated]
    parser_classes = (MultiPartParser,FormParser,JSONParser)

    def put(self, request):
        response = InductionBL().update_induction_details(request)
        return Response(response)

class GetProbationEmployees(APIView):
    authentication_classes = [JSONWebTokenAuthentication]
    permission_classes = [IsAuthenticated]

    def get(self, request):
        response = InductionBL().get_new_employees(request)
        return Response(response)

class DownloadInductionDetails(APIView):
    authentication_classes = [JSONWebTokenAuthentication]
    permission_classes = [IsAuthenticated]

    def get(self, request):
        response = InductionBL().print_induction_details(request)
        return response
        

class SendInductionReminder(APIView):
    authentication_classes = [JSONWebTokenAuthentication]
    permission_classes = [IsAuthenticated]

    def get(self, request, induction_id):
        response = InductionBL().send_induction_reminder(request, induction_id)
        return Response(response)