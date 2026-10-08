from datetime import date

from rest_framework.permissions import IsAuthenticated
from rest_framework.response import Response
from rest_framework.views import APIView
from rest_framework_simplejwt.authentication import JWTAuthentication as JSONWebTokenAuthentication
from rest_framework.parsers import MultiPartParser, FormParser, JSONParser

from pTracker.api.attendance.attendance_biz import AttendanceBL
from pTracker.api.attendance.mapping_biz import UserMappingBL
from pTracker.api.attendance.remote_punch_biz import RemotePunchBL
from pTracker.api.attendance.monthly_attendance_biz import MonthlyAttendanceBL
from pTracker.api.attendance.team_stats_biz import TeamStatsBL
from pTracker.api.attendance.wfh_biz import WorkFromHomeBL
from pTracker.api.attendance.wfh_biz_v1 import WorkFromHomeBL_V1

from pTracker.api.attendance.today_attendance_biz import TodayAttendanceBL
from pTracker.api.attendance.attendance_report_biz import AttendanceReportBL



class MyRecordList(APIView):
    authentication_classes = [JSONWebTokenAuthentication]
    permission_classes = [IsAuthenticated]


    def get(self, request, month_year):
        params = month_year.split("_")
        if len(params) != 2:
            return Response({"error": "Invalid date"}, status=400)
        result = MonthlyAttendanceBL().get_month(request.user.id, params[1], params[0])
        if result.get('error'):
            return Response({"error": result['error']}, status=result['status'])
        return Response(result['attendance'])


class LeadMappingList(APIView):
    authentication_classes = [JSONWebTokenAuthentication]
    permission_classes = [IsAuthenticated]

    def get(self, request):
        team_list = UserMappingBL().get_mapping_list(request.user.id)
        return Response(team_list)


class EmployeeAttendanceLogList(APIView):
    authentication_classes = [JSONWebTokenAuthentication]
    permission_classes = [IsAuthenticated]


    def get(self, request, month_year_empid):
        params = month_year_empid.split("_")
        if len(params) != 3:
            return Response({"error": "Invalid date"}, status=400)
        result = MonthlyAttendanceBL().get_month(request.user.id, params[1], params[0], params[2])
        if result.get('error'):
            return Response({"error": result['error']}, status=result['status'])
        return Response(result['attendance'])

class EmployeeAttendanceAverage(APIView):
    authentication_classes = [JSONWebTokenAuthentication]
    permission_classes = [IsAuthenticated]


    def get(self, request, month_year_empid):

        params = month_year_empid.split("_")
        month = int(params[0])
        year = int(params[1])
        emp_id = int(params[2])
        if month > 12 :
            return Response({"error": "Invalid date"})

        emp_code = UserMappingBL().get_employee_code(emp_id)
        if UserMappingBL().is_employee_accessible(emp_id, request.user.id):
            time_sheet = AttendanceBL().get_emp_attendance_average(emp_id, emp_code, month, year)
            return Response(time_sheet)
        else:
            return Response({"error": "You have no permission to review!"})

class WebPunchCheck(APIView):
    authentication_classes = [JSONWebTokenAuthentication]
    permission_classes = [IsAuthenticated]

    def get(self, request):
        result = RemotePunchBL().punch_check(request.user.id)
        if result.get('error'):
            return Response(result, status=result['status'])
        return Response({'direction': result['direction'], 'is_display': result['is_display']})

class WebPunch(APIView):
    authentication_classes = [JSONWebTokenAuthentication]
    permission_classes = [IsAuthenticated]


    def put(self, request, format=None):
        result = RemotePunchBL().punch(request.user.id, request.data.get('direction'),
                                       request.data.get('channel', 'web'))
        return Response({'error': result.get('error', ''), 'success': result.get('message', ''),
                         'status': result['status']}, status=result['status'])

class UpcomingHolidays(APIView):
    authentication_classes = [JSONWebTokenAuthentication]
    permission_classes = [IsAuthenticated]

    def get(self, request):
        result = AttendanceBL().get_all_upcoming_holidays()
        return Response(result)

