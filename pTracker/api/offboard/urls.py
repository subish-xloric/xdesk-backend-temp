from django.urls import path

from pTracker.api.offboard.views import GenerateResigantionForm, TerminateEmployee
from pTracker.api.offboard.views import CreateFffboardingRequestView
from pTracker.api.offboard.views import UpdateOffBoardRequestView
from pTracker.api.offboard.views import GetOffboardingRequestView
from pTracker.api.offboard.views import DateAfterNWorkingDays
from pTracker.api.offboard.views import InitiateOffboarding
from pTracker.api.offboard.views import OffBoardingExitFormView
from pTracker.api.offboard.views import UpdateExitForm
from pTracker.api.offboard.views import UploadRelievingDocuments
from pTracker.api.offboard.views import OffBoardingDocumentsView
from pTracker.api.offboard.views import DeleteOffBoardingDocuments

from pTracker.api.offboard.views import ExitInterviewFormView
from pTracker.api.offboard.views import UpdateExitInterviewForm

urlpatterns = [
    path('generate-resigantion-form/',GenerateResigantionForm.as_view(), name='generate_resigantion_form'),
    path('get-offboarding-requests/', GetOffboardingRequestView.as_view(), name='get_offboarding_requests'),

    path('create-offboarding-request', CreateFffboardingRequestView.as_view(), name='create_off_board_request'),
    path('update-off-board-request', UpdateOffBoardRequestView.as_view(), name='update_off_board_request'),
    path('initiate-offboarding/',InitiateOffboarding.as_view(), name='initiate_offboarding'),



    path('date-after-n-working-days/', DateAfterNWorkingDays.as_view(), name='date_after_n_working_dates'),


    path('off-boarding-exit-form-view/',OffBoardingExitFormView.as_view(), name='off_boarding_exit_form_view'),
    path('update-exit-form/',UpdateExitForm.as_view(), name='update_exit_form'),
    path('upload-relieving-documents/',UploadRelievingDocuments.as_view(), name='upload_relieving_documents'),
    path('list-off-boarding-documents/',OffBoardingDocumentsView.as_view(), name='list_off_boarding_documents'),
    path('delete-boarding-document/',DeleteOffBoardingDocuments.as_view(), name='delete_boarding_document'),

    path('exit-interview-form-view/',ExitInterviewFormView.as_view(), name='exit_interview_form_view'),

    path('update-exit-interview-form/',UpdateExitInterviewForm.as_view(), name='update_exit_interview_form'),
    path('terminate-employee/',TerminateEmployee.as_view(), name='terminate_employee'),
    path('check-termination-process/<int:emp_id>/',TerminateEmployee.as_view(), name='check_termination_process'),

]