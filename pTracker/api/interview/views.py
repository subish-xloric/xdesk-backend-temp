from rest_framework.permissions import IsAuthenticated
from rest_framework.response import Response
from rest_framework.views import APIView
from rest_framework_simplejwt.authentication import JWTAuthentication as JSONWebTokenAuthentication
from rest_framework.parsers import MultiPartParser, FormParser, JSONParser

from pTracker.api.interview.career_opening_biz import CareerOpeningBL
from pTracker.api.interview.candidate_biz import CandidateBL
from pTracker.api.interview.interview_biz import InterviewBL
from pTracker.api.interview.interview_score_card_biz import InterviewScoreCardBL
from pTracker.api.interview.notification_biz import NotificationBL



class CreateCareerOpeningView(APIView):
    authentication_classes = [JSONWebTokenAuthentication]
    permission_classes = [IsAuthenticated]

    def post(self, request):
        response = CareerOpeningBL().create_or_update_career_opening(request.user, request.data)
        return Response(response)


class UpdateCareerOpeningView(APIView):
    authentication_classes = [JSONWebTokenAuthentication]
    permission_classes = [IsAuthenticated]

    def post(self, request):
        response = CareerOpeningBL().create_or_update_career_opening(request.user, request.data)
        return Response(response)

class GetCareerOpeningView(APIView):
    authentication_classes = [JSONWebTokenAuthentication]
    permission_classes = [IsAuthenticated]

    def get(self, request, year, status):
        response = CareerOpeningBL().get_career_opening_all(request, year, status)
        return Response(response)

class DeleteCareerOpeningView(APIView):
    authentication_classes = [JSONWebTokenAuthentication]
    permission_classes = [IsAuthenticated]

    def put(self, request):
        response = CareerOpeningBL().delete_career_opening(request.user, request.data)
        return Response(response)


class CloseCareerOpeningView(APIView):
    authentication_classes = [JSONWebTokenAuthentication]
    permission_classes = [IsAuthenticated]

    def put(self, request):
        response = CareerOpeningBL().close_career_opening(request.data, request.user)
        return Response(response)

class GetSkillsView(APIView):
    authentication_classes = [JSONWebTokenAuthentication]
    permission_classes = [IsAuthenticated]

    def get(self, request):
        response = CareerOpeningBL().get_soft_and_technical_skills(request)
        return Response(response)

class GetCareerOpenedView(APIView):
    authentication_classes = [JSONWebTokenAuthentication]
    permission_classes = [IsAuthenticated]

    def get(self, request):
        response = CareerOpeningBL().get_career_opened(request)
        return Response(response)




class CreateCandidateView(APIView):
    authentication_classes = [JSONWebTokenAuthentication]
    permission_classes = [IsAuthenticated]
    parser_classes = (MultiPartParser,FormParser,JSONParser)

    def post(self, request):
        response = CandidateBL().create_or_update_candidate(request.user, request.data)
        return Response(response)

class UpdateCandidateView(APIView):
    authentication_classes = [JSONWebTokenAuthentication]
    permission_classes = [IsAuthenticated]

    def post(self, request):
        response = CandidateBL().create_or_update_candidate(request.user, request.data)
        return Response(response)

class DeleteCandidateView(APIView):
    authentication_classes = [JSONWebTokenAuthentication]
    permission_classes = [IsAuthenticated]

    def put(self, request):
        response = CandidateBL().delete_candidate(request.user, request.data)
        return Response(response)


class CreateInterviewView(APIView):
    authentication_classes = [JSONWebTokenAuthentication]
    permission_classes = [IsAuthenticated]

    def post(self, request):
        response = InterviewBL().create_interview(request.user, request.data)
        return Response(response)

class UpdateInterviewView(APIView):
    authentication_classes = [JSONWebTokenAuthentication]
    permission_classes = [IsAuthenticated]

    def post(self, request):
        response = InterviewBL().update_interview(request.user, request.data)
        return Response(response)

class GetInterviewView(APIView):
    authentication_classes = [JSONWebTokenAuthentication]
    permission_classes = [IsAuthenticated]

    def get(self, request, year, status):
        response = InterviewBL().get_all_interviews(request, request.user, year, status)
        return Response(response)

class CancelInterviewView(APIView):
    authentication_classes = [JSONWebTokenAuthentication]
    permission_classes = [IsAuthenticated]

    def put(self, request):
        response = InterviewBL().cancel_interview(request.user, request.data)
        return Response(response)





# class GetInterviewScorecard(APIView):
#     authentication_classes = [JSONWebTokenAuthentication]
#     permission_classes = [IsAuthenticated]

#     def get(self, request, interviewID):
#         response = InterviewBL().get_interview_score_card_by_id(interviewID)
#         return Response(response)

# class UpdateInterviewScoreCard(APIView):
#     authentication_classes = [JSONWebTokenAuthentication]
#     permission_classes = [IsAuthenticated]

#     def post(self, request):
#         response = InterviewBL().update_interview_score_card(request.user, request.data)
#         return Response(response)

#TODO - confimation mail
# class CreateInterviewConfirmationView(APIView):
#     authentication_classes = [JSONWebTokenAuthentication]
#     permission_classes = [IsAuthenticated]

#     def get(self, request, interviewID):
#         response = InterviewBL().create_interview_confirmation_mail(request.user, interviewID)
#         return Response(response)


