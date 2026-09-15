from django.urls import re_path as url
from django.contrib import admin
from django.urls import path

from pTracker.api.finance.views import GetParamsViews
from pTracker.api.finance.views import ManagePayslip
from pTracker.api.finance.views import RevokePayslip
from pTracker.api.finance.views import PublishPayslip
from pTracker.api.finance.views import DownloadPayslip
from pTracker.api.finance.views import DownloadDummyPayslip
from pTracker.api.finance.views import ValidatePayslip
from pTracker.api.finance.views import GetMyPaySlips


#12b
from pTracker.api.finance.views import CreateClaimsData
from pTracker.api.finance.views import GetClaimsDataList
from pTracker.api.finance.views import ManageMyDecalarationForm
from pTracker.api.finance.views import ManageParties
from pTracker.api.finance.views import UpdateParties
from pTracker.api.finance.views import GetInitiateAssessmentDropdowns
from pTracker.api.finance.views import GetCTCDropdowns
from pTracker.api.finance.views import GetUserTaxEligibility
from pTracker.api.finance.views import GetCategories
from pTracker.api.finance.views import ManageClaimDeclarationProof
from pTracker.api.finance.views import UpdateClaimsData
from pTracker.api.finance.views import GetClaimProof
from pTracker.api.finance.views import CreateDecalarationForm
from pTracker.api.finance.views import CreateEstimateDecalarationForm
from pTracker.api.finance.views import UpdateMyDecalarationForm
from pTracker.api.finance.views import DeleteMyDecalarationForm
from pTracker.api.finance.views import UpdateClaimDeclarationProof
from pTracker.api.finance.views import DeleteClaimDeclarationProof
from pTracker.api.finance.views import ListTaxPeriods
from pTracker.api.finance.views import UpdateClaimsFormData
from pTracker.api.finance.views import UpdateTaxBatch
from pTracker.api.finance.views import DeleteTaxPeriod
from pTracker.api.finance.views import ClaimApproval

from pTracker.api.finance.views import DeleteTaxBatch
from pTracker.api.finance.views import GetAssessmentReport
from pTracker.api.finance.views import TaxComputation
#from pTracker.api.finance.views import GenerateNewtaxCalculation
from pTracker.api.finance.views import SendMessage
from pTracker.api.finance.views import GetChatHistory
from pTracker.api.finance.views import GetOrCreateChat
from pTracker.api.finance.views import SendReminderAllNotCompleted
from pTracker.api.finance.views import SendReminderOneEmployeeNotCompleted
#from pTracker.api.finance.views import UserProfileOneTimeUpdate
#from pTracker.api.finance.views import CreateorUpdateCtcEmployeeDetails
from pTracker.api.finance.views import UpdateEmployeCTC
from pTracker.api.finance.views import GetEmployeeCTC
from pTracker.api.finance.views import GetCTCCategories
from pTracker.api.finance.views import CreateEmployeeCTC
from pTracker.api.finance.views import GetEmployeeTDSData
from pTracker.api.finance.views import UpdateEmployeeTDSData
#from pTracker.api.finance.views import CtcEmployeeCsvUpdate
from pTracker.api.finance.views import GetAllOtherIncomeAndDeduction
from pTracker.api.finance.views import UpdateOtherIncomeDeduction
from pTracker.api.finance.views import CreateOtherIncomeDeduction
from pTracker.api.finance.views import DeleteOtherIncomeDeduction
from pTracker.api.finance.views import CreateEmployeeTDSData
from pTracker.api.finance.views import ImportCsvtoCtc
from pTracker.api.finance.views import GetUserCTC

