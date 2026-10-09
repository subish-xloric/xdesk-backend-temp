
from rest_framework.permissions import IsAuthenticated
from rest_framework.response import Response
from rest_framework.views import APIView
from rest_framework_simplejwt.authentication import JWTAuthentication as JSONWebTokenAuthentication
from rest_framework.parsers import MultiPartParser, FormParser, JSONParser

from pTracker.api.leave.leave_biz import LeaveBL
from pTracker.api.leave.leave_reports_biz import LeaveReportsBL
from pTracker.api.leave.leave_bulk_load_biz import LeaveBulkBL
from pTracker.api.leave.comp_off_biz import CompOffBL
from pTracker.api.leave.leave_biz_v1 import LeaveBL_V1
from pTracker.api.leave.leave_type_biz import LeaveTypeBL

class TeamLeaveCalendarView(APIView):
    authentication_classes = [JSONWebTokenAuthentication]
    permission_classes = [IsAuthenticated]

    def get(self, request):
        team_leave_list = LeaveBL().get_team_leave_calendar(request.user.id)
        return Response(team_leave_list)

class CreateFormDropdowns(APIView):
    authentication_classes = [JSONWebTokenAuthentication]
    permission_classes = [IsAuthenticated]

    def get(self, request):
        dropdowns = LeaveBL().fill_leave_apply_form_dropdowns()
        return Response(dropdowns)

class UserLeaveSummaryView(APIView):
    authentication_classes = [JSONWebTokenAuthentication]
    permission_classes = [IsAuthenticated]

    def get(self, request):
        leave_details = LeaveBL().get_user_leave_summary(request.user.id)
        return Response(leave_details)

class LeaveStatusUpdateView(APIView):
    authentication_classes = [JSONWebTokenAuthentication]
    permission_classes = [IsAuthenticated]

    def put(self, request):
        leave_details = LeaveBL().update_leave_status(request.data, request.user)
        return Response(leave_details)

class LeaveDateValidation(APIView):
    authentication_classes = [JSONWebTokenAuthentication]
    permission_classes = [IsAuthenticated]

    def put(self, request):
        leave_validation = LeaveBL().leave_date_validation(request, request.user.id)
        return Response(leave_validation)


class CreateLeaveRequest(APIView):
    authentication_classes = [JSONWebTokenAuthentication]
    permission_classes = [IsAuthenticated]

    def put(self, request):
        leave_validation = LeaveBL().create_leave_request(request, request.user)
        return Response(leave_validation)

class GetLeaveRequest(APIView):
    authentication_classes = [JSONWebTokenAuthentication]
    permission_classes = [IsAuthenticated]

    def put(self, request):
        leave_request = LeaveBL().get_leave_request_by_id(request.data, request.user.id)
        return Response(leave_request)

class UpdateLeaveRequest(APIView):
    authentication_classes = [JSONWebTokenAuthentication]
    permission_classes = [IsAuthenticated]

    def put(self, request):
        leave_request = LeaveBL().update_leave_request(request, request.user)
        return Response(leave_request)

class CompensatoryLeaveFormDropdowns(APIView):
    authentication_classes = [JSONWebTokenAuthentication]
    permission_classes = [IsAuthenticated]

    def get(self, request):
        dropdowns = CompOffBL().get_compo_off_form_dropdowns(request.user.id)
        return Response(dropdowns)

class CompensatoryLeaveDateValidation(APIView):
    authentication_classes = [JSONWebTokenAuthentication]
    permission_classes = [IsAuthenticated]

    def get(self, request):
        dropdowns = CompOffBL().compo_off_date_validation(request.GET,request.user.id)
        return Response(dropdowns)

class LeaveReportDropDowns(APIView):
    authentication_classes = [JSONWebTokenAuthentication]
    permission_classes = [IsAuthenticated]

    def get(self, request):
        dropdowns = LeaveBL().leave_report_dropdowns(request.user, request.GET)
        return Response(dropdowns)

