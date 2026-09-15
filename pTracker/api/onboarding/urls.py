from django.urls import path
from pTracker.api.onboarding.views import CreateOnboardingCandidate
from pTracker.api.onboarding.views import GetAllOnboardingCandidates
from pTracker.api.onboarding.views import EditOnboardingCandidateDetails
from pTracker.api.onboarding.views import OnboardingCandidateDetialsFillingLinkValidation
from pTracker.api.onboarding.views import  GetDistrictsAndStatesForOnboardingProcess
from pTracker.api.onboarding.views import GetKYCDocumentTypes
from pTracker.api.onboarding.views import FillOnboardingCandidateDetails
from pTracker.api.onboarding.views import GetOnBoardingCandidateDetails
from pTracker.api.onboarding.views import UpdateOnboardingCandidateStatus
from pTracker.api.onboarding.views import LoadOnboardingCandidateAsEmployee
from pTracker.api.onboarding.views import GetOnboardingDropdowns

urlpatterns = [
     path('create-onboarding-candidate/', CreateOnboardingCandidate.as_view(), name='create_onboarding_candidate'),
     path('get-all-onbaording-candidates/', GetAllOnboardingCandidates.as_view(), name='get_all_onbaording_candidates'),
     path('update-onboarding-candidate/', EditOnboardingCandidateDetails.as_view(), name='update_onboarding_candidate'),
     path('onboarding-link-validation/', OnboardingCandidateDetialsFillingLinkValidation.as_view(), name='onboarding_link_validation'),
     path('get-districts-and-states-for-dropdown/', GetDistrictsAndStatesForOnboardingProcess.as_view(), name='get_districts_and-states_for_dropdown'),
     path('get-kyc-document-types/', GetKYCDocumentTypes.as_view(), name='get_kyc_document_types'),
     path('fill-onboarding-candidate-details/', FillOnboardingCandidateDetails.as_view(), name='fill_onboarding_candidate_details'),
     path('get-onbaording-candidate-details/', GetOnBoardingCandidateDetails.as_view(), name='get_onbaording_candidate_details'),
     path('apply-action-on-onbaording-candidate-details/', UpdateOnboardingCandidateStatus.as_view(), name='apply_action_on_onbaording_candidate_details'),
     path('load-onboarding-candidate-as-employee/', LoadOnboardingCandidateAsEmployee.as_view(), name='load_onboarding_candidate_as_employee'),
     path('get-onboarding-dropdown/', GetOnboardingDropdowns.as_view(), name='get_onboarding_dropdown'),

]