urlpatterns = [
    path('get-finance-params/', GetParamsViews.as_view(), name="get_fianance_params"),
    path('manage-payslip/<str:year>/<str:org>/', ManagePayslip.as_view(), name="manage_payslip"),
    path('process-payslip/', ManagePayslip.as_view(), name='process_payslip'),
    path('validate-payslip/<str:header_id>/', ValidatePayslip.as_view(), name='validate_payslip'),
    path('revoke-payslip/', RevokePayslip.as_view(), name='revoke_payslip'),
    path('publish-payslip/', PublishPayslip.as_view(), name='publish_payslip'),
    path('my-payslip/<str:year>/', GetMyPaySlips.as_view(), name='get_my_payslip'),
    path('download-payslip/', DownloadPayslip.as_view(), name='download_payslip'),
    path('download-dummy-payslip/', DownloadDummyPayslip.as_view(), name='download_dummy_payslip'),



    #12b
    path('get-tax-dropdowns/', GetInitiateAssessmentDropdowns.as_view(), name='tax_dropdown'),
    path('get-sub-categories/<int:parent_id>/', GetCategories.as_view(), name='get_sub_category_by_parent_id'),

    path('is-user-eligible-for-tax/', GetUserTaxEligibility.as_view(), name='user_tax_eligibility'),

    #Manage Assessment Period
    path('list-tax-periods/', ListTaxPeriods.as_view(), name='list_tax_periods'),
    path('initiate-claim-declaration-form/', CreateClaimsData.as_view(), name='initiate_claim_declaration_form'),
    path('update-claim-declaration-form/', UpdateClaimsData.as_view(), name='update_claim_declaration_form'),
    path('delete-tax-period/', DeleteTaxPeriod.as_view(), name='delete_tax_period'),

    path('get-tax-period-details/<int:tax_period_id>/', UpdateClaimsFormData.as_view(), name='get_tax_period_details'),

    #Add employee to a tax period
    path('add-tax-batch-employees/', UpdateTaxBatch.as_view(), name='add_tax_batch_employees'),
    path('update-tax-batch-employees/<int:is_edit>', UpdateTaxBatch.as_view(), name='edit_tax_batch_employees'),
    path('remove-tax-batch-employees/', DeleteTaxBatch.as_view(), name='remove_tax_batch_employees'),

    path('add-claims/', ManageClaimDeclarationProof.as_view(), name='add_claim_declaration_proof'),
    path('update-claims/', UpdateClaimDeclarationProof.as_view(), name='update_claim_declaration_proof'),
    path('delete-claims/', DeleteClaimDeclarationProof.as_view(), name='delete_claim_declaration_proof'),

    #Add declarion amount by employee
    path('add-claim-decalaration/', ManageMyDecalarationForm.as_view(), name='create_decalaration_form'),
    path('edit-claim-decalaration/', UpdateMyDecalarationForm.as_view(), name='create_decalaration_form'),
    path('delete-claim-decalaration/', DeleteMyDecalarationForm.as_view(), name='create_decalaration_form'),

    path('get-my-decalarations/<int:emp_id>/<int:tax_period_id>/', ManageMyDecalarationForm.as_view(), name='manage_my_decalaration'),
    path('get-all-claim-decalarations/<int:year_id>/', GetClaimsDataList.as_view(), name='manage_all_decalaration'),

    path('generate-12b/<int:financial_year_id>/<int:emp_id>/', CreateDecalarationForm.as_view(), name='create_decalaration_xl'),
    path('generate-12b-estimate/<int:financial_year_id>/<int:emp_id>/', CreateEstimateDecalarationForm.as_view(), name='create_estimate_decalaration_xl'),

    path('claim-approval/<int:claim_id>/', ClaimApproval.as_view(), name='claim_approval'),
    path('send-suggestion-message/<int:emp_id>/', SendMessage.as_view(), name='send_message'),

    path('get-claim-detail-view/<int:claim_id>/', ManageClaimDeclarationProof.as_view(), name='get_parties'),

    path('get-parties/', ManageParties.as_view(), name='get_parties'),
    path('create-parties/', ManageParties.as_view(), name='create_parties'),
    path('get-parties-data/<int:party_id>/', UpdateParties.as_view(), name='get_parties_data'),
    path('update-parties/<int:party_id>/', UpdateParties.as_view(), name='update_parties'),

    path('view-file/', GetClaimProof.as_view(), name='get_parties'),

    path('get-assessment-report/<int:tax_period_id>/', GetAssessmentReport.as_view(), name='get_tax_period_details'),
    path('send-reminder-all-not-completed/<int:tax_period_id>/', SendReminderAllNotCompleted.as_view(), name='send_reminder_all_not_completed_tax'),
    path('send-reminder-one-person-not-completed/<int:emp_id>/<int:tax_period_id>/', SendReminderOneEmployeeNotCompleted.as_view(), name='send_reminder_all_not_completed_tax'),



    path('get-or-create-chat/', GetOrCreateChat.as_view(), name='get_or_create_chat'),
    path('get-chat-history/<int:chat_id>/<int:tax_period_id>/', GetChatHistory.as_view(), name='get_chat_history'),

    #Employee TDS
    path('get-employee-tds-data/<int:fin_year_id>/<int:org_id>/', GetEmployeeTDSData.as_view(), name='get_employee_tds_data'),
    path('update-employee-tds-data/', UpdateEmployeeTDSData.as_view(), name='update_employee_tds_data'),
    path('create-employee-tds-data/', CreateEmployeeTDSData.as_view(), name='create_employee_tds_data'),
    #path('user-profile-one-time-update/', UserProfileOneTimeUpdate.as_view(), name='user_profile_one_time_update'),

    #Employee CTC
    path('get-ctc-dropdowns/<int:fin_year_id>/', GetCTCDropdowns.as_view(), name='ctc_dropdown'),
    path('get-ctc-categories/', GetCTCCategories.as_view(), name='get_ctc_categories'),

    path('get-employees-ctc/<int:fin_year_id>/<int:org_id>/', GetEmployeeCTC.as_view(), name='get_employees_ctc'),
    path('add-new-ctc-employee/', CreateEmployeeCTC.as_view(), name='create_employee_ctc'),
    path('ctc-employee-details-edit/', UpdateEmployeCTC.as_view(), name='ctc_employee_details_edit'),


    #This URI for all users
    path('get-user-ctc/', GetUserCTC.as_view(), name='get_user_ctc'),
    #path('ctc-employee-csv-update/', CtcEmployeeCsvUpdate.as_view(), name='ctc_employee_one_time_update'),
    path('import-csv/', ImportCsvtoCtc.as_view(), name='import_csc_ctct'),




    #Other Income & Deduction
    path('get-all-tax-deduction-data/<int:fin_yr_id>/<int:org_id>/', GetAllOtherIncomeAndDeduction.as_view(), name='get_all_tax_deduction_data'),
    path('create-tax-deduction-data/', CreateOtherIncomeDeduction.as_view(), name='create_tax_deduction_data'),
    path('edit-tax-deduction-data/', UpdateOtherIncomeDeduction.as_view(), name='edit_tax_deduction_data'),
    path('delete-tax-deduction-data/', DeleteOtherIncomeDeduction.as_view(), name='delete_tax_deduction_data'),

    #Tax Computation
    path('tax-computation/<int:emp_id>/<int:fin_year_id>/', TaxComputation.as_view(), name='tax_computation'),
    #path('tax-compution-pdf/<int:emp_id>/<int:fin_yr_id>/', GenerateNewtaxCalculation.as_view(), name='generate_pdf'),
]