class WFHEmp(APIView):
    authentication_classes = [JSONWebTokenAuthentication]
    permission_classes = [IsAuthenticated]

    def get(self, request, work_date):
        return Response(AttendanceBL().get_wfh_employees(request.user.id, work_date))


class DashboardAverageHours(APIView):
    authentication_classes = [JSONWebTokenAuthentication]
    permission_classes = [IsAuthenticated]

    def get(self, request):
        return Response(AttendanceBL().get_dashboard_attendance_average(request.user.id))


class EmployeeWFHRequestListView(APIView):
    authentication_classes = [JSONWebTokenAuthentication]
    permission_classes = [IsAuthenticated]

    def get(self, request):
        from datetime import datetime
        try:
            status_filter = request.GET['status']
        except:
            status_filter = 0
        try:
            month = request.GET['month']
        except:
            month = datetime.now().month
        try:
            year = request.GET['year']
        except:
            year = datetime.now().year

        wfh_requests = WorkFromHomeBL().get_all_wfh_request_by_month_and_status_filter(request.user.id,status_filter,month,year)
        return Response(wfh_requests)


class CreateWFHRequestView(APIView):
    authentication_classes = [JSONWebTokenAuthentication]
    permission_classes = [IsAuthenticated]

    def put(self, request, format=None):
        #emp_code = UserMappingBL().get_employee_code(request.user.id)
        result = WorkFromHomeBL().create_wfh_request(request.data, request.user.id)
        return Response(result)

class UpdateWFHRequestView(APIView):
    authentication_classes = [JSONWebTokenAuthentication]
    permission_classes = [IsAuthenticated]

    def put(self, request, format=None):
        result = WorkFromHomeBL().update_wfh_request(request.data, request.user)
        return Response(result)

class AttendanceDetailView(APIView):
    authentication_classes = [JSONWebTokenAuthentication]
    permission_classes = [IsAuthenticated]

    def get(self, request):
        att_date = request.GET.get("att_date")
        wfh_requests = AttendanceBL().get_attendance_details_by_date(att_date, request.user.id)
        return Response(wfh_requests)

class NotPunchListView(APIView):
    authentication_classes = [JSONWebTokenAuthentication]
    permission_classes = [IsAuthenticated]

    def get(self, request, start_date, end_date):
        result = AttendanceBL().get_not_punched_employee_list(start_date, end_date, request.user.id)
        return Response(result)

class WFHDateValidation(APIView):
    authentication_classes = [JSONWebTokenAuthentication]
    permission_classes = [IsAuthenticated]

    def get(self, request):
        dropdowns = WorkFromHomeBL().wfh_date_validation(request.GET['start_date'],request.GET['end_date'],request.user.id,request.GET['edit_id'])
        return Response(dropdowns)


class WFHRequestFilterByStatus(APIView):
    authentication_classes = [JSONWebTokenAuthentication]
    permission_classes = [IsAuthenticated]

    def get(self, request):
        dropdowns = WorkFromHomeBL().get_filtered_team_wfh_requests(request.user.id,request.GET['status'],request.GET['month'],request.GET['year'])
        return Response(dropdowns)

class WFHMyRequestFilterByStatusAndMonth(APIView):
    authentication_classes = [JSONWebTokenAuthentication]
    permission_classes = [IsAuthenticated]

    def get(self, request):
        dropdowns = WorkFromHomeBL().get_filtered_my_wfh_requests(request.user.id,request.GET['status'],request.GET['month'],request.GET['year'])
        return Response(dropdowns)




########## MOBILE API'S  ##############

from pTracker.api.attendance.wfh_biz_v1 import WorkFromHomeBL_V1

class MyWFHRequestListView_V1(APIView):
    authentication_classes = [JSONWebTokenAuthentication]
    permission_classes = [IsAuthenticated]

    def get(self, request, page):
        wfh_requests = WorkFromHomeBL_V1().get_all_my_wfh_requests(request.user.id, page=page)
        return Response(wfh_requests, status = wfh_requests.get('status', 200))

