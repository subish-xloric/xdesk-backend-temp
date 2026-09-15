from types import SimpleNamespace

from django.conf import settings
from django.db.models import Q

from pTracker.dataaccess.ptracker_access.user_da import UserDA
from pTracker.dataaccess.ptracker_access.attendance import AttendanceDA
from pTracker.dataaccess.ptracker_access.holiday_da import HolidayDA
from pTracker.api.leave.leave_helper import LeaveHelperBL
from pTracker.common.exception_handler import ExceptionHandler
from pTracker.common.logs import Logs
from pTracker.common.utility import Utility

from pTracker.api.attendance.wfh_biz import WorkFromHomeBL
from datetime import date, timedelta, datetime
import calendar

def new_dto():
    dto = SimpleNamespace()
    return dto

class WorkFromHomeBL_V1():

    def __init__(self):
        self.__logs = Logs()
        self.__exception = ExceptionHandler()
        self.__utility = Utility()

    def __exclude_wfh_keys(self, data):
        entries_to_remove = ["emp_name", "emp_id", "created_date" ]
        for k in entries_to_remove:
            data.pop(k, None)
        return data

    def __get_image_url(self, user_id):
        img_url = UserDA().get_user_profile_by_id(user_id)
        if img_url:
            return f"{settings.DEFAULT_SITE_MEDIA_URL}{img_url.profile_photo}"
        else:
            return None


    def get_all_my_wfh_requests(self, user_id, page=1, team=0, status=None, emp_id =0, include_only_direct_reporting = None):
        try:
            direct_reporting =0
            if include_only_direct_reporting:
                if include_only_direct_reporting.upper() == "TRUE":
                    direct_reporting = 1
            min, max = Utility().cutomPageLimits(page)
            response = {"wfh_requests": [], "status": 200}
            if emp_id:
                if(user_id == emp_id):
                    user_id = emp_id
                elif not UserDA().is_team_member(emp_id, user_id):
                    response["error"] = settings.ERROR_MSG['access_denied']
                    response["status"] = 403
                    return response
                user_id = emp_id
            if team:
                if status=="pending":
                    status = [1,] #1 for requested
                elif status=="verified":
                    status = [2, 3, 4] # except requested status
                else:
                    return response
                wfh_requests = WorkFromHomeBL().get_filtered_team_wfh_requests(user_id,status=status,is_mobile=1, direct_reporting = direct_reporting)
            else:
                wfh_requests = WorkFromHomeBL().get_filtered_my_wfh_requests(user_id, is_mobile=1)
            request_list =  wfh_requests['wfh_requests']
            if page:
                request_list =  wfh_requests['wfh_requests'][min:max]
            user_dic = {}
            team_members = UserDA().get_all_active_users()
            for user in team_members:
                user_dic[user.id] = user.first_name + " " + user.last_name
            if team and request_list:
                for row,each in  enumerate(request_list):
                    each["emp_image"] = self.__get_image_url(each.get("emp_id",0))
                    request_list[row] = each
            if not team and request_list:
                for row,each in  enumerate(request_list):
                    request_list[row] = self.__exclude_wfh_keys(each)

            response["wfh_requests"] = request_list
            return response
        except Exception as err:
            response = {}
            response["status"] = 499
            response["error"] = settings.ERROR_MSG['application_error']\
                .format(err, self.__logs.error(self.__exception.get_exception()))
            return response

    def format_wfh_update(self, data, type=""):
        wfh_data = {}
        action = data.get("action", None)
        wfh_id = data.get("wfh_id", 0)
        if action:
            emp_id = AttendanceDA().get_wfh_request_by_id(wfh_id).emp_id
            if action == "APPROVED":
                wfh_data["req_type"] = "APPROVE"
                wfh_data["status"] = 2 #Approve status id
                wfh_data["wfh_id"] = wfh_id
                wfh_data["comment"] = data.get("comment", 0)
                wfh_data["emp_id"] = emp_id
            elif action == "REJECTED":
                wfh_data["req_type"] = "APPROVE"
                wfh_data["status"] = 4 #Reject status id
                wfh_data["wfh_id"] = wfh_id
                wfh_data["comment"] = data.get("comment", 0)
                wfh_data["emp_id"] = emp_id
        if type == "cancel":
            wfh_data["req_type"] = "CANCEL"
            wfh_data["status"] = 3 #cancel status id
            wfh_data["wfh_id"] = wfh_id
            wfh_data["comment"] = data.get("comment", "")
        return wfh_data

    def format_web_punch_data(self, data):
        res = {}
        direction = data.get('direction', None)
        if direction in ("IN", "in"):
            res["direction"] = "in"
        elif direction in ("OUT", "out"):
            res["direction"] = "out"
        return res

    def format_my_attendance_record(self, result):
        if result:
            try:
                if result.get("error"):
                    result = {"error": result.get("error"), "status": result.get("status", 200)}
            except:
                result = {'attendance': result,"status": 200}
        else:
            result = {'attendance': result, "status": 200}
        return result

    def get_emp_code_by_emp_id(self, emp_id):
        emp = UserDA().get_user_by_id(emp_id)
        return emp.username

    def get_work_hours_by_date(self, start_date, emp_id):
        response = {"status": 200}
        try:
            emp_code = self.get_emp_code_by_emp_id(emp_id)
            res = AttendanceDA().get_attendance_by_emp_id_and_date(emp_code, start_date)
            if res:
                response['work_hours'] = res.work_hours
                response['total_hours'] = res.total_hours
            return response
        except Exception as err:
            response = {}
            response['status'] = 499
            response["error"] = settings.ERROR_MSG['application_error']\
                .format(err, self.__logs.error(self.__exception.get_exception()))
            return response


    def get_wfh_summary_report(self, request):
        result = {'error': None, 'leaves': [], 'summary': {}}

        wfh_list = []
        wfh_emp_id_list = []
        role_id=''

        try:
            user_id = request.user.id
            data = request
            role_id, role_name = UserDA().get_user_role_by_id(user_id)
            if role_id not in (1, 2, 3, 4, "1", "2", "3", "4"):
                result["error"] = settings.ERROR_MSG.get('access_denied')
                return result

            helper = LeaveHelperBL()

            emp_id = int(data.GET.get('emp_id', 0))
            startDate = data.GET.get('startDate', 0)
            endDate = data.GET.get('endDate', 0)
            lead_id = int(data.GET.get('lead_id',0))
            obj_start_datetime = Utility().convert_string_to_date_time(startDate, "%Y-%m-%d")
            obj_end_datetime = Utility().convert_string_to_date_time(endDate, "%Y-%m-%d")
            obj_start = obj_start_datetime.date()
            obj_end = obj_end_datetime.date()

            temp_start_date = int(obj_start_datetime.strftime('%d'))
            temp_start_month = int(obj_start_datetime.strftime('%m'))
            temp_start_year = int(obj_start_datetime.strftime('%Y'))

            obj_temp_start_date = None
            obj_temp_end_date = None

            if temp_start_date != 1:
                obj_temp_start_date = Utility().convert_string_to_date_time(str(temp_start_year)+'-'+str(temp_start_month)+'-'+'01', "%Y-%m-%d")

            temp_end_date = int(obj_end_datetime.strftime('%d'))
            temp_end_month = int(obj_end_datetime.strftime('%m'))
            temp_end_year = int(obj_end_datetime.strftime('%Y'))

            last_date = datetime(temp_end_year, temp_end_month + 1, 1) + timedelta(days=-1)

            if int(last_date.strftime('%d')) != temp_end_date:
                obj_temp_end_date = Utility().convert_string_to_date_time(str(temp_end_year)+'-'+str(temp_end_month)+'-'+ last_date.strftime('%d'), "%Y-%m-%d")

            if obj_temp_start_date and obj_temp_end_date:
                wfh_details = AttendanceDA().get_all_wfh_requests().filter(start_date__gte=obj_temp_start_date,start_date__lte=obj_temp_end_date,
                    status__in =[1,2])
            elif obj_temp_start_date and not obj_temp_end_date:
                wfh_details = AttendanceDA().get_all_wfh_requests().filter(start_date__gte=obj_temp_start_date,start_date__lte=obj_end_datetime,
                    status__in =[1,2])
            elif not obj_temp_start_date and obj_temp_end_date:
                wfh_details = AttendanceDA().get_all_wfh_requests().filter(start_date__gte=obj_start_datetime,start_date__lte=obj_temp_end_date,
                    status__in =[1,2])
            else:
                wfh_details = AttendanceDA().get_all_wfh_requests().filter(start_date__gte=obj_start_datetime,start_date__lte=obj_end_datetime,
                    status__in =[1,2])

            if role_id == 4:
                emp_temp_data = UserDA().get_current_team_members_by_lead_id(user_id)
                emp_temp_id = []
                temp_user = UserDA().get_user_by_id(user_id)
                for each in emp_temp_data:
                    emp_temp_id.append(each.id)
                wfh_emp_id_list = emp_temp_id
                wfh_emp_id_list.append(temp_user.id)
                wfh_details = wfh_details.filter(emp_id__in=wfh_emp_id_list)

            if emp_id:
                wfh_details = wfh_details.filter(emp_id=emp_id)

            employee_durations = {}

            holidays = HolidayDA().get_holidays(obj_start_datetime, obj_end_datetime)
            holiday_list = [holiday.holiday_date for holiday in holidays]


            for each in wfh_details:
                applied = 0
                approved = 0
                duration = 0

                if obj_end <= each.end_date and obj_start >= each.start_date:
                    if obj_start != obj_end:
                        date_objs = self.get_all_working_days_in_between(obj_start, obj_end, holiday_list)
                        duration = len(date_objs)
                    # duration = obj_end - obj_start
                    else:
                        if obj_start.weekday() in [5,6] or obj_start in holiday_list:
                            continue
                        if each.status == 1:
                            applied += 1
                        elif each.status == 2:
                            approved += 1

                elif obj_end <= each.end_date and obj_start <= each.start_date and obj_end >= each.start_date:
                    if obj_end != each.start_date:
                        date_objs = self.get_all_working_days_in_between(each.start_date, obj_end, holiday_list)
                        duration = len(date_objs)
                    # duration = obj_end - each.start_date
                    else:
                        if obj_end.weekday() in [5,6] or obj_end in holiday_list:
                            continue
                        if each.status == 1:
                            applied += 1
                        elif each.status == 2:
                            approved += 1

                elif obj_start >= each.start_date and each.end_date >= obj_end:
                    if each.end_date != obj_start:
                        date_objs = self.get_all_working_days_in_between(obj_start, each.end_date, holiday_list)
                        duration = len(date_objs)
                    # duration = each.end_date - obj_start
                    else:
                        if obj_start.weekday() in [5,6] or obj_start in holiday_list:
                            continue
                        if each.status == 1:
                            applied += 1
                        elif each.status == 2:
                            approved += 1

                elif obj_end >= each.end_date and obj_start <= each.start_date:
                    if each.end_date != each.start_date:
                        date_objs = self.get_all_working_days_in_between(each.start_date, each.end_date, holiday_list)
                        duration = len(date_objs)
                    # duration = each.end_date -each.start_date
                    else:
                        if each.end_date.weekday() in [5,6] or each.end_date in holiday_list:
                            continue
                        if each.status == 1:
                            applied += 1
                        elif each.status == 2:
                            approved += 1

                if duration != 0:
                    if each.status == 1:
                        applied = duration
                    elif each.status == 2:
                        approved = duration

                emp_id = each.emp_id

                if emp_id in employee_durations:
                    employee_durations[emp_id] = {
                        "applied": employee_durations[emp_id]["applied"] + applied,
                        "approved": employee_durations[emp_id]["approved"] + approved
                    }
                else:
                    employee_durations[emp_id] = {
                        "applied": applied,
                        "approved": approved
                    }
            active_users = helper.get_all_user_dict()

            for emp_id, durations in employee_durations.items():
                emp_name = active_users.get(emp_id, '-')
                applied_days = durations.get('applied', 0)
                approved_days = durations.get('approved', 0)
                if applied_days==0 and approved_days==0:
                    continue
                wfh_data = {
                    "emp_id": emp_id,
                    "emp_name": emp_name,
                    "applied": applied_days,
                    "approved": approved_days
                }
                wfh_list.append(wfh_data)
                del wfh_data
            wfh_list = sorted(wfh_list, key=lambda k: k['emp_name'])
            result['wfh'] = wfh_list

        except Exception as err:
            result["error"] = settings.ERROR_MSG['application_error']\
                .format(err, self.__log.error(self.__exception.get_exception()))
        return result


    def get_annual_wfh_analytics_report(self, user_id, year, emp_id=0):
        result = {'success': True, 'error': None, 'month_leaves': {}, 'day_leaves': {}, "type_leaves": {}}

        try:
            status_requested_id = settings.WFH_REQUEST_STATUS_V1['Requested']
            status_approved_id = settings.WFH_REQUEST_STATUS_V1['Approved']
            team_members = [user_id]

            role_id, role_name = UserDA().get_user_role_by_id(user_id)

            start_date = date(year, 1, 1)
            end_date = date(year, 12, 31)

            if role_id in (1, 2, 3):
                users = UserDA().get_current_team_members_by_lead_id(0)
            elif role_id == 4:
                users = UserDA().get_current_team_members_by_lead_id(user_id)
            else:
                temp_user = UserDA().get_user_by_id(user_id)
                users = [temp_user]

            for user in users:
                team_members.append(user.id)

            if role_id == 5 :
                wfhs = AttendanceDA().get_employee_wfh_by_date(start_date, end_date, user_id)
            else:
                if emp_id:
                    wfhs = AttendanceDA().get_employee_wfh_by_date(start_date, end_date, emp_id)
                else:
                    wfhs = AttendanceDA().get_wfhs_by_date_range(start_date, end_date)

            if wfhs:
                month_dict = {"Jan":0.0, "Feb":0.0, "Mar":0.0, "Apr":0.0, "May":0.0, "Jun":0.0, "Jul":0.0, "Aug":0.0, "Sep":0.0, "Oct":0.0, "Nov":0.0, "Dec":0.0 }
                day_dict = {"Monday": 0.0, "Tuesday": 0.0, "Wednesday": 0.0, "Thursday": 0.0, "Friday": 0.0, "Saturday": 0.0, "Sunday": 0.0}
                for wfh in wfhs:
                    wfh_day = 1
                    if wfh.status not in (status_requested_id, status_approved_id):
                        continue
                    if wfh.emp_id not in team_members: #ttttttttttttt
                        continue

                    holidays = HolidayDA().get_holidays(start_date.strftime("%Y-%m-%d"), end_date.strftime("%Y-%m-%d"))
                    holiday_list = [holiday.holiday_date for holiday in holidays]

                    if not wfh.start_date == wfh.end_date:
                        date_objs = self.get_all_working_days_in_between(wfh.start_date, wfh.end_date, holiday_list)

                        for date_obj in date_objs:
                            month = date_obj.strftime("%b")
                            day = date_obj.strftime("%A")

                            month_dict[month] = month_dict[month] + wfh_day
                            day_dict[day] = day_dict[day] + wfh_day
                    else:
                        #TODO if someone applies WFH on holiday or weekend days (for single day not date range)
                        # if wfh.start_date in holiday_list or wfh.start_date.weekday() in [5,6]:
                        #     continue
                        month = wfh.start_date.strftime("%b")
                        day = wfh.start_date.strftime("%A")

                        month_dict[month] = month_dict[month] + wfh_day
                        day_dict[day] = day_dict[day] + wfh_day

                is_wfh_none = list(filter(lambda x: x > 0, day_dict.values()))
                if not is_wfh_none:
                    result['success'] = False
                    result['error'] = 'No WFH Data available'

                result['month_wfh'] = month_dict
                result['day_wfh'] = day_dict
            else:
                result['success'] = False
                result['error'] = 'No WFH Data available'

        except Exception as err:
            result["error"] = settings.ERROR_MSG['application_error']\
                .format(err, self.__log.error(self.__exception.get_exception()))
        return result


    def get_annual_wfh_detail_report(self, user_id, data):
        result = {
            'success': True,
            'error': None,
            'wfhs' : []
        }

        emp_wfh_data = []
        helper = LeaveHelperBL()
        try:
            year = int(data['year'])
            emp_id = data['emp_id']
            oranization_id = int(data['organization'])

            status_requested_id = settings.WFH_REQUEST_STATUS_V1['Requested']
            status_approved_id = settings.WFH_REQUEST_STATUS_V1['Approved']
            team_members = [user_id]

            role_id, role_name = UserDA().get_user_role_by_id(user_id)
            if role_id not in (1, 2, 3, "1", "2", "3"):
                result["error"] = settings.ERROR_MSG.get('access_denied')
                return result

            start_date = date(year, 1, 1)
            end_date = date(year, 12, 31)


            holidays = HolidayDA().get_holidays(start_date.strftime("%Y-%m-%d"), end_date.strftime("%Y-%m-%d"))
            holiday_list = [holiday.holiday_date for holiday in holidays]

            active_users = helper.get_all_user_dict()

            wfhs = AttendanceDA().get_wfhs_by_date_range(start_date, end_date)
            if emp_id:
                wfhs = wfhs.filter(emp_id=emp_id)

            wfh_emp_ids = []
            for wfh in wfhs:
                if wfh.emp_id not in wfh_emp_ids:
                    wfh_emp_ids.append(wfh.emp_id)

            if oranization_id:
                user_ids = []
                user_profiles = UserDA().get_all_user_profiles()
                if user_profiles:
                    users = user_profiles.filter(company_id=oranization_id)
                    user_ids = {user.user_id for user in users}
                    wfh_emp_ids = list(set(wfh_emp_ids) & user_ids)

            for each_user_id in wfh_emp_ids:
                month_dict = {"Jan":0.0, "Feb":0.0, "Mar":0.0, "Apr":0.0, "May":0.0, "Jun":0.0, "Jul":0.0, "Aug":0.0, "Sep":0.0, "Oct":0.0, "Nov":0.0, "Dec":0.0 }
                emp_wfhs = wfhs.filter(emp_id=each_user_id)
                total_wfh_day = 0
                if emp_wfhs:
                    for wfh in emp_wfhs:
                        wfh_day = 1
                        if wfh.status not in (status_requested_id, status_approved_id):
                            continue

                        if not wfh.start_date == wfh.end_date:
                            date_objs = self.get_all_working_days_in_between(wfh.start_date, wfh.end_date, holiday_list)
                            for date_obj in date_objs:
                                month = date_obj.strftime("%b")
                                #day = date_obj.strftime("%A")
                                month_dict[month] = month_dict[month] + wfh_day
                                total_wfh_day = total_wfh_day + 1

                        else:
                            month = wfh.start_date.strftime("%b")
                            #day = wfh.start_date.strftime("%A")
                            month_dict[month] = month_dict[month] + wfh_day
                            total_wfh_day = total_wfh_day + 1

                #result['month_wfh'] = month_dict
                emp_dict = {
                    "emp_id":each_user_id,
                    "emp_name": active_users.get(each_user_id, '-'),
                    "total":total_wfh_day,
                    "months":month_dict

                }
                emp_wfh_data.append(emp_dict)
                del month_dict
            result['wfhs'] = emp_wfh_data



        except Exception as err:
            result["error"] = settings.ERROR_MSG['application_error']\
                .format(err, self.__log.error(self.__exception.get_exception()))
        return result


    def get_all_working_days_in_between(self, start_date, end_date, holiday_list):
        date_list = []
        current_date = start_date

        while current_date <= end_date:
            if current_date.weekday() not in [5,6] and current_date not in holiday_list:
                date_list.append(current_date)
            current_date += timedelta(days=1)

        return date_list



    def wfh_report_dropdowns(self, user, data):
        response = {
            'error': None,
            'members_list': [],
            'reported_to': [],
            'is_display': 0
        }
        try:
            user_id = user.id
            permitted =  False
            role_id, role_name = UserDA().get_user_role_by_id(user_id)
            if role_id in (1, 2, 3, 4):
                response['is_display'] = 1
                if role_id == 4:
                    response['is_display'] = 0
                permitted =  True
            if not permitted:
                response['error'] = settings.ERROR_MSG.get('access_denied')
                return response
            lead = data.get('lead_id', 0)
            if lead not in ('', 0, '0'):
                user_id = int(lead)
                members_list = UserDA().get_current_team_members_by_lead_id(user_id)
                members_list.append(UserDA().get_user_by_id(user_id))
            else:
                if role_id == 4:
                    # get team members
                    members_list = UserDA().get_current_team_members_by_lead_id(user_id)
                    members_list.append(user)
                else:
                    members_list = UserDA().get_all_active_users()
            for each in members_list:
                    member = {}
                    member = {'label': each.first_name +
                                ' ' + each.last_name, 'value': each.id}
                    response['members_list'].append(member)

            # get all supervisors
            reported_to = UserDA().get_all_supervisors()
            for each in reported_to[0]:
                if each:
                    person= {}
                    person = {'label': each[1] + ' ' + each[2],
                        'value': each[0]
                    }
                    response['reported_to'].append(person)
        except Exception as err:
            response["error"] = settings.ERROR_MSG['application_error']\
                .format(err, self.__log.error(self.__exception.get_exception()))
        return response


    def employee_wfh_list(self, request):
        result = {"error": None, "wfh_requests": []}
        wfh_request_list = []
        try:
            user_id = request.user.id
            emp_id = int(request.GET.get('emp_id'))

            role_id, role_name = UserDA().get_user_role_by_id(user_id)
            if role_id not in (1, 2, 3, 4, "1", "2", "3", "4"):
                result["error"] = settings.ERROR_MSG.get('access_denied')
                return result

            if role_id == 4:
                emp_temp_data = UserDA().get_current_team_members_by_lead_id(user_id)
                emp_temp_id = []
                for each in emp_temp_data:
                    emp_temp_id.append(each.id)
                if emp_id not in emp_temp_id and emp_id != user_id:
                    result["error"] = settings.ERROR_MSG.get('access_denied')
                    return result

            start_date = request.GET.get('start_date')
            end_date = request.GET.get('end_date')
            status = int(request.GET.get('status'))
            month_id = int(request.GET.get('month_id')) if not request.GET.get('month_id') in ['undefined'] else None

            emps = UserDA().get_all_users()
            emp_dict = {}

            statuses = settings.WFH_REQUEST_STATUS
            is_status_valid = True if status in statuses.keys() else False
            if not is_status_valid:
                result['error'] = "Invalid WFH status"
                return result

            if month_id:
                start_date = end_date = 'undefined'
                if not 1 <= month_id <= 12:
                    result['error'] = "Invalid month"
                    return result

            current_start_date, current_end_date = self.__get_start_end_dates_current_month(month_id)
            if start_date in ['undefined']:
                start_date = current_start_date
            else:
                start_date = datetime.strptime(start_date, "%Y-%m-%d")

            if end_date in ['undefined']:
                end_date = current_end_date
            else:
                end_date = datetime.strptime(end_date, "%Y-%m-%d")

            for emp in emps:
                emp_dict[emp.id] = emp.first_name + " " + emp.last_name

            is_emp_valid = True if emp_id in emp_dict.keys() else False
            if not is_emp_valid:
                result['error'] = "Employee is not a active user"
                return result

            emp_name = emp_dict[int(emp_id)]

            result['emp_name'] = emp_name
            result['start_date'] = start_date.strftime("%d/%m/%Y")
            result['end_date'] = end_date.strftime("%d/%m/%Y")

            holidays = HolidayDA().get_holidays(start_date, end_date)
            holiday_list = [holiday.holiday_date for holiday in holidays]

            holiday_list = list(map(lambda day: datetime.strptime(day.strftime("%Y-%m-%d"), "%Y-%m-%d"), holiday_list))

            wfh_requests = AttendanceDA().get_all_wfh_requests_by_user_id(emp_id)

            # if status:
            #     wfh_requests = wfh_requests.filter(status = status)

            if start_date and end_date:
                wfh_requests = wfh_requests.filter(Q(
                    Q(start_date__gte=start_date, start_date__lte=end_date) |
                    Q(end_date__gte=start_date, end_date__lte=end_date) |
                    Q(start_date__lte=start_date, end_date__gte=start_date) |
                    Q(start_date__lte=end_date, end_date__gte=end_date)
                ), status=status)

            if wfh_requests:
                total_count = 0
                for wfh_request in wfh_requests:
                    no_of_days = 0
                    date_range = Utility().get_date_range(wfh_request.start_date,wfh_request.end_date)
                    if month_id:
                        date_range = list(filter(lambda date_obj: (date_obj.weekday() not in [5,6] and (date_obj.month == month_id and date_obj not in holiday_list)), date_range))
                    else:
                        date_range = list(filter(lambda date_obj: (date_obj.weekday() not in [5,6] and date_obj not in holiday_list), date_range))
                    no_of_days = len(date_range)
                    # for date_obj in date_range:
                    #     if not date_obj.weekday() in [5,6]:
                    #         no_of_days += 1

                    temp = {
                        'wfh_id': wfh_request.wfh_id,
                        'start_date': wfh_request.start_date,
                        'end_date': wfh_request.end_date,
                        'emp_name': emp_name,
                        'emp_id': emp_id,
                        'approver': emp_dict.get(wfh_request.approver_id, ''),
                        'status': settings.WFH_REQUEST_STATUS[wfh_request.status],
                        'reason': wfh_request.reason,
                        'comment': wfh_request.comment,
                        'created_date': wfh_request.created_date,
                        "no_of_days": no_of_days
                    }

                    wfh_request_list.append(temp)
                    del temp

                    total_count += no_of_days

                wfh_request_list = sorted(wfh_request_list, key=lambda dict : dict['start_date'])
                # total_count = len(wfh_request_list)
                wfh_request_list.append(
                    {
                        'wfh_id': '',
                        'start_date': '',
                        'end_date': '',
                        'emp_name': 'Total Count',
                        'emp_id': emp_id,
                        'approver': '',
                        'status': '',
                        'reason': '',
                        'comment': '',
                        'created_date': '',
                        "no_of_days": total_count,
                        'is_bold': True,
                    }
                )
                result['wfh_requests'] = wfh_request_list
        except Exception as err:
            result["error"] = settings.ERROR_MSG['application_error']\
                .format(err, self.__logs.error(self.__exception.get_exception()))
        finally:
            return result


    def __get_start_end_dates_current_month(self, month_id=0):
        if month_id:
            if not 1 <= month_id <= 12:
                raise ValueError("Invalid Month")

            year = datetime.now().year

            # Calculate first date of the month
            first_date = datetime(year, month_id, 1)

            # Calculate last date of the month
            if month_id == 12:
                next_month_first_date = datetime(year + 1, 1, 1)
            else:
                next_month_first_date = datetime(year, month_id + 1, 1)

            last_date = next_month_first_date - timedelta(days=1)

            return first_date.date(), last_date.date()

        else:
            today = date.today()

            first_day = today.replace(day=1)

            next_month = first_day.replace(month=first_day.month + 1, day=1)
            last_day = next_month - timedelta(days=1)

        return first_day, last_day



    def get_first_last_dates(month_id, year=None):
            # Validate month_id
        if not 1 <= month_id <= 12:
            raise ValueError("Invalid Month")

        # If year is not provided, use current year
        if year is None:
            year = datetime.now().year

        # Calculate first date of the month
        first_date = datetime(year, month_id, 1)

        # Calculate last date of the month
        if month_id == 12:
            next_month_first_date = datetime(year + 1, 1, 1)
        else:
            next_month_first_date = datetime(year, month_id + 1, 1)

        last_date = next_month_first_date - timedelta(days=1)

        return first_date.date(), last_date.date()