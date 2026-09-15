from types import SimpleNamespace
from datetime import datetime, timedelta
from datetime import date

from django.conf import settings

from pTracker.common.logs import Logs
from pTracker.api.leave.leave_helper import LeaveHelperBL
from pTracker.settings import constants
from pTracker.common.utility import Utility
from pTracker.common.exception_handler import ExceptionHandler
from pTracker.dataaccess.ptracker_access.leave_da import LeaveDA
from pTracker.dataaccess.ptracker_access.user_da import UserDA




def new_dto():
    dto = SimpleNamespace()
    return dto

class LeaveBulkBL():

    def __init__(self):
        self.__log = Logs()
        self.__exception = ExceptionHandler()
        self.__utility = Utility()


    def __is_access(self, user_id):
        is_access = False
        role_id, role_name = UserDA().get_user_role_by_id(user_id)
        if role_id in (2, "2"):
            is_access = True
        return is_access

    def __get_emp_profile_dict(self):
        profile_dict = {}
        emp_profiles = UserDA().get_all_user_profiles()
        for profile in emp_profiles:
            profile_dict[profile.user_id] = profile
        return profile_dict

    def __taken_leave(self, emp_leaves):
        leave_taken = 0.0
        leave_hours = 0.0
        if emp_leaves:
            for leave in emp_leaves:
                if leave.status in (1, 2):
                    leave_hours = leave_hours + leave.length_hours
        leave_taken = leave_hours / 8
        return leave_taken

    def credit_yearly_employee_leave(self, user_id, credit_year):
        result = {"error": None, "leave_quota": None}
        leave_quota_list = []
        leave_da = LeaveDA()
        try:
            #leave_period_id = 0
            #credit_year = leave_period_id
            user_da = UserDA()
            permitted = self.__is_access(user_id)
            if not permitted:
                result["error"] = settings.ERROR_MSG.get('access_denied')
                return result

            year_start = date(credit_year,1,1)
            obj_leave_period = leave_da.get_leave_period_by_date(year_start)
            if not obj_leave_period:
                result["error"] = "Leave period for selecting year ({0}) is missing in system.".format(credit_year)
                return result

            if leave_da.get_all_employees_leave_quota(obj_leave_period.leave_period_id):
                result["error"] = "Leave quota is already processed for selecting year ({0}).".format(credit_year)
                return result


            active_emps = user_da.get_all_active_users()
            profile_dict = self.__get_emp_profile_dict()
            leave_types = LeaveDA().get_all_leave_types()
            period_id = LeaveDA().get_leave_period_by_date(date(credit_year,1,1)).leave_period_id

            for employee in active_emps:
                emp_name = employee.first_name + " " + employee.last_name
                emp_dict = {"emp_name": emp_name, "emp_id": employee.username, "leave_details": {}}
                profile = profile_dict.get(employee.id, None)


                if profile and profile.job_status == 2: #Confirmed
                    balance = 999
                else:
                    year_start = date(credit_year, 1, 1)
                    year_end = date(credit_year, 12, 31)
                    emp_leaves = LeaveDA().get_employee_leave_by_date(year_start, year_end, employee.id)
                    leave_taken = self.__taken_leave(emp_leaves)
                    balance = settings.PROBATION_LEAVE - leave_taken
                    if balance <= 0:
                        balance = 0

                leave_details = {}
                for leave_type in leave_types:
                    leave_quota_dict = {
                        "leave_type_id": 0,
                        "leave_period_id": period_id,
                        "employee_id": employee.id,
                        "no_of_days_allotted": 0
                    }
                    leave_quota_dict['leave_type_id'] = leave_type.leave_type_id
                    if leave_type.leave_type_id == 1 and balance != 999 :
                        leave_quota_dict['no_of_days_allotted'] = balance
                    else:
                        leave_quota_dict['no_of_days_allotted'] = leave_type.default_no_of_leaves
                    LeaveDA().create_leave_quota(leave_quota_dict)

                    leave_details[leave_type.leave_type_name.replace(' ','')] = leave_quota_dict['no_of_days_allotted']
                emp_dict['leave_details'] = leave_details
                leave_quota_list.append(emp_dict)
                del emp_dict

            result['leave_quota'] = leave_quota_list

        except Exception as err:
            result["error"] = settings.ERROR_MSG['application_error']\
                .format(str(err), self.__logs.error(self.__exception.get_exception()))
        finally:
            return result

    def get_leave_quota(self, user_id, year):

        # method for listing employee leave quota for HR

        response = {"leave_quota" : [],
        "error" : None
        }
        try:
            leave_quota_list = []
            helper = LeaveHelperBL()
            leave_da = LeaveDA()
            obj_start = Utility().convert_string_to_date_time(str(year) + "-01-01", "%Y-%m-%d")
            role_id, role_name = UserDA().get_user_role_by_id(user_id)
            # check permission
            if not role_id in (2, "2"):
                response['error'] = settings.ERROR_MSG.get('no_permission')
                return response
            active_users = UserDA().get_all_active_users()
            leave_types = helper.get_leave_type_dict()
            # obj_date = date.today()
            leave_period = leave_da.get_leave_period_by_date(obj_start)
            if leave_period:
                all_leave_quota = leave_da.get_all_employees_leave_quota(leave_period.leave_period_id)
                if all_leave_quota:
                    for each in active_users:
                        user_leave_quota = all_leave_quota.filter(employee_id = each.id)
                        emp_details = {}
                        if user_leave_quota:
                            emp_details['emp_name'] = each.first_name+" "+each.last_name
                            emp_details['emp_id'] = each.id
                            emp_details['leave_period_id'] = leave_period.leave_period_id
                            emp_details['quota'] = {}
                            test_list = []
                            temp = {'general': 0,'official': 0,'comp_off': 0,'lop' : 0,'maternity' : 0 }
                            for leave_quota in user_leave_quota:
                                leave_type = leave_types.get(int(leave_quota.leave_type_id), '')
                                if str(leave_type).lower() == "general":
                                    temp['general'] = leave_quota.no_of_days_allotted
                                    temp['general_quota_id'] = leave_quota.quota_id
                                elif str(leave_type).lower() == "official":
                                    temp['official'] = leave_quota.no_of_days_allotted
                                    temp['official_quota_id'] = leave_quota.quota_id
                                elif str(leave_type).lower() == "comp off":
                                    temp['comp_off'] = leave_quota.no_of_days_allotted
                                    temp['comp_off_quota_id'] = leave_quota.quota_id
                                elif str(leave_type).lower() == "lop":
                                    temp['lop'] = leave_quota.no_of_days_allotted
                                    temp['lop_quota_id'] = leave_quota.quota_id
                                elif str(leave_type).lower() == "maternity":
                                    temp['maternity'] = leave_quota.no_of_days_allotted
                                    temp['maternity_quota_id'] = leave_quota.quota_id
                            test_list.append(temp)
                            emp_details['quota'] = test_list
                        if emp_details:
                            leave_quota_list.append(emp_details)
                    response['leave_quota'] = leave_quota_list
        except Exception as err:
            response["error"] = settings.ERROR_MSG['application_error']\
                .format(err, self.__log.error(self.__exception.get_exception()))
        return response

    def update_leave_quota(self,user_id, data):
        result = {"status" : 0,
                 "error" : None,
                "message" : None
                }
        try:
            leave_data = data
            role_id, role_name = UserDA().get_user_role_by_id(user_id)
            # check permission
            if role_id not in (2, "2"):
                result['error'] = settings.ERROR_MSG.get('no_permission')
                return result
            for each in leave_data:
                no_of_days = float(each['no_of_days_allocated'])
                if no_of_days < 0:
                    result['error'] = "Leave quota should be greater than or equal to zero."
                    return result
                LeaveDA().update_leave_quota_by_id(each['quota_id'], each['no_of_days_allocated'])
            result['message'] = "Leave quota updated successfully."
        except Exception as err:
            result["error"] = settings.ERROR_MSG['application_error']\
                .format(err, self.__log.error(self.__exception.get_exception()))
        return result
