
from rest_framework.permissions import IsAuthenticated
from rest_framework.response import Response
from rest_framework.views import APIView
from rest_framework_simplejwt.authentication import JWTAuthentication as JSONWebTokenAuthentication
from rest_framework.parsers import MultiPartParser, FormParser, JSONParser

from pTracker.api.finance.finance_biz import FinanceBL
from pTracker.api.finance.tax_biz import TaxBL
from pTracker.api.finance.tax_mail_biz import TaxMailBL
from pTracker.api.finance.tax_report_biz import TaxReportBL
from pTracker.api.finance.tds_biz import TDSBL
from pTracker.cronjobs.user_profile_one_time_update import TestDBUpdate
from pTracker.api.finance.tax_compute_pdf_generation import TaxComputeBL
from pTracker.api.finance.emp_ctc_biz import EmployeeCtcBL
from pTracker.api.finance.tax_deduction import TaxDeduction

class ManagePayslip(APIView):
    authentication_classes = [JSONWebTokenAuthentication]
    permission_classes = [IsAuthenticated]
    parser_classes = (MultiPartParser,FormParser,JSONParser)

    def get(self, request, year, org):
        header_list = FinanceBL().manage_payslip(request, year, org)
        return Response(header_list)

    def put(self, request):
        response = FinanceBL().process_payslip(request)
        return Response(response, status = response.get("status", 200))


class GetParamsViews(APIView):
    authentication_classes = [JSONWebTokenAuthentication]
    permission_classes = [IsAuthenticated]

    def get(self, request):
        header_list = FinanceBL().get_dropdown_prams(request)
        return Response(header_list)


class RevokePayslip(APIView):
    authentication_classes = [JSONWebTokenAuthentication]
    permission_classes = [IsAuthenticated]
    parser_classes = (MultiPartParser,FormParser,JSONParser)

    def put(self, request):
        response = FinanceBL().revoke_payslip(request)
        return Response(response, status = response.get("status", 200))


class PublishPayslip(APIView):
    authentication_classes = [JSONWebTokenAuthentication]
    permission_classes = [IsAuthenticated]
    parser_classes = (MultiPartParser,FormParser,JSONParser)

    def put(self, request):
        response = FinanceBL().publish_payslip(request)
        return Response(response, status = response.get("status", 200))


class ValidatePayslip(APIView):
    authentication_classes = [JSONWebTokenAuthentication]
    permission_classes = [IsAuthenticated]

    def get(self, request, header_id):
        header_list = FinanceBL().validate_payslip(request, header_id)
        return Response(header_list)


class DownloadPayslip(APIView):
    authentication_classes = [JSONWebTokenAuthentication]
    permission_classes = [IsAuthenticated]

    def get(self, request):
        response = FinanceBL().download_payslip(request)
        return response

class GetMyPaySlips(APIView):
    authentication_classes = [JSONWebTokenAuthentication]
    permission_classes = [IsAuthenticated]

    def get(self, request, year):
        response = FinanceBL().get_my_pay_list(request,year)
        return Response(response)


class DownloadDummyPayslip(APIView):
    authentication_classes = [JSONWebTokenAuthentication]
    permission_classes = [IsAuthenticated]

    def get(self, request):
        response = FinanceBL().download_dummy_payslip(request)
        return response


class GetInitiateAssessmentDropdowns(APIView):
    authentication_classes = [JSONWebTokenAuthentication]
    permission_classes = [IsAuthenticated]

    def get(self, request):
        response = TaxBL().get_dropdown_params_for_initiate_assessment(request)
        return Response(response)


class GetCTCDropdowns(APIView):
    authentication_classes = [JSONWebTokenAuthentication]
    permission_classes = [IsAuthenticated]

    def get(self, request, fin_year_id):
        response = EmployeeCtcBL().get_dropdown_params_for_ctc(request, fin_year_id)
        return Response(response)


class CreateClaimsData(APIView):
    authentication_classes = [JSONWebTokenAuthentication]
    permission_classes = [IsAuthenticated]
    parser_classes = (MultiPartParser,FormParser,JSONParser)

    def put(self, request):
        response = TaxBL().initiate_claims_forms(request)
        return Response(response)


