from csv import excel
from rest_framework.permissions import IsAuthenticated
from rest_framework.response import Response
from rest_framework.views import APIView
from rest_framework_simplejwt.authentication import JWTAuthentication as JSONWebTokenAuthentication
from rest_framework.parsers import MultiPartParser, FormParser, JSONParser

from pTracker.api.appraisal.appraisal_biz import AppraisalBL
from pTracker.api.appraisal.appraisal_report import AppraisalReportBL

from django.http import HttpResponse


class GetEligibleEmployess(APIView):
    authentication_classes = [JSONWebTokenAuthentication]
    permission_classes = [IsAuthenticated]

    def get(self, request, year, organization, doj):
        response = AppraisalBL().get_all_eligible_employees(request.user.id, year, organization, doj)
        return Response(response, status=response.get('status', 200))

class InitiateAppraisal(APIView):
    authentication_classes = [JSONWebTokenAuthentication]
    permission_classes = [IsAuthenticated]

    def post(self, request):
        response = AppraisalBL().initiate_appraisal(request.user.id, request.data)
        return Response(response, status=response.get('status', 200))

class AppraisalFormView(APIView):
    authentication_classes = [JSONWebTokenAuthentication]
    permission_classes = [IsAuthenticated]

    def get(self, request):
        response = AppraisalBL().get_appraisal_form_by_appraisal_token(request.user.id, request.GET['token'])
        return Response(response)


class UpdateAppraisalForm(APIView):
    authentication_classes = [JSONWebTokenAuthentication]
    permission_classes = [IsAuthenticated]

    def post(self, request):
        response = AppraisalBL().update_appraisal_form(request.user.id,request.data)
        return Response(response)


class GetAllAppraisalView(APIView):
    authentication_classes = [JSONWebTokenAuthentication]
    permission_classes = [IsAuthenticated]

    def get(self, request):
        response = AppraisalBL().get_all_appraisal(request.user.id, request.GET['year'], request.GET['organization'], request.GET['batch_id'] )
        return Response(response)

class GetAllAppraisalBatches(APIView):
    authentication_classes = [JSONWebTokenAuthentication]
    permission_classes = [IsAuthenticated]

    def get(self, request):
        response = AppraisalBL().get_appraisal_batches()
        return Response(response, status = response.get("status", 200))



class PublishAppraisalNormalizationResult(APIView):
    authentication_classes = [JSONWebTokenAuthentication]
    permission_classes = [IsAuthenticated]
    parser_classes = (MultiPartParser,FormParser,JSONParser)

    def put(self, request):
        user_id = request.user.id
        user_email = request.user.email
        response = AppraisalBL().publish_appraisal_normalization_result(user_id, user_email, request.data['year'], \
            request.data['organization'], request.data['batch_id'], request.data.get('zipFile'))
        return Response(response, status = response.get("status", 200))


class GenerateAppraisalExcelReport(APIView):
    authentication_classes = [JSONWebTokenAuthentication]
    permission_classes = [IsAuthenticated]

    def get(self, request):
        output = AppraisalReportBL().generate_appraisal_excel_report(request.user.id, request.GET['year'], request.GET['organization'], request.GET['batch_id'])
        return output



class GetAppraisalResponseReport(APIView):
    authentication_classes = [JSONWebTokenAuthentication]
    permission_classes = [IsAuthenticated]

    def get(self, request):
        response = AppraisalReportBL().get_appraisal_response_report(request.user.id,
                                                                     request.GET['year'], request.GET['batch_id'], request.GET['response_of'])
        return Response(response)


class UploadAppraisalDocument(APIView):
    authentication_classes = [JSONWebTokenAuthentication]
    permission_classes = [IsAuthenticated]
    parser_classes = (MultiPartParser,FormParser,JSONParser)

    def post(self, request):
        response = AppraisalReportBL().upload_appraisal_document(request.user.id,request)
        return Response(response)

class DownloadPerformanceAssesmentLetter(APIView):
    authentication_classes = [JSONWebTokenAuthentication]
    permission_classes = [IsAuthenticated]

    def get(self, request):
        response = AppraisalBL().download_performance_assesment_letter(request, request.GET['filename'])
        return response

class PublishPerformanceAssesmentLetter(APIView):
    authentication_classes = [JSONWebTokenAuthentication]
    permission_classes = [IsAuthenticated]

    def get(self, request):
        response = AppraisalBL().publish_performance_assesment_letter(request, request.GET['filename'], request.GET['token'])
        return Response(response)
