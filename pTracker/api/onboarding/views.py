from rest_framework.permissions import IsAuthenticated
from rest_framework.response import Response
from rest_framework.views import APIView
from rest_framework_simplejwt.authentication import JWTAuthentication as JSONWebTokenAuthentication
from rest_framework.parsers import MultiPartParser, FormParser, JSONParser

from pTracker.api.onboarding.onboarding_biz import OnboardingBL



class CreateOnboardingCandidate(APIView):
    authentication_classes = [JSONWebTokenAuthentication]
    permission_classes = [IsAuthenticated]
    parser_classes = (MultiPartParser,FormParser,JSONParser)

    def post(self, request):
        response = OnboardingBL().create_onboarding_candidate(request.user.id, request)
        return Response(response)

class GetAllOnboardingCandidates(APIView):
    authentication_classes = [JSONWebTokenAuthentication]
    permission_classes = [IsAuthenticated]

    def get(self, request):
        response = OnboardingBL().get_all_onboarding_candidates(request.user.id)
        return Response(response)

class EditOnboardingCandidateDetails(APIView):
    authentication_classes = [JSONWebTokenAuthentication]
    permission_classes = [IsAuthenticated]
    parser_classes = (MultiPartParser,FormParser,JSONParser)

    def post(self, request):
        response = OnboardingBL().edit_onboarding_candidate_details(request.user.id, request)
        return Response(response)

class OnboardingCandidateDetialsFillingLinkValidation(APIView):
    authentication_classes = []
    permission_classes = []

    def get(self, request):
        response = OnboardingBL().onboarding_link_validation(request.GET['onboarding_code'])
        return Response(response)


#for onboarding process only
class GetDistrictsAndStatesForOnboardingProcess(APIView):
    authentication_classes = []
    permission_classes = []


    def get(self, request):
        result = OnboardingBL().get_dropdowns_for_onboarding()
        return Response(result, status = result.get("status", 200))

class GetKYCDocumentTypes(APIView):
    authentication_classes = []
    permission_classes = []
    def get(self, request):
        result = OnboardingBL().get_KYC_document_types()
        return Response(result, status = result.get("status", 200))

class FillOnboardingCandidateDetails(APIView):
    authentication_classes = []
    permission_classes = []
    parser_classes = (MultiPartParser,FormParser,JSONParser)

    def post(self, request):
        response = OnboardingBL().fill_onboarding_candidate_details(request)
        return Response(response)




class GetOnBoardingCandidateDetails(APIView):
    authentication_classes = [JSONWebTokenAuthentication]
    permission_classes = [IsAuthenticated]

    def get(self, request):
        response = OnboardingBL().get_details_filled_by_onboarding_candidate(request.user.id, request.GET['onboarding_token'])
        return Response(response)



class UpdateOnboardingCandidateStatus(APIView):
    authentication_classes = [JSONWebTokenAuthentication]
    permission_classes = [IsAuthenticated]


    def post(self, request):
        response = OnboardingBL().update_onboarding_candidate_status(request.user.id, request)
        return Response(response)


class LoadOnboardingCandidateAsEmployee(APIView):
    authentication_classes = [JSONWebTokenAuthentication]
    permission_classes = [IsAuthenticated]

    def post(self, request):
        response = OnboardingBL().load_onboarding_candidate_as_user(request.user.id, request)
        return Response(response)


class GetOnboardingDropdowns(APIView):
    authentication_classes = [JSONWebTokenAuthentication]
    permission_classes = [IsAuthenticated]

    def get(self, request):
        response = OnboardingBL().get_onboard_user_dropdowns()
        return Response(response)