class DeleteTaxPeriod(APIView):
    authentication_classes = [JSONWebTokenAuthentication]
    permission_classes = [IsAuthenticated]
    parser_classes = (MultiPartParser,FormParser,JSONParser)

    def put(self, request):
        response = TaxBL().delete_tax_period(request)
        return Response(response)



class ClaimApproval(APIView):
    authentication_classes = [JSONWebTokenAuthentication]
    permission_classes = [IsAuthenticated]
    parser_classes = (MultiPartParser,FormParser,JSONParser)

    def put(self, request, claim_id):
        response = TaxBL().approve_claim(request, claim_id)
        return Response(response)

class SendMessage(APIView):
    authentication_classes = [JSONWebTokenAuthentication]
    permission_classes = [IsAuthenticated]
    parser_classes = (MultiPartParser,FormParser,JSONParser)

    def put(self, request, emp_id):
        response = TaxBL().send_message(request, emp_id)
        return Response(response)



class UpdateClaimsData(APIView):
    authentication_classes = [JSONWebTokenAuthentication]
    permission_classes = [IsAuthenticated]
    parser_classes = (MultiPartParser,FormParser,JSONParser)

    def put(self, request):
        response = TaxBL().update_claims_forms(request)
        return Response(response)



class UpdateClaimsFormData(APIView):
    authentication_classes = [JSONWebTokenAuthentication]
    permission_classes = [IsAuthenticated]
    parser_classes = (MultiPartParser,FormParser,JSONParser)

    def get(self, request, tax_period_id):
        response = TaxBL().get_tax_period_data(request, tax_period_id)
        return Response(response)

    def put(self, request):
        response = TaxBL().update_claims_forms(request)
        return Response(response)


class UpdateTaxBatch(APIView):
    authentication_classes = [JSONWebTokenAuthentication]
    permission_classes = [IsAuthenticated]
    parser_classes = (MultiPartParser,FormParser,JSONParser)

    def put(self, request, is_edit=0):
        response = TaxBL().add_tax_batch(request, is_edit)
        return Response(response)

    def delete(self, request):
        response = TaxBL().delete_tax_batch(request)
        return Response(response)

class DeleteTaxBatch(APIView):
    authentication_classes = [JSONWebTokenAuthentication]
    permission_classes = [IsAuthenticated]
    parser_classes = (MultiPartParser,FormParser,JSONParser)

    def put(self, request, is_edit=0):
        response = TaxBL().delete_tax_batch(request)
        return Response(response)



class GetClaimsDataList(APIView):
    authentication_classes = [JSONWebTokenAuthentication]
    permission_classes = [IsAuthenticated]

    def get(self, request, year_id):
        response = TaxBL().list_all_claims_data(request, year_id)
        return Response(response)



class ManageMyDecalarationForm(APIView):
    authentication_classes = [JSONWebTokenAuthentication]
    permission_classes = [IsAuthenticated]
    parser_classes = (MultiPartParser,FormParser,JSONParser)

    def get(self, request, emp_id, tax_period_id=0):
        response = TaxBL().get_my_declarations(request, emp_id, tax_period_id)
        return Response(response)

    def put(self, request):
        response = TaxBL().create_declaration(request)
        return Response(response)


class UpdateMyDecalarationForm(APIView):
    authentication_classes = [JSONWebTokenAuthentication]
    permission_classes = [IsAuthenticated]
    parser_classes = (MultiPartParser,FormParser,JSONParser)

    def put(self, request):
        response = TaxBL().edit_claim_declaration_data(request)
        return Response(response)


class DeleteMyDecalarationForm(APIView):
    authentication_classes = [JSONWebTokenAuthentication]
    permission_classes = [IsAuthenticated]
    parser_classes = (MultiPartParser,FormParser,JSONParser)

    def put(self, request):
        response = TaxBL().delete_declaration(request)
        return Response(response)


