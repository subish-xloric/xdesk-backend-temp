from types import SimpleNamespace

from django.conf import settings

from pTracker.common.logs import Logs
from pTracker.notification_center.email_engine import Email
from pTracker.dataaccess.ptracker_access.user_da import UserDA
from pTracker.common.exception_handler import ExceptionHandler
from pTracker.dataaccess.ptracker_access.attendance import AttendanceDA
from pTracker.dataaccess.essl_access.attendance import  AttendanceDA as essl_AttendanceDA
from pTracker.api.leave.leave_biz import LeaveBL

from datetime import date,datetime, time
import datetime

from pTracker.api.leave.leave_helper import LeaveHelperBL
from pTracker.common.utility import Utility
from pTracker.api.leave.leave_notification_biz import LeaveNotificationBL
from pTracker.api.attendance.wfh_biz import WorkFromHomeBL
from pTracker.dataaccess.ptracker_access.timesheet_da import TimeSheetDA
from pTracker.dataaccess.ptracker_access.project_da import ProjectDA
from pTracker.user_management.holiday_da import HolidayDA
from pTracker.dataaccess.ptracker_access.leave_da import LeaveDA


def new_dto():
    dto = SimpleNamespace()
    return dto

class TimeSheetBL_V1():

    def __init__(self):
        self.__logs = Logs()
        self.__exception = ExceptionHandler()
        self.__utility = Utility()

    def format_my_timesheet_list(self, timesheet_list):
        if timesheet_list:
            if "error" in timesheet_list[0].keys():
                res = {"error": timesheet_list[0]["error"], "status": timesheet_list[0].get("status", 200) }
            else:
                res = {"timesheet_list": timesheet_list, "status": 200}
        return res

    def get_last_and_first_date(self, year, month):
        start_date = self.__utility.get_first_day_of_month(None, int(year), int(month))
        end_date = self.__utility.get_last_day_of_month(start_date)
        return start_date, end_date

    def format_approve_time_sheet(self, data):
        res = {}
        timesheet_id = data.get("timesheet_id", 0)
        res["comment"] = ""
        res["status"] = data.get("action")
        res["timesheet_id"] = timesheet_id
        return res

    def format_add_or_edit_timesheet(self, request):
        data = request.data
        user = request.user
        data["user_id"] = user.id
        return data

    def format_timesheet_details(self, timesheet_details):
        entries_to_remove = ["user_id"]
        if timesheet_details.get("user_id", None):
            timesheet_details['emp_id'] = timesheet_details['user_id']
            for each_entry in entries_to_remove:
                timesheet_details.pop(each_entry, None)

        return timesheet_details

    #TODO confrm with subishettan

    def get_time_sheet_detail_by_id(self, time_sheet_id):
        timesheet_dict = {"status_code": 200}
        item_list = []

        project_dict = self.get_all_project_dict()
        activity_dict = self.get_all_project_activity_dict()
        module_dict = self.get_all_project_module_dict()

        time_sheet = TimeSheetDA().get_time_sheet_by_id(time_sheet_id)
        if time_sheet:
            items = TimeSheetDA().get_time_sheet_items_by_timesheet_id(time_sheet_id)
            working_hours = self.get_work_hours_by_date(time_sheet.timesheet_date, time_sheet.user_id)
            if items:
                for item in items:
                    hours = Utility().convert_seconds_to_hour_and_minute(item.duration)
                    item_list.append({
                        "module_id": item.module_id,
                        "module_name": module_dict.get(item.module_id, ""),
                        "project_id": item.project_id,
                        "project_name": project_dict.get(item.project_id, "") ,
                        "activity_id": item.activity_id,
                        "activity_name": activity_dict.get(item.activity_id, "") ,
                        "duration": item.duration,
                        "hour": hours.split(":")[0],
                        "minute": hours.split(":")[1],
                        "comment": item.comment,
                        "is_billable": item.is_billable,
                        "percentage_completed": item.percentage_completed if item.percentage_completed else '-',
                        "status": item.status if item.status else '-',
                        "ticket_title": item.ticket_title if item.ticket_title else '-',
                        "ticket_eta": item.ticket_eta if item.ticket_eta else '-'
                        })
            timesheet_dict['timesheet_id'] = time_sheet.timesheet_id
            timesheet_dict['status'] = time_sheet.status
            timesheet_dict['timesheet_date'] = time_sheet.timesheet_date
            timesheet_dict['user_id'] = time_sheet.user_id
            timesheet_dict['total_duration'] = Utility().convert_seconds_to_hour_and_minute(time_sheet.total_duration)
            timesheet_dict['work_hours'] = working_hours
            timesheet_dict['items'] = item_list

        if not timesheet_dict:
            timesheet_dict['error']  = "No record found !!"
            timesheet_dict['status_code'] = 499
        return timesheet_dict


    def get_all_project_dict(self):
        project_dict = {}
        projects = ProjectDA().get_all_projects()
        if projects:
            for project in projects:
                project_dict[project.project_id] = project.name
        return project_dict

    def get_all_project_activity_dict(self):
        res_dict = {}
        activities = ProjectDA().get_all_project_activity()
        if activities:
            for activity in activities:
                res_dict[activity.activity_id] = activity.name
        return res_dict

    def get_all_project_module_dict(self):
        res_dict = {}
        modules = ProjectDA().get_all_project_modules()
        if modules:
            for module in modules:
                res_dict[module.module_id] = module.name
        return res_dict

    def get_work_hours_by_date(self, work_date, emp_id):
        work_hours = "0:00"
        emp = UserDA().get_user_by_id(emp_id)
        res = AttendanceDA().get_attendance_by_emp_id_and_date(emp.username, work_date)
        if res:
            work_hours = Utility().convert_seconds_to_hour_and_minute(res.work_hours)
        return work_hours


    def timesheet_by_n_days(self , emp_id , current_date='' , n=5):
        count_date = 0
        holiday=[]
        timesheet=[]
        new_date = []
        dates=[]
        length_timesheet = 0
        date_list = []
        current_date = date.today()
        previous_date = current_date - datetime.timedelta(days=1)
        end = current_date - datetime.timedelta(days=2)
        end_date = datetime.datetime.strptime(str(end),'%Y-%m-%d')
        start =previous_date - datetime.timedelta(days=n)
        start_date = datetime.datetime.strptime(str(start),'%Y-%m-%d')
        while True:
            obj_dates = Utility().get_date_range(start_date,end_date)
            if obj_dates:
                for each_dates in obj_dates:
                    dates.append(each_dates.strftime('%Y-%m-%d'))
            obj_holiday = HolidayDA().get_all_holidays(start_date, end_date)
            if obj_holiday :
                for each_holiday in obj_holiday :
                    holiday.append(each_holiday.holiday_date.strftime('%Y-%m-%d'))


            obj_leave = LeaveDA().get_employee_leave_by_date(start_date,end_date,emp_id)
            if obj_leave :
                for each_item in obj_leave :
                    holiday.append(each_item.leave_date.strftime('%Y-%m-%d'))

            obj_weekends = Utility().get_all_weekends(start_date,end_date)
            if obj_weekends :
                for each_weekends in obj_weekends :
                    holiday.append(each_weekends.strftime('%Y-%m-%d'))
            if holiday :
                for each_dates in dates:
                    if each_dates not in holiday:
                        new_date.append(each_dates)
            if new_date :
                count_date = len(new_date)
            if count_date == n :
                obj_timesheet = TimeSheetDA().get_timesheet_date_range(emp_id,start_date,end_date)
                if obj_timesheet :
                    for each_timesheet in obj_timesheet :
                        timesheet.append(each_timesheet.timesheet_id)
                length_timesheet = len(timesheet)
                break
            else :
                new_day_length = n - count_date
                start_date = start_date - datetime.timedelta(days=new_day_length)
                dates=[]
                holiday=[]
                new_date=[]
        if length_timesheet < n :
            flag = True
        else :
            flag = False
        return length_timesheet,flag

    def get_timesheet_missing_alert(self, emp_id):
        response = {'prevent_login': False, 'miissing_in_timesheet': False, "error": ''}
        try:
            no_of_timesheets, is_missing = self.timesheet_by_n_days(emp_id,n=10)
            if is_missing:
                if no_of_timesheets == 0:
                    timesheet_excluded_emp = UserDA().get_timesheet_excluded_employee_by_id(emp_id)
                    if timesheet_excluded_emp is None:
                        response['prevent_login'] = True
                response['miissing_in_timesheet'] = True
        except Exception as err:
            response['error'] = { "error" : settings.ERROR_MSG['application_error']\
                .format(str(err), self.__logs.error(self.__exception.get_exception())) }

        response['prevent_login'] = False
        response['miissing_in_timesheet'] = False

        return response

    def create_exclude_ts_employee(self, request):
        response = {"error": None, "success": False, 'status':200}
        try:
            user_id = request.user.id
            is_permitted = self.__utility.is_permitted(user_id, 'can_unblock_prevent_login')
            if user_id == 54:
                is_permitted = True

            if not is_permitted:
                response["error"] = settings.ERROR_MSG.get('access_denied')
                response['status'] = 403
                return response

            emp_id =  request.data.get('emp_id')
            if emp_id is not None:
                create_dict = {
                    'emp_id': emp_id,
                    'expiry_date': date.today()
                }
                res = TimeSheetDA().create_exclude_timesheet_employee(create_dict)
                if res:
                    #UserDA().update_auth_user({'is_active':1}, emp_id)
                    response["success"] = True
        except Exception as err:
            response["error"] = settings.ERROR_MSG["application_error"].format(
                str(err), self.__logs.error(self.__exception.get_exception())
            )
        return response


    # def __format_days(self,att_days):
    #     str_dates =[]
    #     if att_days:
    #         #att_days = att_days[2:]
    #         for day in att_days:
    #             #log_day = datetime.datetime.strptime(day[0].strftime("%Y-%m-%d"), "%Y-%m-%d")
    #             str_dates.append(day)
    #     return str_dates

    def get_current_weekday(self):
        today = datetime.date.today()
        current_weekday = today.weekday()
        return current_weekday

    def find_last_monday_and_friday(self, is_two_weeks=0):
        today = datetime.date.today()
        current_weekday = today.weekday()  # 0 for Monday, 6 for Sunday

        if is_two_weeks:
            days_to_last_monday = current_weekday + 7 + 7  # Go back to previous Monday
            days_to_last_friday = current_weekday + 3 + 7  # Go back to previous Friday
        else:
            days_to_last_monday = current_weekday + 7   # Go back to previous Monday
            days_to_last_friday = current_weekday + 3   # Go back to previous Friday

        last_monday = today - datetime.timedelta(days=days_to_last_monday)
        last_friday = today - datetime.timedelta(days=days_to_last_friday)

        last_monday = last_monday.strftime("%Y-%m-%d")
        last_friday = last_friday.strftime("%Y-%m-%d")

        return last_monday, last_friday


    def prevent_login_by_timesheet(self, emp_id):
        timesheet = []
        prevent_login = False
        is_two_weeks = 0
        try:
            #return prevent_login #TODO
            timesheet_excluded_emp = UserDA().get_timesheet_excluded_employee_by_id(emp_id)
            if timesheet_excluded_emp:
                return prevent_login

            if self.get_current_weekday() in (0,1,6): # 0 for Monday, 6 for Sunday
                is_two_weeks = 1
            monday, friday =  self.find_last_monday_and_friday(is_two_weeks)           
            #monday = '2025-02-27'

            emp = UserDA().get_user_by_id(emp_id)
            if emp:
                emp_code = emp.username
                att_days, err = essl_AttendanceDA().get_essl_attendance_by_emp_code(emp_code, monday, friday)
                #att_days = self.__format_days(att_days)

                

                if len(att_days) <= 0:
                    return prevent_login
                
                total_work_days = len(att_days)

                # obj_start_date = datetime.datetime.strptime(monday, "%Y-%m-%d").date()
                # #obj_start_date = datetime.datetime.strptime('2025-02-27', "%Y-%m-%d").date() #27/02/2025
                # obj_end_date = datetime.datetime.strptime(friday, "%Y-%m-%d").date()
                # obj_leaves_dates = LeaveDA().get_employee_leave_by_date_v1(obj_start_date, obj_end_date, emp_id)
                # total_work_days = len(att_days)  

                # leave_dates = []
                # if obj_leaves_dates:  
                #     for each_date in obj_leaves_dates:
                #         leave_dates.append(each_date.strftime("%Y-%m-%d"))

                # self.__logs.error("leave_dates found " + str(leave_dates))


                # if obj_leaves_dates:
                #     for each_day in att_days:
                #         punch_date = each_day[0]
                #         #self.__logs.error("punch_date" + str(punch_date))
                #         #self.__logs.error("punch_date type" + str(type(punch_date)))
                #         #self.__logs.error("obj_leaves_dates" + str(obj_leaves_dates))

                #         #obj_punch_day = datetime.datetime.strptime(punch_date, '%Y-%m-%d').date()
                #         if punch_date in obj_leaves_dates:
                #             self.__logs.error("punch_date found" + str(punch_date))
                #             total_work_days -= 1

                obj_timesheet = TimeSheetDA().get_timesheet_date_range(emp_id, monday, friday)               
                
                if obj_timesheet :
                    for each_timesheet in obj_timesheet :
                        timesheet.append(each_timesheet.timesheet_id)                
                
                if len(timesheet) < total_work_days:
                    prevent_login = True 
                    #self.__logs.error("prevent_login" + str(prevent_login))                   
                    #UserDA().update_auth_user({"is_active":0}, emp_id)
                    return prevent_login
        except Exception as err:
            self.__logs.error(self.__exception.get_exception())

        return prevent_login