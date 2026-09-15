from django.urls import path
from pTracker.api.appraisal.views import GetEligibleEmployess
from pTracker.api.appraisal.views import InitiateAppraisal
from pTracker.api.appraisal.views import AppraisalFormView
from pTracker.api.appraisal.views import UpdateAppraisalForm
from pTracker.api.appraisal.views import GetAllAppraisalView
from pTracker.api.appraisal.views import GetAllAppraisalBatches
from pTracker.api.appraisal.views import PublishAppraisalNormalizationResult
from pTracker.api.appraisal.views import GenerateAppraisalExcelReport
from pTracker.api.appraisal.views import GetAppraisalResponseReport
from pTracker.api.appraisal.views import  UploadAppraisalDocument
from pTracker.api.appraisal.views import  DownloadPerformanceAssesmentLetter
from pTracker.api.appraisal.views import  PublishPerformanceAssesmentLetter

urlpatterns = [
     path('get-all-eligible-employees/<int:year>/<int:organization>/<str:doj>/', GetEligibleEmployess.as_view(), name='get_all_eligible_employees'),
     path('initiate-appraisal/', InitiateAppraisal.as_view(), name='initiate_appraisal'),
     path('get-all-appraisal/', GetAllAppraisalView.as_view(), name='get_all_appraisal'),
     path('update-appraisal-form/', UpdateAppraisalForm.as_view(), name='update_appraisal_form'),
     path('appraisal-form-view/', AppraisalFormView.as_view(), name='appraisal_form_view'),
     path('get-all-appraisal-batches/', GetAllAppraisalBatches.as_view(), name='get_all_appraisal_batches'),
     path('publish-normalization-result/', PublishAppraisalNormalizationResult.as_view(), name='publish_normalization_result/'),
     path('generate-appraisal-excel-report/', GenerateAppraisalExcelReport.as_view(), name='generate_appraisal_excel_report'),
     path('get-appraisal-response-report/', GetAppraisalResponseReport.as_view(), name='get_appraisal_response_report'),
     path('upload-appraisal-report/', UploadAppraisalDocument.as_view(), name='upload_appraisal_report'),
     path('get-annual-assessment-letter/', DownloadPerformanceAssesmentLetter.as_view(), name='get_annual_assessment_letter'),
     path('publish-annual-assessment-letter/', PublishPerformanceAssesmentLetter.as_view(), name='publish_annual_assessment_letter'),
]