class GetUserTaxEligibility(APIView):
    authentication_classes = [JSONWebTokenAuthentication]
    permission_classes = [IsAuthenticated]

    def get(self, request):
        response = TaxBL().get_user_tax_eligibilty(request)
        return Response(response)


class ManageParties(APIView):
    authentication_classes = [JSONWebTokenAuthentication]
    permission_classes = [IsAuthenticated]
    parser_classes = (MultiPartParser,FormParser,JSONParser)


    def get(self, request):
        response = TaxBL().get_parties(request)
        return Response(response)

    def put(self, request):
        response = TaxBL().create_employee_claim(request)
        return Response(response)


class UpdateParties(APIView):
    authentication_classes = [JSONWebTokenAuthentication]
    permission_classes = [IsAuthenticated]
    parser_classes = (MultiPartParser,FormParser,JSONParser)

    def get(self, request, party_id):
        response = TaxBL().get_party_data(request, party_id)
        return Response(response)

    def put(self, request, party_id):
        response = TaxBL().update_parties(request, party_id)
        return Response(response)


class GetCategories(APIView):
    authentication_classes = [JSONWebTokenAuthentication]
    permission_classes = [IsAuthenticated]

    def get(self, request, parent_id):
        response = TaxBL().get_sub_category_by_parent_id(request, parent_id)
        return Response(response)


class ManageClaimDeclarationProof(APIView):
    authentication_classes = [JSONWebTokenAuthentication]
    permission_classes = [IsAuthenticated]
    parser_classes = (MultiPartParser,FormParser,JSONParser)

    def put(self, request):
        response = TaxBL().create_employee_claim(request)
        return Response(response)

    def get(self, request, claim_id):
        response = TaxBL().get_claim_by_claim_id(request, claim_id)
        return Response(response)


class GetClaimProof(APIView):
    authentication_classes = [JSONWebTokenAuthentication]
    permission_classes = [IsAuthenticated]

    def get(self, request):
        response = TaxBL().get_file(request)
        return response


class ListTaxPeriods(APIView):
    authentication_classes = [JSONWebTokenAuthentication]
    permission_classes = [IsAuthenticated]

    def get(self, request):
        response = TaxBL().get_tax_periods(request)
        return Response(response)


class UpdateClaimDeclarationProof(APIView):
    authentication_classes = [JSONWebTokenAuthentication]
    permission_classes = [IsAuthenticated]
    parser_classes = (MultiPartParser,FormParser,JSONParser)

    def put(self, request):
        response = TaxBL().update_employee_claim(request)
        return Response(response)


class DeleteClaimDeclarationProof(APIView):
    authentication_classes = [JSONWebTokenAuthentication]
    permission_classes = [IsAuthenticated]
    parser_classes = (MultiPartParser,FormParser,JSONParser)

    def put(self, request):
        response = TaxBL().delete_employee_claim(request)
        return Response(response)


class CreateDecalarationForm(APIView):
    authentication_classes = [JSONWebTokenAuthentication]
    permission_classes = [IsAuthenticated]
    parser_classes = (MultiPartParser,FormParser,JSONParser)

    def get(self, request, financial_year_id, emp_id):
        response = TaxReportBL().create_12bb_actual_sheet(request,financial_year_id, emp_id)
        return response


class GetAssessmentReport(APIView):
    authentication_classes = [JSONWebTokenAuthentication]
    permission_classes = [IsAuthenticated]
    # parser_classes = (MultiPartParser,FormParser,JSONParser)

    def get(self, request, tax_period_id):
        response = TaxReportBL().get_assessment_report(request, tax_period_id)
        return Response(response)


class CreateEstimateDecalarationForm(APIView):
    authentication_classes = [JSONWebTokenAuthentication]
    permission_classes = [IsAuthenticated]
    parser_classes = (MultiPartParser,FormParser,JSONParser)

    def get(self, request, financial_year_id, emp_id):
        response = TaxReportBL().create_12bb_estimate_sheet(request, financial_year_id, emp_id)
        return response


# class GenerateTaxCompute(APIView):
#     authentication_classes = [JSONWebTokenAuthentication]
#     permission_classes = [IsAuthenticated]
#     parser_classes = (MultiPartParser,FormParser,JSONParser)

