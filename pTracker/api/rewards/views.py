from rest_framework.authentication import SessionAuthentication, BasicAuthentication, TokenAuthentication
from rest_framework.permissions import IsAuthenticated
from rest_framework.response import Response
from rest_framework.views import APIView
from rest_framework_simplejwt.authentication import JWTAuthentication as JSONWebTokenAuthentication
from rest_framework.parsers import MultiPartParser, FormParser, JSONParser
from pTracker.common.permissions import IPRestrictedPermission

from pTracker.api.rewards.rewards_biz import RewardsBL


class CreateRewardNomination(APIView):
    authentication_classes = [JSONWebTokenAuthentication]
    permission_classes = [IsAuthenticated]
    parser_classes = (MultiPartParser,FormParser,JSONParser)

    def put(self, request):
        response = RewardsBL().create_reward_nomination(request, request.user.id)
        return Response(response)

class ApproveRewardNomination(APIView):
    authentication_classes = [JSONWebTokenAuthentication]
    permission_classes = [IsAuthenticated]
    parser_classes = (MultiPartParser,FormParser,JSONParser)

    def put(self, request):
        response = RewardsBL().approve_reward_status(request)
        return Response(response)

class CancelRewardNomination(APIView):
    authentication_classes = [JSONWebTokenAuthentication]
    permission_classes = [IsAuthenticated]
    parser_classes = (MultiPartParser,FormParser,JSONParser)

    def put(self, request):
        response = RewardsBL().cancel_reward(request)
        return Response(response)

class RejectRewardNomination(APIView):
    authentication_classes = [JSONWebTokenAuthentication]
    permission_classes = [IsAuthenticated]
    parser_classes = (MultiPartParser,FormParser,JSONParser)

    def put(self, request):
        response = RewardsBL().reject_reward_status(request)
        return Response(response)

class DeleteRewardNomination(APIView):
    authentication_classes = [JSONWebTokenAuthentication]
    permission_classes = [IsAuthenticated]
    parser_classes = (MultiPartParser,FormParser,JSONParser)

    def put(self, request):
        response = RewardsBL().delete_reward(request, request.user.id)
        return Response(response)

class GetParamsViews(APIView):
    authentication_classes = [JSONWebTokenAuthentication]
    permission_classes = [IsAuthenticated]

    def get(self, request):
        response = RewardsBL().get_dropdown_prams(request)
        return Response(response)

class GetAllRewards(APIView):
    authentication_classes = [JSONWebTokenAuthentication]
    permission_classes = [IsAuthenticated]

    def get(self, request):
        response = RewardsBL().list_all_rewards(request)
        return Response(response)

class RewardCommets(APIView):
    authentication_classes = [JSONWebTokenAuthentication]
    permission_classes = [IsAuthenticated]
    parser_classes = (MultiPartParser,FormParser,JSONParser)

    def put(self, request):
        response = RewardsBL().create_comments(request)
        return Response(response)

    def get(self, request, reward_id=0):
        response = RewardsBL().get_reward_comments(request, reward_id)
        return Response(response)

class GetRewardCriteria(APIView):
    authentication_classes = [JSONWebTokenAuthentication]
    permission_classes = [IsAuthenticated]
    parser_classes = (MultiPartParser,FormParser,JSONParser)

    def get(self, request, type_id=0):
        response = RewardsBL().get_reward_criterias(request, type_id)
        return Response(response)

class ViewRewardDetails(APIView):
    authentication_classes = [JSONWebTokenAuthentication]
    permission_classes = [IsAuthenticated]
    parser_classes = (MultiPartParser,FormParser,JSONParser)

    def get(self, request, reward_id=0):
        response = RewardsBL().view_reward_details(request, reward_id)
        return Response(response)

class GetAllMyRewards(APIView):
    authentication_classes = [JSONWebTokenAuthentication]
    permission_classes = [IsAuthenticated]

    def get(self, request):
        response = RewardsBL().get_my_rewards(request)
        return Response(response)

class GetRewardReports(APIView):
    authentication_classes = [JSONWebTokenAuthentication]
    permission_classes = [IsAuthenticated]
    parser_classes = (MultiPartParser,FormParser,JSONParser)

    def put(self, request):
        response = RewardsBL().show_reward_reports(request)
        return Response(response)


class GetRewardReportDetails(APIView):
    authentication_classes = [JSONWebTokenAuthentication]
    permission_classes = [IsAuthenticated]
    parser_classes = (MultiPartParser,FormParser,JSONParser)

    def put(self, request):
        response = RewardsBL().show_reward_report_details(request)
        return Response(response)


class GetTvNotification(APIView):
    authentication_classes = []
    #permission_classes = [IPRestrictedPermission]
    permission_classes = []

    def get(self, request):
        response = RewardsBL().get_tv_notifications(request)
        return Response(response)

class CreateNotices(APIView):
    authentication_classes = [JSONWebTokenAuthentication]
    permission_classes = [IsAuthenticated]
    parser_classes = (MultiPartParser,FormParser,JSONParser)

    def put(self, request):
        response = RewardsBL().create_notices(request)
        return Response(response)


class GetNoticeList(APIView):
    authentication_classes = [JSONWebTokenAuthentication]
    permission_classes = [IsAuthenticated]

    def get(self, request):
        response = RewardsBL().manage_notices(request)
        return Response(response)

class CancelNotices(APIView):
    authentication_classes = [JSONWebTokenAuthentication]
    permission_classes = [IsAuthenticated]
    parser_classes = (MultiPartParser,FormParser,JSONParser)

    def put(self, request):
        response = RewardsBL().cancel_notices(request)
        return Response(response)


class UpdateNotices(APIView):
    authentication_classes = [JSONWebTokenAuthentication]
    permission_classes = [IsAuthenticated]
    parser_classes = (MultiPartParser,FormParser,JSONParser)

    def put(self, request):
        response = RewardsBL().update_notice(request)
        return Response(response)


class CreateEvents(APIView):
    authentication_classes = [JSONWebTokenAuthentication]
    permission_classes = [IsAuthenticated]
    parser_classes = (MultiPartParser,FormParser,JSONParser)

    def put(self, request):
        response = RewardsBL().create_events(request)
        return Response(response)

class GetEventList(APIView):
    authentication_classes = [JSONWebTokenAuthentication]
    permission_classes = [IsAuthenticated]

    def get(self, request):
        response = RewardsBL().list_events(request)
        return Response(response)
    def put(self, request):
        response = RewardsBL().list_events(request)
        return Response(response)


class DeleteEvents(APIView):
    authentication_classes = [JSONWebTokenAuthentication]
    permission_classes = [IsAuthenticated]
    parser_classes = (MultiPartParser,FormParser,JSONParser)

    def put(self, request):
        response = RewardsBL().delete_events(request)
        return Response(response)

class UpdateRewardContent(APIView):
    authentication_classes = [JSONWebTokenAuthentication]
    permission_classes = [IsAuthenticated]
    parser_classes = (MultiPartParser,FormParser,JSONParser)

    def put(self, request):
        response = RewardsBL().update_reward_content(request)
        return Response(response)