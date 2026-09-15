
import math
import time
import copy
from  datetime import datetime, date, timedelta
from django.conf import settings
from types import SimpleNamespace
from pTracker.api import attendance

from pTracker.common.utility import Utility
from pTracker.common.exception_handler import ExceptionHandler
from pTracker.common.logs import Logs
from pTracker.dataaccess.ptracker_access.project_da import  ProjectDA

from pTracker.dataaccess.essl_access.attendance import  AttendanceDA
from pTracker.user_management.holiday_da import HolidayDA
from pTracker.dataaccess.ptracker_access.user_da import UserDA
from pTracker.api.attendance.mapping_biz import UserMappingBL
from pTracker.user_management.employee import Employee
from pTracker.dataaccess.ptracker_access.attendance import AttendanceDA as pAttendanceDA
from pTracker.dataaccess.ptracker_access.leave_da import LeaveDA
from pTracker.api.user.user_management_bl_v1 import UserManagementBL_V1


def new_dto():
    dto = SimpleNamespace()
    return dto


class AttendanceBL_V1():

    def __init__(self):
        self.__log = Logs()
        self.__exception = ExceptionHandler()

    def __get_team_members(self, role_id, user_id):
        if role_id == 4:
            return UserDA().get_current_team_members_by_lead_id(user_id)
        else:
            return UserDA().get_all_active_users()

    def __get_list_diff(self, li1, li2):
        return list(set(li1) - set(li2)) + list(set(li2) - set(li1))

    def __get_profile_photo(self):
        profile_dict = {}
        emp_dict = {}
        all_emps = UserDA().get_all_active_users()
        for each in all_emps:
            try:
                emp_dict[each.id] = int(each.username)
            except:
                continue

        emps = UserDA().get_all_user_profiles()
        for each_emp in emps:
            img_uri =  f"{settings.DEFAULT_SITE_MEDIA_URL}{each_emp.profile_photo}"
            profile_dict[emp_dict.get(each_emp.user_id, 0)] = img_uri
        return profile_dict


    def __get_punchout_data(self, att_date):
        punchout_dict = {}
        punchout_data, err = AttendanceDA().get_logout_details_by_date(att_date, att_date)
        if punchout_data:
            for each_item in punchout_data:
                try:
                    key = int(each_item[0])
                except:
                    continue
                if key in punchout_dict.keys():
                    continue
                punchout_dict[key] = Utility().convert_string_to_date_time(str(each_item[2]).lower())
        return punchout_dict

    def get_team_stats(self, user_id, att_date, page=1,filter_by_type='', keyword=0):
        try:
            #att_date yyyy-mm-dd
            total_employees = 0
            active_users_emp_code = []
            c_level_emps = []
            active_users_dict = {}
            puched_emps = []
            no_of_wfh = 0
            no_of_present = 0
            no_of_leave = 0
            no_of_not_punched = 0
            detail_items_list = []
            active_users_emp_id_dict= {}

            result = {
                'status' : 200,
                'error': None,
                'present_count': 0,
                'leave_count': 0,
                'wfh_count': 0,
                'not_punched_count': 0,
                'team_members': []
            }
            team_dict = {
                "emp_id": 0,
                "emp_name":"",
                "emp_image": "",
                "status": "",
                "work_hours": 0,
                "first_punch_in": "-",
                "last_punch_out": "-",

            }
            requsests = {"leave_requests": 0, "wfh_requests": 0}

            role_id, role_name = UserDA().get_user_role_by_id(user_id)
            if role_id not in (1, 2, 3, 4):
                result['error'] = settings.ERROR_MSG.get('access_denied')
                result['status'] = 403
                return result

            filter_by_type = self.format_filter_by_type_for_team_stats(filter_by_type)

            emps = self.__get_team_members(role_id, user_id)
            if role_id in (1, 2, 3): #TODO verfiy
                emps = emps.exclude(id=user_id)
            if keyword:
                for row,each in enumerate(emps):
                    user_name = each.first_name + ' ' + each.last_name
                    if user_name.upper().startswith(keyword.upper()) == False and\
                        user_name.upper().endswith(keyword.upper()) == False:
                            if role_id == 4:
                                del emps[row]
                            else:
                                emps = emps.exclude(id=each.id)
            # if len(emps):
            #     emps = sorted(emps, key = lambda i: i.first_name)

            for emp in emps:
                try:
                    user_name = emp.first_name + ' ' + emp.last_name
                    if keyword:
                        if user_name.upper().startswith(keyword.upper()) == False and\
                            user_name.upper().endswith(keyword.upper()) == False:
                                continue
                    total_employees += 1
                    active_users_emp_code.append(int(emp.username))
                    active_users_dict[int(emp.username)] = emp.first_name + " " + emp.last_name
                    active_users_emp_id_dict[int(emp.username)] = emp.id
                except :
                    continue

            # results = Employee().get_att_exclude_employees_code()
            # if results:
            #     for each_item in results:
            #         try:
            #             c_level_emps.append(int(each_item.emp_code))
            #             total_employees = total_employees - 1
            #         except :
            #             continue

            #active_users_emp_code = self.__get_list_diff(active_users_emp_code, c_level_emps)
            punchout_dict = self.__get_punchout_data(att_date)
            profile_photo = self.__get_profile_photo()

            attendance_details, err = AttendanceDA().get_attendance_details_by_date(att_date, att_date)
            if attendance_details:
                for attendance in attendance_details:
                    emp_code = int(attendance[0])
                    device = str(attendance[1]).lower()
                    punch_in = str(attendance[2]).lower()
                    punch_in = Utility().convert_string_to_date_time(punch_in)
                    if emp_code in active_users_emp_code:
                        if emp_code in puched_emps:
                            continue
                        else:
                            temp_dict = copy.deepcopy(team_dict)
                            temp_dict["emp_id"] = active_users_emp_id_dict.get(emp_code)
                            temp_dict["emp_image"] = profile_photo.get(emp_code, '')
                            temp_dict["emp_name"] = active_users_dict.get(emp_code)
                            temp_dict["first_punch_in"] = punch_in.strftime("%I:%M %p")
                            punch_out = punchout_dict.get(emp_code, None)
                            if punch_out:
                                temp_dict["last_punch_out"] = punch_out.strftime("%I:%M %p")
                                temp_dict["work_hours"] = Utility().time_diff_in_seconds(punch_in, punch_out)


                            puched_emps.append(emp_code)
                            if device == "web in":
                                no_of_wfh += 1
                                temp_dict["status"] = "WFH"
                            else:
                                no_of_present += 1
                                temp_dict["status"] = "In Office"

                            detail_items_list.append(temp_dict)
                            del temp_dict

            active_users_emp_code = self.__get_list_diff(active_users_emp_code, puched_emps)

            #no of leave
            obj_att_date = datetime.strptime(att_date, "%Y-%m-%d")
            status_requested_id = settings.LEAVE_REQUEST_STATUS['Requested']
            status_approved_id = settings.LEAVE_REQUEST_STATUS['Approved']
            status_in = [status_requested_id, status_approved_id ]
            leaves = self.__get_emp_leave_dict_by_date_range_and_status_in(obj_att_date, obj_att_date, status_in)

            results = Employee().get_att_exclude_employees_code()
            if results:
                for each_item in results:
                    c_level_emps.append(int(each_item.emp_code))


            for each_emp in active_users_emp_code:
                # if role_id==4:
                #     for ec in emps:
                #         if ec.username==each_emp:
                #             emp=ec
                # else:
                #     emp = emps.get(username=each_emp)
                try:
                    if each_emp in c_level_emps:
                        continue
                    # leave = leaves.get(employee_id=emp.id)
                    leave = leaves.get(active_users_emp_id_dict.get(each_emp), None)
                    temp_dict = copy.deepcopy(team_dict)
                    temp_dict["emp_id"] =  active_users_emp_id_dict.get(each_emp)
                    temp_dict["emp_image"] = profile_photo.get(each_emp, '')
                    temp_dict["emp_name"] = active_users_dict.get(each_emp)

                    if leave:
                        temp_dict["status"] = "Leave"
                        no_of_leave += 1
                    else:
                        temp_dict["status"] = "Not Punched"
                        no_of_not_punched += 1
                    #temp_dict["punch_in"] = "-"
                    detail_items_list.append(temp_dict)
                    del temp_dict
                    #leave_emps.append(each_emp)
                except Exception as err:
                    continue
            if role_id in (1, 2, 3, 4):
                request_count = UserManagementBL_V1().get_request_count(user_id, date=att_date)
                if request_count:
                    if request_count.get("error"):
                        pass
                    else:
                        result["requests"] = request_count
                else:
                    result["requests"] = requsests
            else:
                result["requests"] = requsests

            filtered_detail_items_list = []
            if filter_by_type:
                if filter_by_type.upper() != "ALL":
                    for detail in detail_items_list:
                        if detail['status'].upper() == filter_by_type.upper():
                            filtered_detail_items_list.append(detail)
                    detail_items_list = filtered_detail_items_list

            if len(detail_items_list):
                min, max = Utility().cutomPageLimits(page, 25)
                detail_items_list = sorted(detail_items_list, key = lambda i: i['emp_name'])[min:max]


            result["team_members"] = detail_items_list
            result['present_count'] = no_of_present
            result['wfh_count'] = no_of_wfh
            result['leave_count'] = no_of_leave
            result['not_punched_count'] = no_of_not_punched
            #     min, max = Utility().cutomPageLimits(page, 25)
            #     result["team_members"] = team_stats[min:max]
        except Exception as err:
            #response = {}
            result['status'] = 499
            result["error"] = settings.ERROR_MSG['application_error']\
                .format(err, self.__logs.error(self.__exception.get_exception()))
        return result


    def __get_emp_leave_dict_by_date_range_and_status_in(self, obj_start_date, obj_end_date, status_in ):
        emp_leave_dict ={}

        leaves = LeaveDA().get_all_leaves_by_date_range(obj_start_date,obj_end_date, \
            status=status_in)

        for leave in leaves:
            emp_leave_dict[leave.employee_id] = leave

        return emp_leave_dict

    def format_filter_by_type_for_team_stats(self, filter_by_type):

        if filter_by_type.upper() == "IN_OFFICE":
            filter_by_type = "In Office"

        if filter_by_type.upper() == "LEAVE":
            filter_by_type = "Leave"

        if filter_by_type.upper() == "WFH":
            filter_by_type = "WFH"

        if filter_by_type.upper() == "NOT_PUNCHED":
            filter_by_type = "Not Punched"

        return filter_by_type