#     def post(self, request):
#         response = TaxComputeBL().generate_pdf(request)
#         return response



class GetChatHistory(APIView):
    authentication_classes = [JSONWebTokenAuthentication]
    permission_classes = [IsAuthenticated]

    def get(self, request, chat_id, tax_period_id):
        response = TaxBL().get_chat_history(request, chat_id, tax_period_id)
        return Response(response)


class GetOrCreateChat(APIView):
    authentication_classes = [JSONWebTokenAuthentication]
    permission_classes = [IsAuthenticated]
    parser_classes = (MultiPartParser,FormParser,JSONParser)

    def put(self, request):
        response = TaxBL().get_or_create_chat(request)
        return Response(response)


class SendReminderAllNotCompleted(APIView):
    authentication_classes = [JSONWebTokenAuthentication]
    permission_classes = [IsAuthenticated]
    parser_classes = (MultiPartParser,FormParser,JSONParser)

    def get(self, request, tax_period_id):
        response = TaxMailBL().send_reminder_all_not_completed_tax(request, tax_period_id)
        return Response(response)


class SendReminderOneEmployeeNotCompleted(APIView):
    authentication_classes = [JSONWebTokenAuthentication]
    permission_classes = [IsAuthenticated]
    parser_classes = (MultiPartParser,FormParser,JSONParser)

    def get(self, request, emp_id, tax_period_id):
        response = TaxMailBL().send_reminder_one_employee_not_completed_tax(request, emp_id, tax_period_id)
        return Response(response)


class GetEmployeeTDSData(APIView):
    authentication_classes = [JSONWebTokenAuthentication]
    permission_classes = [IsAuthenticated]
    parser_classes = (MultiPartParser,FormParser,JSONParser)

    def get(self, request, fin_year_id, org_id):
        response = TDSBL().get_employee_tds_data(request, fin_year_id, org_id)
        return Response(response)


class UpdateEmployeeTDSData(APIView):
    authentication_classes = [JSONWebTokenAuthentication]
    permission_classes = [IsAuthenticated]
    parser_classes = (MultiPartParser,FormParser,JSONParser)

    def put(self, request):
        response = TDSBL().update_employee_tds_data(request)
        return Response(response)


# class UserProfileOneTimeUpdate(APIView):
#     authentication_classes = [JSONWebTokenAuthentication]
#     permission_classes = [IsAuthenticated]

#     def put(self, request):
#         csv_file_path = '/home/digitalmesh/Downloads/testupdate.csv'
#         response = TestDBUpdate().update_user_profiles_from_csv(csv_file_path)
#         return Response(response)


class GetEmployeeCTC(APIView):
    authentication_classes = [JSONWebTokenAuthentication]
    permission_classes = [IsAuthenticated]
    parser_classes = (MultiPartParser,FormParser,JSONParser)

    def get(self, request, fin_year_id, org_id):
        response = EmployeeCtcBL().get_employees_ctc(request, fin_year_id, org_id)
        return Response(response)


# class CreateorUpdateCtcEmployeeDetails(APIView):
#     authentication_classes = [JSONWebTokenAuthentication]
#     permission_classes = [IsAuthenticated]

#     def put(self, request):
#         response = EmployeeCtcBL().create_or_update_ctc_employee(request)
#         return Response(response)


class UpdateEmployeCTC(APIView):
    authentication_classes = [JSONWebTokenAuthentication]
    permission_classes = [IsAuthenticated]
    parser_classes = (MultiPartParser,FormParser,JSONParser)

    def put(self, request):
        response = EmployeeCtcBL().update_employee_ctc(request)
        return Response(response)


class GetCTCCategories(APIView):
    authentication_classes = [JSONWebTokenAuthentication]
    permission_classes = [IsAuthenticated]
    parser_classes = (MultiPartParser,FormParser,JSONParser)

    def get(self, request):
        response = EmployeeCtcBL().get_ctc_categories(request)
        return Response(response)


