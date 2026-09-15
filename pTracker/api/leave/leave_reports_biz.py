from types import SimpleNamespace
from datetime import datetime, date, timedelta
import calendar
from collections import Counter
# import datetime

from django.conf import Settings, settings
from django.db import  DatabaseError, transaction
from django.http import response

from pTracker.common.utility import Utility
from pTracker.common.exception_handler import ExceptionHandler
from pTracker.common.logs import Logs

from pTracker.api.leave.leave_helper import LeaveHelperBL

from pTracker.dataaccess.ptracker_access.leave_da import LeaveDA
from pTracker.dataaccess.ptracker_access.user_da import UserDA
from pTracker.dataaccess.ptracker_access.holiday_da import HolidayDA
from pTracker.settings import constants


def new_dto():
    dto = SimpleNamespace()
    return dto

class LeaveReportsBL():
    def __init__(self):
        self.__log = Logs()
        self.__exception = ExceptionHandler()
        self.__utility = Utility()

    def my_test(self):
        obj_start = Utility().convert_string_to_date_time("2021-11-01", "%Y-%m-%d")
        obj_end = Utility().convert_string_to_date_time("2021-11-26", "%Y-%m-%d")

        duration = Utility().get_date_range(obj_start, obj_end)
        week_days = LeaveHelperBL().get_all_off_days_for_date_range(obj_start, obj_end)

    def get_leave_summary_report(self, user_id, data):
        result = {'error': None, 'leaves': [], 'summary': {}}

        total_general = 0.0
        total_official = 0.0
        total_comp_off = 0.0
        total_lop = 0.0
        total_maternity = 0.0
        total_leaves = 0.0
        total_working_days = 0.0

        leaves_list = []
        leave_emp_id_list = []
        summary_dict = {}
        try:
            helper = LeaveHelperBL()
            leave_da = LeaveDA()
            status_requested_id = settings.LEAVE_REQUEST_STATUS['Requested']
            status_approved_id = settings.LEAVE_REQUEST_STATUS['Approved']

            role_id, role_name = UserDA().get_user_role_by_id(user_id)
            if role_id not in (1, 2, 3, 4, "1", "2", "3", "4"):
                result["error"] = settings.ERROR_MSG.get('access_denied')
                return result

            emp_id = int(data.get('emp_id', 0))
            filter_date = int(data.get('month', 0))
            startDate = data.get('startDate', 0)
            endDate = data.get('endDate', 0)
            lead_id = int(data.get('lead_id',0))
            obj_start = Utility().convert_string_to_date_time(startDate, "%Y-%m-%d")
            obj_end = Utility().convert_string_to_date_time(endDate, "%Y-%m-%d")

            working_days = Utility().get_date_range(obj_start, obj_end)
            off_days = LeaveHelperBL().get_all_off_days_for_date_range(obj_start, obj_end)

            total_working_days = len(working_days) - off_days

            # if lead_id:
            #     active_users = helper.get_all_user_dict_by_lead_id(lead_id)
            # else:
            #     active_users = helper.get_all_user_dict()
            # if role_id == 4:
            #     active_users = helper.get_all_user_dict_by_lead_id(user_id)
            if lead_id:
                user_id = lead_id
                role_id = 4
            active_users = helper.get_all_user_dict()
            leave_types = helper.get_leave_type_dict()

            leaves = leave_da.get_leaves_by_date_range(obj_start, obj_end)
            if leaves:
                for leave in leaves:
                    leave_emp_id_list.append(leave.employee_id)
            leave_emp_id_list = list(set(leave_emp_id_list))
            if role_id == 4:
                emp_temp_data = UserDA().get_current_team_members_by_lead_id(user_id)
                emp_temp_id = []
                temp_user = UserDA().get_user_by_id(user_id)
                for each in emp_temp_data:
                    emp_temp_id.append(each.id)
                # leave_emp_id_list = list(set(emp_temp_id)&set(leave_emp_id_list))
                leave_emp_id_list = emp_temp_id
                leave_emp_id_list.append(temp_user.id)


            if emp_id:
                leave_emp_id_list = [emp_id]
            for emp_id in leave_emp_id_list:
                general = 0.0
                official = 0.0
                comp_off = 0.0
                lop = 0.0
                maternity = 0.0
                emp_total_leaves = 0.0
                emp_name = active_users.get(emp_id, '-')

                emp_leaves = leaves.filter(employee_id=emp_id)

                if emp_leaves:
                    for leave in emp_leaves:
                        leave_day = 1
                        if leave.status not in (status_requested_id, status_approved_id):
                            continue
                        leave_type = leave_types.get(leave.type_id, '')
                        leave_housrs = leave.length_hours
                        if leave_housrs == 4:
                            leave_day = 0.5

                        emp_total_leaves += leave_day
                        total_leaves += leave_day

                        if str(leave_type).lower() == "general":
                            general += leave_day
                            total_general += leave_day

                        elif str(leave_type).lower() == "official":
                            official += leave_day
                            total_official += leave_day

                        elif str(leave_type).lower() == "comp off":
                            comp_off += leave_day
                            total_comp_off += leave_day

                        elif str(leave_type).lower() == "lop":
                            lop += leave_day
                            total_lop += leave_day

                        elif str(leave_type).lower() == "maternity":
                            maternity += leave_day
                            total_maternity += leave_day

                    leave_persentage = (emp_total_leaves / total_working_days) * 100
                    leave_data = {
                        "emp_id": emp_id,
                        "emp_name": emp_name,
                        "general": general,
                        "official": official,
                        "comp_off": comp_off,
                        "lop": lop,
                        "maternity": maternity,
                        "emp_total_leaves": emp_total_leaves,
                        "total_working_days": total_working_days - emp_total_leaves,
                        "leave_persentage": int(leave_persentage)

                    }
                    leaves_list.append(leave_data)
                    del emp_leaves, leave_data
            leaves_list = sorted(leaves_list, key=lambda k: k['emp_name'])
            result['leaves'] = leaves_list
            summary_dict['total_general'] = total_general
            summary_dict['total_official'] = total_official
            summary_dict['total_comp_off'] = total_comp_off
            summary_dict['total_lop'] = total_lop
            summary_dict['total_maternity'] = total_maternity
            summary_dict['total_leaves'] = total_leaves
            summary_dict['total_days'] = total_working_days
            result['summary'] = summary_dict


        except Exception as err:
            response["error"] = settings.ERROR_MSG['application_error']\
                .format(err, self.__log.error(self.__exception.get_exception()))
        return result

    def annual_leave_summary_report(self, user_id, data):
        """
        {
            emp_name
            emp_id
            month :{'jan':12, 'feb':4,......., 'total_used':15, 'total_allottes':25, 'total_leaft'5 }
            }
                    """
        year = data['year']
        emp_id = data['emp_id']
        oranization_id = data['organization']
        response = {'error': None, 'leaves': []}
        helper = LeaveHelperBL()
        leave_da = LeaveDA()
        status_requested_id = settings.LEAVE_REQUEST_STATUS['Requested']
        status_approved_id = settings.LEAVE_REQUEST_STATUS['Approved']
        leave_emp_id_list = []
        leaves_list = []
        leave_period_id = 0

        try:
            role_id, role_name = UserDA().get_user_role_by_id(user_id)
            if role_id not in (1, 2, 3, "1", "2", "3"):
                response["error"] = settings.ERROR_MSG.get('access_denied')
                return response

            obj_start = Utility().convert_string_to_date_time(str(year) + "-01-01", "%Y-%m-%d")
            obj_end = Utility().convert_string_to_date_time(str(year) + "-12-31", "%Y-%m-%d")
            if not obj_start or not obj_end:
                response["error"] = "Invalid leave year."
                return response
            period = leave_da.get_leave_period_by_date(obj_start)
            if period:
                leave_period_id = period.leave_period_id
            leave_quota_dict = helper.get_total_leave_quota_by_period(leave_period_id)
            active_users = helper.get_all_user_dict()
            leaves = leave_da.get_leaves_by_date_range(obj_start, obj_end)
            all_user_profiles = leave_da.get_all_active_users_profile()
            if not (int(oranization_id) == 0):
                all_user_profiles = all_user_profiles.filter(company_id = oranization_id)
            if emp_id:
                leaves = leaves.filter(employee_id = emp_id)
            if leaves:
                for leave in leaves:
                    if leave.status not in (status_requested_id, status_approved_id):
                            continue
                    leave_emp_id_list.append(leave.employee_id)
            else:
                return response
            all_employees = []
            for each in all_user_profiles:
               all_employees.append(each.user_id)
            leave_emp_id_list = [value for value in all_employees if value in leave_emp_id_list]
            leave_emp_id_list = list(set(leave_emp_id_list))
            for emp_id in leave_emp_id_list:
                emp_total_leaves = 0.0
                month_dict = {"Jan":0.0, "Feb":0.0, "Mar":0.0, "Apr":0.0, "May":0.0, "Jun":0.0, "Jul":0.0, "Aug":0.0, "Sep":0.0, "Oct":0.0, "Nov":0.0, "Dec":0.0 }
                emp_name = active_users.get(emp_id, '-')
                emp_leaves = leaves.filter(employee_id=emp_id)
                if emp_leaves:
                    for leave in emp_leaves:
                        leave_day = 1
                        if leave.status not in (status_requested_id, status_approved_id):
                            continue
                        leave_housrs = leave.length_hours
                        if leave_housrs == 4:
                            leave_day = 0.5
                        month = leave.leave_date.strftime("%b")

                        month_dict[month] = month_dict[month] + leave_day
                        emp_total_leaves = emp_total_leaves + leave_day
                total_allotted = leave_quota_dict.get(emp_id, 0)
                month_dict['total_used'] = emp_total_leaves
                month_dict['total_allotted'] = total_allotted
                month_dict['total_left'] = float(total_allotted) - float(emp_total_leaves)
                temp_dict = {"emp_id": emp_id, "emp_name": emp_name, "months": month_dict}
                leaves_list.append(temp_dict)
                del temp_dict
            response['leaves'] = leaves_list
        except Exception as err:
            response["error"] = settings.ERROR_MSG['application_error']\
                .format(err, self.__log.error(self.__exception.get_exception()))
        return response

    def get_all_active_users(self):
        # for dropdown in annual leave report and team compensatory leaves, not to be here
        response = {"error": "",
                    "users": []}
        try:
            active_users = []
            users = UserDA().get_all_active_users()
            for each in users:
                temp = {
                    "id": each.id,
                    "name": each.first_name+''+each.last_name
                }
                active_users.append(temp)
            response['users'] = active_users
        except Exception as err:
            response["error"] = settings.ERROR_MSG['application_error']\
                .format(err, self.__log.error(self.__exception.get_exception()))
        return response



    def get_annual_leave_analytics_report(self, user_id, year, emp_id=0):
        result = {'error': None, 'month_leaves': {}, 'day_leaves': {}, "type_leaves": {}}

        try:
            helper = LeaveHelperBL()
            leave_da = LeaveDA()
            status_requested_id = settings.LEAVE_REQUEST_STATUS['Requested']
            status_approved_id = settings.LEAVE_REQUEST_STATUS['Approved']
            team_members = [user_id]

            role_id, role_name = UserDA().get_user_role_by_id(user_id)

            year_start = date(year, 1, 1)
            #year_end = date(date.today().year, 12, 31)
            leave_types = helper.get_leave_type_dict()

            leave_period = leave_da.get_leave_period_by_date(year_start)

            if leave_period:
                start_date = leave_period.leave_period_start_date
                end_date = leave_period.leave_period_end_date
            else:
                result["error"] = "Invalid Leave Period."
                return result

            if role_id in (1, 2, 3):
                users = UserDA().get_current_team_members_by_lead_id(0)
            elif role_id == 4:
                users = UserDA().get_current_team_members_by_lead_id(user_id)
            else:#tttttttttt
                temp_user = UserDA().get_user_by_id(user_id)
                users = [temp_user]

            for user in users:
                team_members.append(user.id)

            if role_id == 5 :
                leaves = leave_da.get_employee_leave_by_date(start_date, end_date, user_id)
            else:
                if emp_id:
                    leaves = leave_da.get_employee_leave_by_date(start_date, end_date, emp_id)
                else:
                    leaves = leave_da.get_leaves_by_date_range(start_date, end_date)

            if leaves:
                month_dict = {"Jan":0.0, "Feb":0.0, "Mar":0.0, "Apr":0.0, "May":0.0, "Jun":0.0, "Jul":0.0, "Aug":0.0, "Sep":0.0, "Oct":0.0, "Nov":0.0, "Dec":0.0 }
                day_dict = {"Monday": 0.0, "Tuesday": 0.0, "Wednesday": 0.0, "Thursday": 0.0, "Friday": 0.0, "Saturday": 0.0, "Sunday": 0.0}
                leave_type_dict = {"General": 0.0, "Official": 0.0, "Comp Off": 0.0, "LOP": 0.0, "Maternity": 0.0,}
                for leave in leaves:
                    leave_day = 1
                    if leave.status not in (status_requested_id, status_approved_id):
                        continue
                    if leave.employee_id not in team_members: #ttttttttttttt
                        continue

                    leave_housrs = leave.length_hours
                    if leave_housrs == 4:
                        leave_day = 0.5
                    month = leave.leave_date.strftime("%b")
                    day = leave.leave_date.strftime("%A")
                    leave_type = leave_types[leave.type_id]

                    month_dict[month] = month_dict[month] + leave_day
                    day_dict[day] = day_dict[day] + leave_day
                    leave_type_dict[leave_type] = leave_type_dict[leave_type] + leave_day

                result['month_leaves'] = month_dict
                result['day_leaves'] = day_dict
                result['type_leaves'] = leave_type_dict
            # else:
            #     return response


        except Exception as err:
            response["error"] = settings.ERROR_MSG['application_error']\
                .format(err, self.__log.error(self.__exception.get_exception()))
        return result

    def get_pending_leave_request_lists(self, user_id):
        result = {
            'error': None,
            'total_pending': {},
            'graph_data': {},
            'is_display': 0,
            'comp_count': 0
        }
        try:
            total_pending = 0
            mapping_dict = {}
            user_dict = {}
            sub_list = []
            temp_list = []
            temp = {}
            temp_data = {}
            today_stats = 0
            month_stats = 0
            status_requested_id = settings.LEAVE_REQUEST_STATUS['Requested']
            role_id, role_name = UserDA().get_user_role_by_id(user_id)
            start_day = date.today() #date(date.today().year, 1, 31)#ttttttttt
            end_day = date(start_day.year, 12, 31)
            this_week_end  = Utility().get_next_n_working_days(7)

            if role_id == 4:
                team_members = UserDA().get_current_team_members_by_lead_id(user_id)
                team_members.append(UserDA().get_user_by_id(user_id))
            elif role_id ==5 :
                team_members = UserDA().get_current_team_members_by_emp_id(user_id)
                team_members.append(UserDA().get_user_by_id(user_id))
            else:
                team_members = UserDA().get_all_active_users()
            for user in team_members:
                user_dict[user.id] = user.first_name  + " " + user.last_name
            today_stats = self.__process_leave_count_by_date_range(date.today(), date.today(), team_members)
            month_stats = self.__process_leave_count_by_date_range(date(start_day.year , start_day.month, 1),\
                        date.today(), team_members)
            this_week = self.__process_leave_count_by_date_range(date.today(), this_week_end[-1], team_members)
            result["graph_data"] = {'today':today_stats, 'month':month_stats, 'this_week':this_week}

            if role_id in (1, 2, 3, 4):

                lead_mappings = UserDA().get_all_employee_lead_mapping()
                leave_request = LeaveDA().get_all_leave_requests()

                for each in lead_mappings:
                    mapping_dict[each.emp_id] = each.lead_id

                if leave_request:
                    team_id_list = [each.id for each in team_members if each.id != user_id ]
                    leave_request = leave_request.filter(employee_id__in=team_id_list)

                    for leave in leave_request.filter(status=1):
                        lead_name = user_dict.get(mapping_dict.get(leave.employee_id), None)
                        temp_list.append(lead_name)

                    total_pending = leave_request.filter(status=1).count()
                    sub_list = [{'name':value[0], 'value':value[1]} for value in Counter(temp_list).items()]

                if role_id in (1, 2, 3):
                    result["is_display"] = 1
                result["total_pending"] = {'total_pending':total_pending,'sub_list':sub_list}
                result["comp_count"] = self.__get_pending_compensatory_request(team_members)

        except Exception as error:
            response["error"] = settings.ERROR_MSG['application_error']\
                .format(error, self.__log.error(self.__exception.get_exception()))
        return result


    def __process_leave_count_by_date_range(self, start_date, end_date, users):
        count = 0
        status_requested_id = settings.LEAVE_REQUEST_STATUS['Requested']
        status_approved_id = settings.LEAVE_REQUEST_STATUS['Approved']
        leaves = LeaveDA().get_all_leaves_by_date_range(start_date, end_date, \
            status = [status_requested_id, status_approved_id])
        for each in users:
            for row in leaves:
                if each.id == row.employee_id:
                    if row.leave_day_type == settings.LEAVE_DAY_TYPE['Fullday']:
                        count += 1
                    else:
                        count += .5
        return count

    def __get_pending_compensatory_request(self, team_members):
        try:
            id_list = []
            for member in team_members:
                id_list.append(member.id)
            period = LeaveDA().get_leave_period_by_date(date.today()).leave_period_id
            leaves = LeaveDA().get_all_comp_off_requests_by_status(period)
            if leaves:
                leaves = leaves.filter(employee_id__in=id_list, status = 1).count()
            else:
                leaves = 0
            return leaves
        except:
            return 0

    def get_pending_leaves(self, user_id, limit = 3):
        response = {'error': None, 'pending_leaves':[]}
        try:
            role_id, role_name = UserDA().get_user_role_by_id(user_id)
            if role_id != 5:
                return response
            temp ={}
            today = date.today()
            period = LeaveDA().get_leave_period_by_date(today)
            temp_leaves = LeaveDA().get_all_leave_requests()
            if temp_leaves:
                exclude_list = [settings.LEAVE_REQUEST_STATUS['Cancelled'],settings.LEAVE_REQUEST_STATUS['Rejected']]
                temp_leaves = temp_leaves.filter(leave_period_id = period.leave_period_id,\
                    employee_id = user_id, start_date__gt=today).exclude(status__in=exclude_list).order_by('start_date')

                for each in temp_leaves[:limit]:
                    temp['status'] = each.status
                    temp['date'] = each.start_date
                    temp['leave_type'] = each.type_id
                    response["pending_leaves"].append(temp)
                    temp = {}
            # leaves = LeaveDA().get_leaves_by_date_range(period.leave_period_start_date,\
            #     period.leave_period_end_date)
            # if leaves:
            #     leaves = leaves.filter(leave_date__gt=today)
            #     exclude_list = [settings.LEAVE_REQUEST_STATUS['Cancelled'],settings.LEAVE_REQUEST_STATUS['Rejected']]
            #     leaves = leaves.filter(employee_id = user_id)
            #     leaves = leaves.exclude(status__in=exclude_list)
                # leaves = leaves.order_by('-leave_id')
        except Exception as err:
            response["error"] = settings.ERROR_MSG['application_error']\
                .format(err, self.__log.error(self.__exception.get_exception()))
        return response

    # def send_not_punch_notification(self, user, data):
    #     response = { 'error': None, 'message': '' }
    #     try:
    #         role_id, role_name = UserDA().get_user_role_by_id(user.id)
    #         if role_id not in(1, 2, 3, '1', '2', '3'):
    #             response["error"] = settings.ERROR_MSG.get('access_denied')
    #             return response
    #         comment = data.get('comment', None)
    #         emp_id = data.get('emp_id', 0)
    #         if emp_id:
    #             employee = UserDA().get_user_by_id(emp_id)

    #     except Exception as error:
    #         response["error"] = settings.ERROR_MSG['application_error']\
    #             .format(error, self.__log.error(self.__exception.get_exception()))
    #     return response