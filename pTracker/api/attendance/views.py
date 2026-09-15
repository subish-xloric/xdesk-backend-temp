from rest_framework.permissions import IsAuthenticated
from rest_framework.response import Response
from rest_framework.views import APIView
from rest_framework_simplejwt.authentication import JWTAuthentication as JSONWebTokenAuthentication
from rest_framework.parsers import MultiPartParser, FormParser, JSONParser

from pTracker.api.attendance.attendance_biz import AttendanceBL
from pTracker.api.attendance.mapping_biz import UserMappingBL
from pTracker.api.attendance.wfh_biz import WorkFromHomeBL
from pTracker.api.attendance.wfh_biz_v1 import WorkFromHomeBL_V1

from pTracker.api.attendance.today_attendance_biz import TodayAttendanceBL
from pTracker.api.attendance.attendance_biz_v1 import AttendanceBL_V1
from pTracker.api.attendance.attendance_report_biz import AttendanceReportBL



class MyRecordList(APIView):
    authentication_classes = [JSONWebTokenAuthentication]
    permission_classes = [IsAuthenticated]


    def get(self, request, month_year):

        month_year = month_year.split("_")
        month = int(month_year[0])
        year = int(month_year[1])
        if month > 12 :
            return Response({"error": "Invalid date"})

        time_sheet = AttendanceBL().get_emp_attendance_log(request.user.id, request.user.username, month, year)
        return Response(time_sheet)


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
        month = int(params[0])
        year = int(params[1])
        emp_id = int(params[2])
        if month > 12 :
            return Response({"error": "Invalid date"})

        emp_code = UserMappingBL().get_employee_code(emp_id)
        if UserMappingBL().is_employee_accessible(emp_id, request.user.id):
            time_sheet = AttendanceBL().get_emp_attendance_log(emp_id, emp_code, month, year)
            return Response(time_sheet)
        else:
            return Response({"error": "No records found !"})

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
        emp_code = UserMappingBL().get_employee_code(request.user.id)
        result = AttendanceBL().get_web_punch_check(emp_code)
        return Response(result)

class WebPunch(APIView):
    authentication_classes = [JSONWebTokenAuthentication]
    permission_classes = [IsAuthenticated]


    def put(self, request, format=None):
        emp_code = UserMappingBL().get_employee_code(request.user.id)
        result = AttendanceBL().create_web_punch(emp_code, request.data)
        return Response(result)

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

    def get(self, request, page, status, includeOnlyDirectReporting):
        wfh_requests = WorkFromHomeBL_V1().get_all_my_wfh_requests(request.user.id, team=1, page=page, status=status, include_only_direct_reporting = includeOnlyDirectReporting)
        return Response(wfh_requests, status = wfh_requests.get('status', 200))

class WebPunch_V1(APIView):
    authentication_classes = [JSONWebTokenAuthentication]
    permission_classes = [IsAuthenticated]

    def post(self, request, format=None):
        emp_code = UserMappingBL().get_employee_code(request.user.id)
        data = WorkFromHomeBL_V1().format_web_punch_data(request.data)
        result = AttendanceBL().create_web_punch(emp_code, data)
        if result.get("error"):
            result = {"error": result.get("error"), "status": 499}
        elif result.get("success"):
            result = {"message":result.get("success")}
        return Response(result, status= result.get("status", 200))

class WebPunchCheck_V1(APIView):
    authentication_classes = [JSONWebTokenAuthentication]
    permission_classes = [IsAuthenticated]

    def get(self, request):
        res = {'direction':'', 'is_display': True}
        emp_code = UserMappingBL().get_employee_code(request.user.id)
        result = AttendanceBL().get_web_punch_check(emp_code)
        direction = result.get('direction', None)
        if str(direction).lower() == 'in':
            res['direction'] = 'in'
        elif str(direction).lower() == 'out':
            res['direction'] = 'out'

        is_display = result.get('is_display', True)
        if str(is_display).lower() == 'true':
            res['is_display'] = True
        else:
            res['is_display'] = False
        return Response(res, status = result.get("status", 200))

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

    def get(self, request, year, month, emp_id):
        emp_code = WorkFromHomeBL_V1().get_emp_code_by_emp_id(emp_id)
        result = AttendanceBL().get_emp_attendance_log(request.user.id, emp_code, month, year)
        attendance = WorkFromHomeBL_V1().format_my_attendance_record(result)
        return Response(attendance, status = attendance.get("status", 200))

class GetWorkHours_V1(APIView):
    authentication_classes = [JSONWebTokenAuthentication]
    permission_classes = [IsAuthenticated]

    def get(self, request, date, emp_id):

        result = WorkFromHomeBL_V1().get_work_hours_by_date(date, emp_id)
        return Response(result, status = result.get("status", 200))

class GetTeamStatsView_V1(APIView):
    authentication_classes = [JSONWebTokenAuthentication]
    permission_classes = [IsAuthenticated]

    def get(self, request, date, page, filterByType):
        dash_info = AttendanceBL_V1().get_team_stats(request.user.id, date, page, filterByType)
        return Response(dash_info, status=dash_info.get('status', 200))

class GetTeamStatsViewbyKeyword_V1(APIView):
    authentication_classes = [JSONWebTokenAuthentication]
    permission_classes = [IsAuthenticated]

    def get(self, request, date, page,  filterByType, searchKeyword):
        dash_info = AttendanceBL_V1().get_team_stats(request.user.id, date, page,filterByType, searchKeyword)
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
