from rest_framework.authentication import SessionAuthentication, BasicAuthentication
from rest_framework_simplejwt.authentication import JWTAuthentication as JSONWebTokenAuthentication
from rest_framework.permissions import IsAuthenticated
from rest_framework.response import Response
from rest_framework.views import APIView
from rest_framework.parsers import MultiPartParser, FormParser, JSONParser


from pTracker.api.timesheet.timesheet_biz import TimeSheetBL
from pTracker.api.timesheet.timesheet_report_biz import TimesheetReportBL
from pTracker.api.timesheet.timesheet_biz_v1 import TimeSheetBL_V1

from pTracker.api.timesheet.timesheet_archive_biz import ArchiveTimeSheetBL

class TimeSheetList(APIView):
    authentication_classes = [JSONWebTokenAuthentication]
    permission_classes = [IsAuthenticated]

    def get(self, request):
        projects = TimeSheetBL().get_all_time_sheet_by_user(request.user.id)
        return Response(projects)

class TimeSheetDateValid(APIView):
    authentication_classes = [JSONWebTokenAuthentication]
    permission_classes = [IsAuthenticated]

    def get(self, request, time_sheet_date, time_sheet_id=0):
        result = TimeSheetBL().is_timesheet_date_valid(request.user.id, time_sheet_date, time_sheet_id)
        return Response(result)


class TimeSheetDetail(APIView):
    authentication_classes = [JSONWebTokenAuthentication]
    permission_classes = [IsAuthenticated]
    parser_classes = [JSONParser]

    def get(self, request, time_sheet_id):
        time_sheet = TimeSheetBL().get_time_sheet_detail_by_id(time_sheet_id, request.user.id)
        return Response(time_sheet)

    def put(self, request, format=None):
        result  = TimeSheetBL().create_or_update_time_sheet(request.data, request.user.id)
        return Response(result)

class EmployeeTimeSheetDetail(APIView):
    authentication_classes = [JSONWebTokenAuthentication]
    permission_classes = [IsAuthenticated]
    parser_classes = [JSONParser]
    def get(self, request, time_sheet_id, emp_id):
        time_sheet = TimeSheetBL().get_employee_time_sheet_detail_by_id(time_sheet_id, emp_id, request.user.id)
        return Response(time_sheet)


class MyTimeSheetList(APIView):
    authentication_classes = [JSONWebTokenAuthentication]
    permission_classes = [IsAuthenticated]

    def get(self, request, start_date, end_date, status):
        time_sheets = TimeSheetBL().\
            get_time_sheets_by_date_range(request.user.id, start_date, end_date, status)
        return Response(time_sheets)

class TeamTimeSheetList(APIView):
    authentication_classes = [JSONWebTokenAuthentication]
    permission_classes = [IsAuthenticated]

    def get(self, request, emp_id, start_date, end_date, status):
        time_sheets = TimeSheetBL().\
            get_time_sheets_by_date_range(emp_id, start_date, end_date, status, request.user.id)
        return Response(time_sheets)

class TimeSheetApprove(APIView):
    authentication_classes = [JSONWebTokenAuthentication]
    permission_classes = [IsAuthenticated]


    def put(self, request, format=None):
        result = TimeSheetBL().approve_time_sheet(request.data, request.user.id)
        return Response(result)

class TimesheetSummary(APIView):
    authentication_classes = [JSONWebTokenAuthentication]
    permission_classes = [IsAuthenticated]

    def get(self,request,start_date, end_date):
        result = TimesheetReportBL().get_timesheet_summary(request.user.id, start_date, end_date)
        return Response(result)

class TimesheetDetailByEmployee(APIView):
    authentication_classes = [JSONWebTokenAuthentication]
    permission_classes = [IsAuthenticated]

    def get(self,request,emp_id, start_date, end_date):
        try:
            result = TimesheetReportBL().get_time_sheet_detail_by_employee(emp_id, start_date, end_date, request.user.id)
            return Response(result)
        except Exception as error:
            return [{"error": str(error)}]

class TimesheetDPU(APIView):
    authentication_classes = [JSONWebTokenAuthentication]
    permission_classes = [IsAuthenticated]

    def get(self,request,start_date, project_id):
        user_name = request.user.first_name + " "  + request.user.last_name
        result = TimesheetReportBL().get_time_sheet_dpu(start_date, project_id, request.user.id, user_name)
        return Response(result)

class TimesheetMissingAlert(APIView):
    authentication_classes = [JSONWebTokenAuthentication]
    permission_classes = [IsAuthenticated]

    def get(self,request):
        result = TimeSheetBL_V1().get_timesheet_missing_alert( request.user.id)
        return Response(result)

class ExcludeTsEmployees(APIView):
    authentication_classes = [JSONWebTokenAuthentication]
    permission_classes = [IsAuthenticated]
    parser_classes = (MultiPartParser,FormParser,JSONParser)

    def put(self,request):
        result = TimeSheetBL_V1().create_exclude_ts_employee(request)
        return Response(result)