class CreateCompensatoryLeave(APIView):
    authentication_classes = [JSONWebTokenAuthentication]
    permission_classes = [IsAuthenticated]

    def put(self, request):
        result = CompOffBL().create_compensatory_leave(request,request.user)
        return Response(result)

class LeaveReportList(APIView):
    authentication_classes = [JSONWebTokenAuthentication]
    permission_classes = [IsAuthenticated]

    def put(self, request):
        response = LeaveBL().leave_report_list(request.data, request.user.id)
        return Response(response)

class CompensataoryLeaveView(APIView):
    authentication_classes = [JSONWebTokenAuthentication]
    permission_classes = [IsAuthenticated]

    def get(self, request):
        leave_details = CompOffBL().get_all_compensatory_leave_request(request.user.id)
        return Response(leave_details)

class TeamMembersByLeadId(APIView):
    authentication_classes = [JSONWebTokenAuthentication]
    permission_classes = [IsAuthenticated]

    def get(self, request):
        dropdowns = LeaveBL().get_team_members_by_lead_id(request.user.id)
        return Response(dropdowns)

class LeaveSummaryReport(APIView):
    authentication_classes = [JSONWebTokenAuthentication]
    permission_classes = [IsAuthenticated]

    def get(self, request):
        dropdowns = LeaveReportsBL().get_leave_summary_report(request.user.id, request.GET)
        return Response(dropdowns)

class AnnualLeaveSummaryReport(APIView):
    authentication_classes = [JSONWebTokenAuthentication]
    permission_classes = [IsAuthenticated]

    def get(self, request):
        dropdowns = LeaveReportsBL().annual_leave_summary_report(request.user.id,request.GET)
        return Response(dropdowns)

class GetAllActiveUsers(APIView):
    authentication_classes = [JSONWebTokenAuthentication]
    permission_classes = [IsAuthenticated]

    def get(self, request):
        result = LeaveReportsBL().get_all_active_users()
        return Response(result)

class TeamLeaveSummaryView(APIView):
    authentication_classes = [JSONWebTokenAuthentication]
    permission_classes = [IsAuthenticated]

    def post(self, request):
        leave_request = LeaveBL().get_team_leave_summary(request.user.id, request.data)
        return Response(leave_request)

class TeamLeaveDropdownView(APIView):
    authentication_classes = [JSONWebTokenAuthentication]
    permission_classes = [IsAuthenticated]

    def get(self, request):
        leave_request = LeaveBL().team_leave_dropdowns(request.user.id)
        return Response(leave_request)

class UpdateCompensatoryLeave(APIView):
    authentication_classes = [JSONWebTokenAuthentication]
    permission_classes = [IsAuthenticated]

    def put(self, request):
        result = CompOffBL().update_compensatory_leaves(request.data,request.user)
        return Response(result)

class CompensatoryLeaveFilter(APIView):
    authentication_classes = [JSONWebTokenAuthentication]
    permission_classes = [IsAuthenticated]

    def put(self, request):
        result = CompOffBL().compensatory_leave_filter(request.data,request.user.id)
        return Response(result)

class LeaveQuotaView(APIView):
    authentication_classes = [JSONWebTokenAuthentication]
    permission_classes = [IsAuthenticated]

    def get(self, request, year):
        result = LeaveBulkBL().get_leave_quota(request.user.id, year)
        return Response(result)

class UpdateLeaveQuota(APIView):
    authentication_classes = [JSONWebTokenAuthentication]
    permission_classes = [IsAuthenticated]

    def put(self, request):
        result = LeaveBulkBL().update_leave_quota(request.user.id, request.data)
        return Response(result)

class CreditLeaveQuotaView(APIView):
    authentication_classes = [JSONWebTokenAuthentication]
    permission_classes = [IsAuthenticated]

    def get(self, request, year):
        result = LeaveBulkBL().credit_yearly_employee_leave(request.user.id, year)
        return Response(result)