class RescheduleInterviewView(APIView):
    authentication_classes = [JSONWebTokenAuthentication]
    permission_classes = [IsAuthenticated]

    def post(self, request):
        response = InterviewBL().reschedule_interview(request.user, request.data)
        return Response(response)

# class SearchCandidateView(APIView):
#     authentication_classes = [JSONWebTokenAuthentication]
#     permission_classes = [IsAuthenticated]

#     def get(self, request, search_parameter):
#         response = CandidateBL().search_candidate_by_name_email_phone(request, search_parameter)
#         return Response(response)

class CheckInterviewStatus(APIView):
    authentication_classes = [JSONWebTokenAuthentication]
    permission_classes = [IsAuthenticated]

    def get(self, request, candidate_id):
        response = InterviewBL().check_interview_status(request, candidate_id)
        return Response(response)

class GetAllCandidateView(APIView):
    authentication_classes = [JSONWebTokenAuthentication]
    permission_classes = [IsAuthenticated]

    def get(self, request, position=None, status=None):
        response = CandidateBL().get_all_candidates(request.user, position, status)
        return Response(response)


class CandidateOfferReleasedView(APIView):
    authentication_classes = [JSONWebTokenAuthentication]
    permission_classes = [IsAuthenticated]

    def put(self, request):
        response = CandidateBL().candidate_offer_released(request.user, request.data)
        return Response(response)


class CandidateStatusRejectedView(APIView):
    authentication_classes = [JSONWebTokenAuthentication]
    permission_classes = [IsAuthenticated]

    def put(self, request):
        response = CandidateBL().reject_candidate(request.user, request.data)
        return Response(response)


class GenerateInterviewScorecard(APIView):
    authentication_classes = [JSONWebTokenAuthentication]
    permission_classes = [IsAuthenticated]

    def get(self, request, interview_id):
        response = InterviewScoreCardBL().generate_scorecard_by_interview(request.user,interview_id)
        return Response(response)

class CreateInterviewScoreCard(APIView):
    authentication_classes = [JSONWebTokenAuthentication]
    permission_classes = [IsAuthenticated]

    def post(self, request):
        response = InterviewScoreCardBL().create_interview_score_card(request.user, request.data)
        return Response(response)

class GetCandidateInterviewScorecard(APIView):
    authentication_classes = [JSONWebTokenAuthentication]
    permission_classes = [IsAuthenticated]

    def get(self, request, candidate_id):
        response = InterviewScoreCardBL().get_interview_scorecard_by_candidate(request.user, candidate_id)
        return Response(response)

class GetInterviewScorecard(APIView):
    authentication_classes = [JSONWebTokenAuthentication]
    permission_classes = [IsAuthenticated]

    def get(self, request, interview_id):
        response = InterviewScoreCardBL().get_interview_scorecard_by_interview(request.user, interview_id)
        return Response(response)

class CandidateActionValidation(APIView):
    authentication_classes = [JSONWebTokenAuthentication]
    permission_classes = [IsAuthenticated]

    def get(self, request, candidate_id, action):
        response = CandidateBL().candidate_action_validation(request, candidate_id, action)
        return Response(response)

class InterviewActionValidation(APIView):
    authentication_classes = [JSONWebTokenAuthentication]
    permission_classes = [IsAuthenticated]

    def get(self, request, interview_id, action):
        response = InterviewBL().interview_action_validation(request, interview_id, action)
        return Response(response)

class SendMail(APIView):
    authentication_classes = [JSONWebTokenAuthentication]
    permission_classes = [IsAuthenticated]

    def put(self, request):
        response = NotificationBL().send_mail(request.user, request.data)
        return Response(response)

class UpdateInterviewCommentView(APIView):
    authentication_classes = [JSONWebTokenAuthentication]
    permission_classes = [IsAuthenticated]

    def post(self, request):
        response = InterviewBL().update_interview_comment(request.user, request.data)
        return Response(response)

class GetInterviewCommentsView(APIView):
    authentication_classes = [JSONWebTokenAuthentication]
    permission_classes = [IsAuthenticated]

    def get(self, request, interview_id):
        response = InterviewBL().get_all_interview_comments(request.user,interview_id)
        return Response(response)



class GetCandidateInformationSheetView(APIView):
    '''No need for authentication; used to get candidate information sheet.'''
    authentication_classes = []
    permission_classes = []

    def get(self, request, token):
        response = CandidateBL().get_candidate_information_sheet(token)
        return Response(response)


class UpdateCandidateInformationSheet(APIView):
    authentication_classes = []
    permission_classes = []
    parser_classes = (MultiPartParser,FormParser,JSONParser)

    def put(self, request):
        response = CandidateBL().update_candidate_information_sheet(request)
        return Response(response)

class GetCandidateInformationSheetView_V1(APIView):
    authentication_classes = []
    permission_classes = []
    '''No need for authentication; used to get candidate information sheet.'''

    def get(self, request, token):
        response = CandidateBL().get_candidate_information_sheet(token, 0)
        return Response(response)



class GetCandidateFile(APIView):
    authentication_classes = []
    permission_classes = []
    '''No need for authentication; used to get candidate information sheet.'''

    def get(self, request, candidate_id):
        response = CandidateBL().get_candidate_file(request, candidate_id)
        return response



