class TeamWFHRequestListView_V1(APIView):
    authentication_classes = [JSONWebTokenAuthentication]
    permission_classes = [IsAuthenticated]

    def get(self, request, page=None, status=None, includeOnlyDirectReporting=None):
        """ /<page>/<status>/<includeOnlyDirectReporting>/, or the bare URL with optional
        ?page=&status=&direct= (defaults: 1, pending, false). """
        params = request.query_params
        wfh_requests = WorkFromHomeBL_V1().get_team_wfh_requests(
            request.user.id, page if page is not None else params.get('page', 1),
            status or params.get('status', 'pending'), includeOnlyDirectReporting or params.get('direct', 'false'))
        return Response(wfh_requests, status = wfh_requests.get('status', 200))

class WebPunch_V1(APIView):
    authentication_classes = [JSONWebTokenAuthentication]
    permission_classes = [IsAuthenticated]

    def post(self, request, format=None):
        result = RemotePunchBL().punch(request.user.id, request.data.get('direction'),
                                       request.data.get('channel', 'mobile'))
        if result.get('error'):
            return Response({'error': result['error'], 'status': result['status']}, status=result['status'])
        return Response({'message': result['message']})

class WebPunchCheck_V1(APIView):
    authentication_classes = [JSONWebTokenAuthentication]
    permission_classes = [IsAuthenticated]

    def get(self, request):
        result = RemotePunchBL().punch_check(request.user.id)
        if result.get('error'):
            return Response(result, status=result['status'])
        return Response({'direction': result['direction'].lower(), 'is_display': result['is_display']})

class CreateWFHRequestView_V1(APIView):
    authentication_classes = [JSONWebTokenAuthentication]
    permission_classes = [IsAuthenticated]

    def post(self, request, format=None):
        if request.data.get("wfh_id",0):
            request.data.update({"req_type": "EDIT"})
            result = WorkFromHomeBL().update_wfh_request(request.data, request.user)
        else:
            result = WorkFromHomeBL().create_wfh_request(request.data, request.user.id, 1)
        if result.get("error"):
            result = {"error": result.get("error"), "status": result.get("status", 200)}
        elif result.get("success"):
            result = {"message": result.get("success")}
        return Response(result,status = result.get("status", 200))

class UpdateWFHRequestView_V1(APIView):
    authentication_classes = [JSONWebTokenAuthentication]
    permission_classes = [IsAuthenticated]

    def post(self, request, format=None):
        wfh_data = WorkFromHomeBL_V1().format_wfh_update(request.data)
        result = WorkFromHomeBL().update_wfh_request(wfh_data, request.user, 1)
        status = result.get("status", 200)
        if result.get("error"):
            result = {"error": result.get("error")}
        elif result.get("success"):
            result = {"message": result.get("success")}
        return Response(result, status= status)

class CancelWFHRequestView_V1(APIView):
    authentication_classes = [JSONWebTokenAuthentication]
    permission_classes = [IsAuthenticated]

    def post(self, request, format=None):
        wfh_data = WorkFromHomeBL_V1().format_wfh_update(request.data, type="cancel")
        result = WorkFromHomeBL().update_wfh_request(wfh_data, request.user)
        if result.get("error"):
            result = {"error": result.get("error"), "status": result.get("status", 200)}
        elif result.get("success"):
            result = {"message": result.get("success")}
        return Response(result, status = result.get("status", 200))

class MyRecordList_V1(APIView):
    authentication_classes = [JSONWebTokenAuthentication]
    permission_classes = [IsAuthenticated]

    def get(self, request, year=None, month=None, emp_id=None):
        """ Path form /<year>/<month>/<emp_id>/, or the bare URL with optional
        ?year=&month=&emp_id= (defaults: this month, the caller). """
        today = date.today()
        year = year or request.query_params.get('year') or today.year
        month = month or request.query_params.get('month') or today.month
        emp_id = emp_id or request.query_params.get('emp_id') or request.user.id
        result = MonthlyAttendanceBL().get_month(request.user.id, year, month, emp_id)
        return Response(result, status=result['status'])

class GetWorkHours_V1(APIView):
    authentication_classes = [JSONWebTokenAuthentication]
    permission_classes = [IsAuthenticated]

    def get(self, request, date, emp_id):

        result = WorkFromHomeBL_V1().get_work_hours_by_date(date, emp_id)
        return Response(result, status = result.get("status", 200))

