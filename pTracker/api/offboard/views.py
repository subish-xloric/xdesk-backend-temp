from rest_framework.permissions import IsAuthenticated
from rest_framework.response import Response
from rest_framework.views import APIView
from rest_framework_simplejwt.authentication import JWTAuthentication as JSONWebTokenAuthentication
from rest_framework.parsers import MultiPartParser, FormParser, JSONParser

from pTracker.api.offboard.off_board_biz import OffBoardBL


class GenerateResigantionForm(APIView):
    authentication_classes = [JSONWebTokenAuthentication]
    permission_classes = [IsAuthenticated]

    def get(self, request):
        response = OffBoardBL().get_user_details_for_offboard_request(request.user.id)
        return Response(response)

class CreateFffboardingRequestView(APIView):
    authentication_classes = [JSONWebTokenAuthentication]
    permission_classes = [IsAuthenticated]

    def post(self, request):
        response = OffBoardBL().create_offboarding_request(request.user.id, request)
        return Response(response)


class UpdateOffBoardRequestView(APIView):
    authentication_classes = [JSONWebTokenAuthentication]
    permission_classes = [IsAuthenticated]

    def post(self, request):
        response = OffBoardBL().update_offboarding_request(request.user.id, request.data)
        return Response(response)

class GetOffboardingRequestView(APIView):
    authentication_classes = [JSONWebTokenAuthentication]
    permission_classes = [IsAuthenticated]

    def get(self, request):
        response = OffBoardBL().get_all_offboarding_requests(request.user.id,request.GET['year'],
            request.GET['organization'], request.GET['from_date'], request.GET['to_date'])
        return Response(response)

class DateAfterNWorkingDays(APIView):
    authentication_classes = [JSONWebTokenAuthentication]
    permission_classes = [IsAuthenticated]

    def get(self, request):
        response = OffBoardBL().date_after_n_working_days_from_custom_date(request.GET['from_date'],
            request.GET['no_of_days'],)
        return Response(response)

class InitiateOffboarding(APIView):
    authentication_classes = [JSONWebTokenAuthentication]
    permission_classes = [IsAuthenticated]

    def post(self, request):
        response = OffBoardBL().initiate_offboarding(request.user.id,request)
        return Response(response)

class OffBoardingExitFormView(APIView):
    authentication_classes = [JSONWebTokenAuthentication]
    permission_classes = [IsAuthenticated]

    def get(self, request):
        response = OffBoardBL().get_off_boarding_exit_form(request.user.id,request.GET['exit_form_id'])
        return Response(response)

class UpdateExitForm(APIView):
    authentication_classes = [JSONWebTokenAuthentication]
    permission_classes = [IsAuthenticated]

    def post(self, request):
        response = OffBoardBL().update_exit_form(request.user.id,request)
        return Response(response)


class UploadRelievingDocuments(APIView):
    authentication_classes = [JSONWebTokenAuthentication]
    permission_classes = [IsAuthenticated]
    parser_classes = (MultiPartParser,FormParser,JSONParser)

    def post(self, request):
        response = OffBoardBL().upload_relieving_documents(request.user.id,request)
        return Response(response)


class OffBoardingDocumentsView(APIView):
    authentication_classes = [JSONWebTokenAuthentication]
    permission_classes = [IsAuthenticated]

    def get(self, request):
        response = OffBoardBL().get_relieving_documents_by_off_boarding_id(request.user.id,request.GET['off_boarding_id'])
        return Response(response)


class DeleteOffBoardingDocuments(APIView):
    authentication_classes = [JSONWebTokenAuthentication]
    permission_classes = [IsAuthenticated]

    def get(self, request):
        response = OffBoardBL().delete_relieving_document(request.user.id,request.GET['document_id'])
        return Response(response)





class ExitInterviewFormView(APIView):
    authentication_classes = [JSONWebTokenAuthentication]
    permission_classes = [IsAuthenticated]

    def get(self, request):
        response = OffBoardBL().get_exit_interview_form_by_code(request.user.id, request.GET['exit_code'])
        return Response(response)

class UpdateExitInterviewForm(APIView):
    authentication_classes = [JSONWebTokenAuthentication]
    permission_classes = [IsAuthenticated]

    def put(self, request):
        response = OffBoardBL().update_exit_interview_form(request.user.id,request.data)
        return Response(response)

class TerminateEmployee(APIView):
    authentication_classes = [JSONWebTokenAuthentication]
    permission_classes = [IsAuthenticated]

    def put(self, request):
        response = OffBoardBL().terminate_employee(request.user.id, request.data, request.user)
        return Response(response)

    def get(self, request, emp_id):
        response = OffBoardBL().check_termination_process(emp_id)
        return Response(response)

        

class UpdatePftransferAndGrativityPaidDates(APIView):
    authentication_classes = [JSONWebTokenAuthentication]
    permission_classes = [IsAuthenticated]

    def put(self, request):
        response = OffBoardBL().update_pftransfer_grativity_dates(request.user.id,request.data)
        return Response(response)