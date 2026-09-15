from django.urls import re_path as url
from django.contrib import admin
from django.urls import path

from pTracker.api.induction.views import CreateInduction
from pTracker.api.induction.views import GetInductions
from pTracker.api.induction.views import GetInductionDetails
from pTracker.api.induction.views import UpdateInductionDetails
from pTracker.api.induction.views import GetProbationEmployees 
from pTracker.api.induction.views import DownloadInductionDetails 
from pTracker.api.induction.views import SendInductionReminder 

urlpatterns = [
    path('create-induction/', CreateInduction.as_view(), name="create_induction"),
    path('get-induction/<str:filter>/', GetInductions.as_view(), name="get_induction"),
    path('get-induction-details/<str:induction_id>/', GetInductionDetails.as_view(), name="get_induction_details"),
    path('update-induction-details/', UpdateInductionDetails.as_view(), name="update_induction_details"),
    path('get-all-new-employee/', GetProbationEmployees.as_view(), name="get_new_employees"),
    path('print-induction-details/', DownloadInductionDetails.as_view(), name="print_induction_details"),
    path('send-induction-reminder/<str:induction_id>/', SendInductionReminder.as_view(), name="send_induction_reminder")
]
