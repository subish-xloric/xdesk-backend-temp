from django.urls import path
from pTracker.api.interview.views import CreateCareerOpeningView
#from pTracker.api.interview.views import CreateInterviewConfirmationView
from pTracker.api.interview.views import DeleteCareerOpeningView
# from pTracker.api.interview.views import GetInterviewScorecard
# from pTracker.api.interview.views import GetInterviewScorecard
# from pTracker.api.interview.views import GetInterviewScorecard
# from pTracker.api.interview.views import GetInterviewScorecard
from pTracker.api.interview.views import GetSkillsView
from pTracker.api.interview.views import GetCareerOpenedView
#from pTracker.api.interview.views import UpdateInterviewScoreCard
from pTracker.api.interview.views import RescheduleInterviewView
from pTracker.api.interview.views import GetCareerOpeningView
from pTracker.api.interview.views import UpdateCareerOpeningView
from pTracker.api.interview.views import CreateInterviewView
from pTracker.api.interview.views import UpdateInterviewView
from pTracker.api.interview.views import GetInterviewView
from pTracker.api.interview.views import CancelInterviewView
from pTracker.api.interview.views import CreateCandidateView
from pTracker.api.interview.views import UpdateCandidateView
from pTracker.api.interview.views import DeleteCandidateView
from pTracker.api.interview.views import CheckInterviewStatus

from pTracker.api.interview.views import CloseCareerOpeningView
from pTracker.api.interview.views import GetAllCandidateView

from pTracker.api.interview.views import CandidateOfferReleasedView
from pTracker.api.interview.views import CandidateStatusRejectedView
from pTracker.api.interview.views import GenerateInterviewScorecard
from pTracker.api.interview.views import CandidateActionValidation
from pTracker.api.interview.views import InterviewActionValidation

# from pTracker.api.interview.views import GetCandidateView, SearchCandidateView,

# from pTracker.api.interview.views import GetCandidateView

from pTracker.api.interview.views import CreateInterviewScoreCard
from pTracker.api.interview.views import GetCandidateInterviewScorecard
from pTracker.api.interview.views import GetInterviewScorecard

from pTracker.api.interview.views import GetCandidateFile

from pTracker.api.interview.views import SendMail
from pTracker.api.interview.views import UpdateInterviewCommentView
from pTracker.api.interview.views import GetInterviewCommentsView
from pTracker.api.interview.views import GetCandidateInformationSheetView, GetCandidateInformationSheetView_V1
from pTracker.api.interview.views import UpdateCandidateInformationSheet




urlpatterns = [
    path('create-opening/', CreateCareerOpeningView.as_view(), name='create_career_opening'),
    path('update-opening/', UpdateCareerOpeningView.as_view(), name='update_career_opening'),
    path('get-career-opening-all/<int:year>/<str:status>', GetCareerOpeningView.as_view(), name='get_career_opening'),
    path('delete-opening/', DeleteCareerOpeningView.as_view(), name='delete_career_opening'),
    path('close-opening/', CloseCareerOpeningView.as_view(), name='close_career_opening'),
    path('get-career-opened/',GetCareerOpenedView.as_view(),name='get_career_opened'),
    path('get-skills/', GetSkillsView.as_view(), name='get_skills'),


    path('get-all-candidates/', GetAllCandidateView.as_view(), name='get_all_candidate'),
    path('get-all-candidates-by-position/<int:position>/', GetAllCandidateView.as_view(), name='get_all_candidates_position'),
    path('get-all-candidates-by-status/<int:status>/', GetAllCandidateView.as_view(), name='get_all_candidate_status'),
    path('get-all-candidates-by-position-or-status/<int:position>/<int:status>/', GetAllCandidateView.as_view(), name='get_all_candidate_pos_status'),
    path('create-candidate/', CreateCandidateView.as_view(), name='create_candidate'),
    path('update-candidate/', UpdateCandidateView.as_view(), name='update_candidate'),
    path('delete-candidate/',DeleteCandidateView.as_view(), name='delete_candidate'),
    path('offer-released/', CandidateOfferReleasedView.as_view(), name='candidate_offer_released'),
    path('status-change-to-rejected/', CandidateStatusRejectedView.as_view(), name='candidate_status_change_to_rejected'),
    path('candidate-action-validation/<int:candidate_id>/<str:action>/', CandidateActionValidation.as_view(), name='candidate_action_validation'),
    path('get-candidate-information-sheet/<str:token>/', GetCandidateInformationSheetView.as_view(), name='get_candidate_information_sheet'),
    path('get-candidate-information-sheet-v1/<str:token>/', GetCandidateInformationSheetView_V1.as_view(), name='get_candidate_information_sheet_v1'),

    path('get-candidate-file/<int:candidate_id>/', GetCandidateFile.as_view(), name='get_candidate_file'),

    path('interview-action-validation/<int:interview_id>/<str:action>/', InterviewActionValidation.as_view(), name='interview_action_validation'),
    path('check-interview-status/<int:candidate_id>',CheckInterviewStatus.as_view(),name='check_interview_status'),
    path('create-interview/' , CreateInterviewView.as_view(), name='create_interview'),
    path('update-interview/', UpdateInterviewView.as_view(), name='update_interview'),
    path('get-all-interviews/<int:year>/<int:status>', GetInterviewView.as_view(), name='get_all_interviews'),
    path('cancel-interview/', CancelInterviewView.as_view(), name='cancel_interview'),
    path('reschedule-interview/', RescheduleInterviewView.as_view(), name='reschedule_interview'),
    path('update-interview-comment/',UpdateInterviewCommentView.as_view(), name='update_interview_comment_mail'),
    path('get-all-interview-comments/<int:interview_id>',GetInterviewCommentsView.as_view(), name='update_interview_comment_mail'),


    path('generate-inteview-scorecard/<int:interview_id>',GenerateInterviewScorecard.as_view(),name='generate-inteview-scorecard'),
    path('create-interview-scorecard/',CreateInterviewScoreCard.as_view(), name='create_interview_scorecard'),
    path('get-interview-scorecard-by-candidate/<int:candidate_id>',GetCandidateInterviewScorecard.as_view(), name='get_interview_scorecard_by_candidate'),
    path('get-interview-scorecard-by-interview/<int:interview_id>',GetInterviewScorecard.as_view(), name='get_interview_scorecard_by_interview'),
    path('save-candidate-information-sheet/',UpdateCandidateInformationSheet.as_view(), name='save_candidate_information_sheet'),


    path('send-mail/',SendMail.as_view(), name='send-mail'),
     
    

    


    #TODO -
    #path('get-inteview-scorecard/<int:interviewID>',GetInterviewScorecard.as_view(),name='get_interview_scorecard'),
    #path('update-interview-score-card/',UpdateInterviewScoreCard.as_view(), name='update_interview_score_card'),

    #path('update-interview-score-card/',UpdateInterviewScoreCard.as_view(), name='update_interview_score_card'),

    #TODO - confirmation mail
    #path('send-email-confirmation/<int:interviewID>',CreateInterviewConfirmationView.as_view(), name='create_interview_confirmation'),


    # path('search-candidate/<str:search_parameter>' , SearchCandidateView.as_view(), name='search_candidate'),




    #path('get-inteview-scorecard/<int:interviewID>',GetInterviewScorecard.as_view(),name='get_interview_scorecard'),





]