############ MOBILE API ##################

import calendar

class MyTimeSheetList_V1(APIView):
    authentication_classes = [JSONWebTokenAuthentication]
    permission_classes = [IsAuthenticated]

    def get(self, request, year, month):
        start_date, end_date = TimeSheetBL_V1().get_last_and_first_date(year, month)
        time_sheets = TimeSheetBL().\
            get_time_sheets_by_date_range(request.user.id, start_date, end_date)
        result = TimeSheetBL_V1().format_my_timesheet_list(time_sheets)
        return Response(result, status = result.get("status", 200))

class TeamTimeSheetList_V1(APIView):
    authentication_classes = [JSONWebTokenAuthentication]
    permission_classes = [IsAuthenticated]

    def get(self, request, emp_id, year, month):
        start_date, end_date = TimeSheetBL_V1().get_last_and_first_date(year, month)
        if request.user.id != emp_id:
            time_sheets = TimeSheetBL().\
                get_time_sheets_by_date_range(emp_id, start_date, end_date, 0, request.user.id)
        else:
            time_sheets = TimeSheetBL().\
                get_time_sheets_by_date_range(emp_id, start_date, end_date, 0, 0)
        result = TimeSheetBL_V1().format_my_timesheet_list(time_sheets)
        return Response(result, status= result.get("status", 200))

class TimeSheetDetail_V1(APIView):
    authentication_classes = [JSONWebTokenAuthentication]
    permission_classes = [IsAuthenticated]
    parser_classes = [JSONParser]

    def get(self, request, timesheet_id):
        # time_sheet = TimeSheetBL().get_time_sheet_detail_by_id(timesheet_id, request.user.id)
        time_sheet=TimeSheetBL_V1().get_time_sheet_detail_by_id(timesheet_id)
        time_sheet=TimeSheetBL_V1().format_timesheet_details(time_sheet)
        return Response(time_sheet, status = time_sheet.get("status_code", 200))

    def post(self, request, format=None):
        data = TimeSheetBL_V1().format_add_or_edit_timesheet(request)
        result  = TimeSheetBL().create_or_update_time_sheet(data, request.user.id)
        if result[0].get("error"):
            result = {"error": result[0].get("error"), "status": result[0].get("status", 200) }
        elif result[0].get("success"):
            result = {"message":result[0].get("success")}
        return Response(result, status = result.get("status", 200))

class TimeSheetList_V1(APIView):
    authentication_classes = [JSONWebTokenAuthentication]
    permission_classes = [IsAuthenticated]

    def get(self, request):
        projects = TimeSheetBL().get_all_time_sheet_by_user(request.user.id)
        result = TimeSheetBL_V1().format_my_timesheet_list(projects)
        return Response(result, status = result.get("status", 200))

class TimeSheetDateValid_V1(APIView):
    authentication_classes = [JSONWebTokenAuthentication]
    permission_classes = [IsAuthenticated]

    def get(self, request, date, time_sheet_id=0):
        result = TimeSheetBL().is_timesheet_date_valid(request.user.id, date, time_sheet_id)
        return Response(result, status = result.get("status", 200))

class TimeSheetApprove_V1(APIView):
    authentication_classes = [JSONWebTokenAuthentication]
    permission_classes = [IsAuthenticated]

    def post(self, request, format=None):
        data = TimeSheetBL_V1().format_approve_time_sheet(request.data)
        result = TimeSheetBL().approve_time_sheet(data, request.user.id)
        if result[0].get("error"):
            result = {"error": result[0].get("error"), "status": result[0].get("status", 200)}
        elif result[0].get("success"):
            result = {"message":result[0].get("success")}
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

class CreateTimesheetArchive(APIView):
    authentication_classes = [JSONWebTokenAuthentication]
    permission_classes = [IsAuthenticated]
    ArchiveTimeSheetBL = ArchiveTimeSheetBL()

    def post(self, request):
        response = ArchiveTimeSheetBL().create_timesheet_archive(request.user.id, request.data)
        return Response(response)

class TimesheetArchiveList(APIView):
    authentication_classes = [JSONWebTokenAuthentication]
    permission_classes = [IsAuthenticated]

    def get(self,*args, **kwargs):
        result = ArchiveTimeSheetBL().get_all_timesheet_archives()
        return Response(result, status = result.get("status", 200))

class RestoreTimesheetFromArchives(APIView):
    authentication_classes = [JSONWebTokenAuthentication]
    permission_classes = [IsAuthenticated]
    ArchiveTimeSheetBL = ArchiveTimeSheetBL()

    def post(self, request):
        response = ArchiveTimeSheetBL().restore_timesheet_from_archive(request.user.id, request.data)
        return Response(response)


        