class AnuualLeaveDetailView(APIView):
    authentication_classes = [JSONWebTokenAuthentication]
    permission_classes = [IsAuthenticated]

    def get(self, request, emp_id, year):
        result = LeaveReportsBL().get_annual_leave_analytics_report(request.user.id, year, emp_id)
        return Response(result)

class PendingRequestListView(APIView):
    authentication_classes = [JSONWebTokenAuthentication]
    permission_classes = [IsAuthenticated]

    def get(self, request):
        result = LeaveReportsBL().get_pending_leave_request_lists(request.user.id)
        return Response(result)

class LeaveRequestDateValidate(APIView):
    authentication_classes = [JSONWebTokenAuthentication]
    permission_classes = [IsAuthenticated]

    def get(self,request, start_date, end_date, edit_id ):
        result = CompOffBL().leave_request_date_validate(start_date, end_date, request.user.id, edit_id)
        return Response(result)

class PendingLeavesView(APIView):
    authentication_classes = [JSONWebTokenAuthentication]
    permission_classes = [IsAuthenticated]

    def get(self, request):
        result = LeaveReportsBL().get_pending_leaves(request.user.id)
        return Response(result)

class SendNotPunchNotification(APIView):
    authentication_classes = [JSONWebTokenAuthentication]
    permission_classes = [IsAuthenticated]

    def put(self, request):
        result = LeaveBL().send_not_punch_notification(request.user, request.data)
        return Response(result)

class DebitleavesView(APIView):
    authentication_classes = [JSONWebTokenAuthentication]
    permission_classes = [IsAuthenticated]

    def put(self, request):
        result = LeaveBL().deabit_leaves(request)
        return Response(result)



######### MOBILE API's


class CreateLeaveRequest_V1(APIView):
    authentication_classes = [JSONWebTokenAuthentication]
    permission_classes = [IsAuthenticated]

    def post(self, request):
        if request.data.get("duration"):
            request.data.update({"leave_day_type":str(request.data.get("duration"))})
        request.data.update({"request_id":request.data.get("leave_request_id",0)})
        request.data.update({"type_id":request.data.get("leave_type_id",0)})
        request.data.update({"notify": LeaveBL_V1().format_notfy_list(request.data.get("notify_person_ids", None))})
        if request.data.get("request_id",0):
            leave_validation = LeaveBL().update_leave_request(request, request.user)
        else:
            leave_validation = LeaveBL().create_leave_request(request, request.user, 1)
        result = LeaveBL_V1().format_leave_request_response(leave_validation)
        return Response(result, status = leave_validation.get("status_code", 200))

class UserLeaveSummaryView_V1(APIView):
    authentication_classes = [JSONWebTokenAuthentication]
    permission_classes = [IsAuthenticated]

    def get(self, request, page=None):
        """ /<page>/, or the bare URL with optional ?page=&emp_id= (default page 1, yourself). """
        params = request.query_params
        result = LeaveBL_V1().get_my_leave_requests(
            request.user.id, page if page is not None else params.get('page', 1), params.get('emp_id'))
        return Response(result, status = result.get("status", 200))

class LeaveStatusUpdateView_V1(APIView):
    authentication_classes = [JSONWebTokenAuthentication]
    permission_classes = [IsAuthenticated]

    def post(self, request):
        data = LeaveBL_V1().format_cancel_leave_request(request.data, 1)
        result = LeaveBL().update_leave_status(data, request.user)
        if result.get("error"):
            result = {"error": result.get("error"), "status": result.get("status", 200)}
        elif result.get("success"):
            result = {"message":result.get("success")}
        return Response(result, status= result.get("status", 200))

