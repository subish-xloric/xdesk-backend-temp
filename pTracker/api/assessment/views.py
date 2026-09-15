from rest_framework.permissions import IsAuthenticated
from rest_framework.response import Response
from rest_framework.views import APIView
from rest_framework_simplejwt.authentication import JWTAuthentication as JSONWebTokenAuthentication
from rest_framework.parsers import MultiPartParser, FormParser, JSONParser

from pTracker.api.assessment.assessment_biz import AssessmentBL

class CreateAssessment(APIView):
    authentication_classes = [JSONWebTokenAuthentication]
    permission_classes = [IsAuthenticated]
    parser_classes = (MultiPartParser,FormParser,JSONParser)

    def put(self, request):
        response = AssessmentBL().create_assessment_v1(request)
        return Response(response)

class ManageAssessee(APIView):
    authentication_classes = [JSONWebTokenAuthentication]
    permission_classes = [IsAuthenticated]
    parser_classes = (MultiPartParser,FormParser,JSONParser)

    def get(self, request, status=0):
        response = AssessmentBL().manage_assessee(request, status)
        return Response(response)
    
    def put(self, request):
        response = AssessmentBL().update_assessment(request)
        return Response(response)

class GetDropdowns(APIView):
    authentication_classes = [JSONWebTokenAuthentication]
    permission_classes = [IsAuthenticated]

    def get(self, request):
        response = AssessmentBL().get_dropdown_params(request)
        return Response(response)
        
class ManageAssessment(APIView):
    authentication_classes = [JSONWebTokenAuthentication]
    permission_classes = [IsAuthenticated]

    def get(self, request, status=0, year=0):
        response = AssessmentBL().my_assessment(request, status, year)
        return Response(response)
        

class createAssessmentReport(APIView):
    authentication_classes = [JSONWebTokenAuthentication]
    permission_classes = [IsAuthenticated]
    parser_classes = (MultiPartParser,FormParser,JSONParser)
    
    def put(self, request):
        response = AssessmentBL().create_assessment_report(request)
        return Response(response)

class CancelAssessment(APIView):
    authentication_classes = [JSONWebTokenAuthentication]
    permission_classes = [IsAuthenticated]
    parser_classes = (MultiPartParser,FormParser,JSONParser)
    
    def put(self, request):
        response = AssessmentBL().cancel_assessment(request)
        return Response(response)

class RescheduleAssessment(APIView):
    authentication_classes = [JSONWebTokenAuthentication]
    permission_classes = [IsAuthenticated]
    parser_classes = (MultiPartParser,FormParser,JSONParser)
    
    def put(self, request):
        response = AssessmentBL().reschedule_assessment(request)
        return Response(response)


class ViewAssessmentReport(APIView):
    authentication_classes = [JSONWebTokenAuthentication]
    permission_classes = [IsAuthenticated]

    def get(self, request, assessment_id=0):
        response = AssessmentBL().view_assessment_report(request, assessment_id)
        return Response(response)

class ViewAssesseeReport(APIView):
    authentication_classes = [JSONWebTokenAuthentication]
    permission_classes = [IsAuthenticated]

    def get(self, request, assessee_id=0):
        response = AssessmentBL().view_assessee_report(request, assessee_id)
        return Response(response)
            


class DownloadAssessmentReport(APIView):
    authentication_classes = [JSONWebTokenAuthentication]
    permission_classes = [IsAuthenticated]

    def get(self, request):
        response = AssessmentBL().download_report(request)
        return response

class getAssessors(APIView):
    authentication_classes = [JSONWebTokenAuthentication]
    permission_classes = [IsAuthenticated]

    def get(self, request, total_assessments, emp_id):
        response = AssessmentBL().get_assessment_lead_ids(request, total_assessments, emp_id)
        return Response(response)
            
        