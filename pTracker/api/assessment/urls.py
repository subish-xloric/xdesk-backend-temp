from django.urls import re_path as url
from django.contrib import admin
from django.urls import path

from pTracker.api.assessment.views import CreateAssessment
from pTracker.api.assessment.views import ManageAssessee
from pTracker.api.assessment.views import ManageAssessment
from pTracker.api.assessment.views import GetDropdowns 
from pTracker.api.assessment.views import createAssessmentReport
from pTracker.api.assessment.views import ViewAssessmentReport
from pTracker.api.assessment.views import CancelAssessment
from pTracker.api.assessment.views import RescheduleAssessment
from pTracker.api.assessment.views import ViewAssesseeReport
from pTracker.api.assessment.views import DownloadAssessmentReport
from pTracker.api.assessment.views import getAssessors

urlpatterns = [
    path('get-dropdown-params/', GetDropdowns.as_view(), name="dropdown_assessee"),
    path('create-assessee/', CreateAssessment.as_view(), name="create_assessee"),
    path('manage-assessee/<str:status>/', ManageAssessee.as_view(), name="get_assessee"),
    path('manage-assessment/<str:status>/<str:year>/', ManageAssessment.as_view(), name="get_assessement"),
    path('update-assessee/', ManageAssessee.as_view(), name="update_assessee"),
    path('create-assessment-report/', createAssessmentReport.as_view(), name="create_assessment_report"),
    path('view-assessment-report/<str:assessment_id>/', ViewAssessmentReport.as_view(), name="view_assessment_report"),
    path('cancel-assessment/', CancelAssessment.as_view(), name="cancel_assessement"),
    path('reschedule-assessment/', RescheduleAssessment.as_view(), name="reschdule_assessement"),
    path('view-assessee-report/<str:assessee_id>/', ViewAssesseeReport.as_view(), name="view_assessee_report"),
    path('download-assessee-report/', DownloadAssessmentReport.as_view(), name="download_assessee_report"),
    path('get-assessors-list/<int:total_assessments>/<int:emp_id>/', getAssessors.as_view(), name="get_assessors"),
]