class GetTeamStatsView_V1(APIView):
    authentication_classes = [JSONWebTokenAuthentication]
    permission_classes = [IsAuthenticated]

    def get(self, request, date=None, page=None, filterByType=None):
        """ /<date>/<page>/<filterByType>/, or the bare URL with optional
        ?date=&page=&filter=&keyword= (defaults: today, page 1, ALL). """
        params = request.query_params
        dash_info = TeamStatsBL().get_team_stats(
            request.user.id, date or params.get('date'), page or params.get('page', 1),
            filterByType or params.get('filter', 'ALL'), params.get('keyword'))
        return Response(dash_info, status=dash_info.get('status', 200))

class GetTeamStatsViewbyKeyword_V1(APIView):
    authentication_classes = [JSONWebTokenAuthentication]
    permission_classes = [IsAuthenticated]

    def get(self, request, date, page,  filterByType, searchKeyword):
        dash_info = TeamStatsBL().get_team_stats(request.user.id, date, page, filterByType, searchKeyword)
        return Response(dash_info, status=dash_info.get('status', 200))

class WFHRequestListViewByEmpId_V1(APIView):
    authentication_classes = [JSONWebTokenAuthentication]
    permission_classes = [IsAuthenticated]

    def get(self, request, page, emp_id):
        wfh_requests = WorkFromHomeBL_V1().get_all_my_wfh_requests(request.user.id, page=page, emp_id = emp_id)
        return Response(wfh_requests, status = wfh_requests.get('status', 200))


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

class GetAttendanceReport(APIView):
    authentication_classes = [JSONWebTokenAuthentication]
    permission_classes = [IsAuthenticated]

    def get(self,request, str_date, organization):
        response = AttendanceReportBL().get_employee_attendence_report(request, str_date, organization)
        return Response(response, status = response.get("status", 200))

class GetMonthlyAttendanceReport(APIView):
    authentication_classes = [JSONWebTokenAuthentication]
    permission_classes = [IsAuthenticated]

    def get(self,request, year, month, organization):
        response = AttendanceReportBL().generate_monthly_att_report_v1(request, int(month), int(year), int(organization))
        # response = AttendanceReportBL().generate_monthly_att_report(request, month, year, organization)
        return Response(response, status = response.get("status", 200))

class GenerateExcelReport(APIView):
    authentication_classes = [JSONWebTokenAuthentication]
    permission_classes = [IsAuthenticated]

    def get(self,request, year, month, organization):
        response = AttendanceReportBL().generate_monthly_excel_att_report(request, int(month), int(year), int(organization))
        return response



class AnuualWFHDetailView(APIView):
    authentication_classes = [JSONWebTokenAuthentication]
    permission_classes = [IsAuthenticated]

    def get(self, request, emp_id, year):
        result = WorkFromHomeBL_V1().get_annual_wfh_analytics_report(request.user.id, year, emp_id)
        return Response(result)



class WFHReportDropDowns(APIView):
    authentication_classes = [JSONWebTokenAuthentication]
    permission_classes = [IsAuthenticated]

    def get(self, request):
        dropdowns = WorkFromHomeBL_V1().wfh_report_dropdowns(request.user, request.GET)
        return Response(dropdowns)

class GetWorkFromHomeReport(APIView):
    authentication_classes = [JSONWebTokenAuthentication]
    permission_classes = [IsAuthenticated]

    def get(self, request):

        result = WorkFromHomeBL_V1().get_wfh_summary_report(request)
        return Response(result, status = result.get("status", 200))


class GetWorkFromHomeEmployee(APIView):
    authentication_classes = [JSONWebTokenAuthentication]
    permission_classes = [IsAuthenticated]

    def get(self, request):
        response = WorkFromHomeBL_V1().employee_wfh_list(request)
        return Response(response)


class AnnualWFHSummaryReport(APIView):
    authentication_classes = [JSONWebTokenAuthentication]
    permission_classes = [IsAuthenticated]

    def get(self, request):
        dropdowns = WorkFromHomeBL_V1().get_annual_wfh_detail_report(request.user.id,request.GET)
        return Response(dropdowns)