class TeamLeaveSummaryView_V1(APIView):
    authentication_classes = [JSONWebTokenAuthentication]
    permission_classes = [IsAuthenticated]

    def get(self, request, page=None, status=None, includeOnlyDirectReporting=None):
        """ /<page>/<status>/<includeOnlyDirectReporting>/, or the bare URL with optional
        ?page=&status=&direct= (defaults: 1, pending, false). """
        params = request.query_params
        result = LeaveBL_V1().get_team_leave_requests(
            request.user.id, page if page is not None else params.get('page', 1),
            status or params.get('status', 'pending'), includeOnlyDirectReporting or params.get('direct', 'false'))
        return Response(result, status = result.get("status", 200))

class LeaveDateValidation_V1(APIView):
    authentication_classes = [JSONWebTokenAuthentication]
    permission_classes = [IsAuthenticated]

    def get(self, request, start_date, end_date):
        data = LeaveBL_V1().format_date_validation(start_date, end_date)
        leave_validation = LeaveBL_V1().leave_date_validation(data, request.user.id)
        return Response(leave_validation, status = leave_validation.get("status", 200))

class LeaveCancelView_V1(APIView):
    authentication_classes = [JSONWebTokenAuthentication]
    permission_classes = [IsAuthenticated]

    def post(self, request):
        data = LeaveBL_V1().format_cancel_leave_request(request.data)
        if not data:
            return Response({ "error": "An error occurred. Please try again."}, status= 499 )
        result = LeaveBL().update_leave_status(data, request.user)
        if result.get("error"):
            result = {"error": result.get("error"), "status": result.get("status", 200)}
        elif result.get("success"):
            result = {"message":result.get("success")}
        return Response(result, status = result.get("status", 200))

class UserLeaveSummaryViewByEmpID_V1(APIView):
    authentication_classes = [JSONWebTokenAuthentication]
    permission_classes = [IsAuthenticated]

    def get(self, request, page, emp_id):
        result = LeaveBL_V1().get_my_leave_requests(request.user.id, page, emp_id)
        return Response(result, status = result.get("status", 200))

class GetUserLeaveSummaryByEmpID_V1(APIView):
    authentication_classes = [JSONWebTokenAuthentication]
    permission_classes = [IsAuthenticated]

    def get(self, request, emp_id=None):
        """ /<emp_id>/, or the bare URL (optionally ?emp_id=) for your own summary. """
        emp_id = emp_id or request.query_params.get('emp_id')
        result = LeaveBL_V1().get_user_leave_summary_by_emp_id(request.user.id, emp_id)
        return Response(result, status = result.get("status", 200))


class VersionExpiredView(APIView):
    authentication_classes = [JSONWebTokenAuthentication]
    permission_classes = [IsAuthenticated]
    parser_classes = (MultiPartParser,FormParser,JSONParser)


    def post(self,*args, **kwargs):
        response ={"error": "This version of the app is obsolete. Please update.", "status": 426}
        return Response(response, status = response.get("status", 200))

    def get(self,*args, **kwargs):
        response ={"error": "This version of the app is obsolete. Please update.", "status": 426}
        return Response(response, status = response.get("status", 200))


class LeaveTypeListView(APIView):
    """ GET: the active company's leave types. POST: add one (leave.manage_all). """
    authentication_classes = [JSONWebTokenAuthentication]
    permission_classes = [IsAuthenticated]

    def get(self, request):
        res = LeaveTypeBL().list(request.user.id)
        return Response(res, status=res.get('status', 200))

    def post(self, request):
        res = LeaveTypeBL().create(request.user.id, request.data)
        return Response(res, status=res.get('status', 201))


class LeaveTypeDetailView(APIView):
    """ PUT: edit one of the active company's leave types. DELETE: remove it (leave.manage_all). """
    authentication_classes = [JSONWebTokenAuthentication]
    permission_classes = [IsAuthenticated]

    def put(self, request, row_id):
        res = LeaveTypeBL().update(request.user.id, row_id, request.data)
        return Response(res, status=res.get('status', 200))

    def delete(self, request, row_id):
        res = LeaveTypeBL().delete(request.user.id, row_id)
        return Response(res, status=res.get('status', 200))