class GetUserCTC(APIView):
    authentication_classes = [JSONWebTokenAuthentication]
    permission_classes = [IsAuthenticated]
    parser_classes = (MultiPartParser,FormParser,JSONParser)

    def get(self, request):
        response = EmployeeCtcBL().get_user_ctc(request)
        return Response(response)


class CreateEmployeeCTC(APIView):
    authentication_classes = [JSONWebTokenAuthentication]
    permission_classes = [IsAuthenticated]
    parser_classes = (MultiPartParser,FormParser,JSONParser)

    def put(self, request):
        response = EmployeeCtcBL().create_employee_ctc(request)
        return Response(response)


# class CtcEmployeeCsvUpdate(APIView):
#     authentication_classes = [JSONWebTokenAuthentication]
#     permission_classes = [IsAuthenticated]
class ImportCsvtoCtc(APIView):
    authentication_classes = [JSONWebTokenAuthentication]
    permission_classes = [IsAuthenticated]
    parser_classes = (MultiPartParser,FormParser,JSONParser)

    def put(self, request):
        response = EmployeeCtcBL().import_csv_ctc(request)
        return Response(response)


class CtcEmployeeCsvUpdate(APIView):
    authentication_classes = [JSONWebTokenAuthentication]
    permission_classes = [IsAuthenticated]

#     def put(self, request):
#         csv_file_path = '/home/digitalmesh/Downloads/testupdate.csv'
#         response = TestDBUpdate().update_ctc_employee_from_csv(request,csv_file_path)
#         return Response(response)


class TaxComputation(APIView):
    authentication_classes = [JSONWebTokenAuthentication]
    permission_classes = [IsAuthenticated]
    parser_classes = (MultiPartParser,FormParser,JSONParser)

    def get(self, request, emp_id, fin_year_id):
        response = TaxComputeBL().generate_tax_computation(request, emp_id, fin_year_id)
        if 'error' in response:
            return Response(response, status=499)
        return response


# class GenerateNewtaxCalculation(APIView):
#     authentication_classes = [JSONWebTokenAuthentication]
#     permission_classes = [IsAuthenticated]
#     parser_classes = (MultiPartParser,FormParser,JSONParser)

#     def post(self, request, emp_id, fin_yr_id):
#         response = TaxComputeBL().tax_compution_pdf(request, emp_id, fin_yr_id)
#         return response


class GetAllOtherIncomeAndDeduction(APIView):
    authentication_classes = [JSONWebTokenAuthentication]
    permission_classes = [IsAuthenticated]
    parser_classes = (MultiPartParser,FormParser,JSONParser)

    def get(self, request, fin_yr_id, org_id):
        response = TaxDeduction().get_all_other_income_and_deduction(request, fin_yr_id, org_id)
        return Response(response)


class CreateOtherIncomeDeduction(APIView):
    authentication_classes = [JSONWebTokenAuthentication]
    permission_classes = [IsAuthenticated]
    parser_classes = (MultiPartParser,FormParser,JSONParser)

    def put(self, request):
        response = TaxDeduction().create_other_income_deduction(request)
        return Response(response)


class UpdateOtherIncomeDeduction(APIView):
    authentication_classes = [JSONWebTokenAuthentication]
    permission_classes = [IsAuthenticated]
    parser_classes = (MultiPartParser,FormParser,JSONParser)

    def put(self, request):
        response = TaxDeduction().update_other_income_deduction(request)
        return Response(response)


class DeleteOtherIncomeDeduction(APIView):
    authentication_classes = [JSONWebTokenAuthentication]
    permission_classes = [IsAuthenticated]
    parser_classes = (MultiPartParser,FormParser,JSONParser)

    def put(self, request):
        response = TaxDeduction().delete_other_income_deduction(request)
        return Response(response)


class CreateEmployeeTDSData(APIView):
    authentication_classes = [JSONWebTokenAuthentication]
    permission_classes = [IsAuthenticated]
    parser_classes = (MultiPartParser,FormParser,JSONParser)

    def put(self, request):
        response = TDSBL().create_tds_data(request)
        return Response(response)