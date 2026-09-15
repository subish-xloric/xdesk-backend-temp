import json
from types import SimpleNamespace
from datetime import datetime, date, timedelta
# import datetime

from django.conf import settings

from pTracker.common.utility import Utility
from pTracker.common.exception_handler import ExceptionHandler
from pTracker.common.logs import Logs

from pTracker.dataaccess.ptracker_access.leave_da import LeaveDA
from pTracker.dataaccess.ptracker_access.user_da import UserDA
from pTracker.api.leave.leave_biz import LeaveBL
from pTracker.api.leave.leave_helper import LeaveHelperBL
from pTracker.user_management.holiday_da import HolidayDA



def new_dto():
    dto = SimpleNamespace()
    return dto

class LeaveBL_V1():
    def __init__(self):
        self.__log = Logs()
        self.__exception = ExceptionHandler()
        self.__utility = Utility()

    def __exclude_leave_keys(self, data):
        entries_to_remove = ["log", "total_days", "request_id", "is_cancel", "date_applied", "leave_type"]
        for k in entries_to_remove:
            data.pop(k, None)
        return data

    def format_leave_request_response(self, result):
        if result.get("error"):
            result = {"error": result.get("error")}
        elif result.get("status"):
            result = {"message": result.get("status")}
        return result

    def format_my_leave_summary(self, user_id, page=1, emp_id=0):
        leaves = []
        result = {"status": 200}
        try:
            # get leave details
            if(emp_id):
                if(emp_id == user_id):
                    user_id = emp_id
                elif not UserDA().is_team_member(emp_id, user_id):
                    result["error"] = "You have no permission."
                    result['status'] = 403
                    return result
                user_id = emp_id
            current_date = date.today()
            period = LeaveDA().get_leave_period_by_date(current_date)
            if not period:
                result['error'] = "Invalid leave period."
                result['status'] = 499
                return result
            period = period.leave_period_id

            leave_requests = LeaveDA().get_leave_requests_by_user_id(user_id, period)
            # "notify_list": [2,3,4]
            LEAVE_REQUEST_STATUS = settings.MOBILE_LEAVE_REQUEST_STATUS
            min, max = Utility().cutomPageLimits(page)
            for leave_request in leave_requests[min:max]:
                temp = {}
                temp["duration"] = LeaveDA().get_leave_day_type(int(leave_request.request_id))
                temp['comment'] = leave_request.comment
                temp["leave_type_id"] = int(leave_request.type_id)
                temp['start_date'] = leave_request.start_date
                temp['end_date'] = leave_request.end_date
                temp['status'] = LEAVE_REQUEST_STATUS.get(leave_request.status)
                temp['no_of_days'] = leave_request.length_days
                temp['reason'] = leave_request.reason
                temp['leave_request_id'] = leave_request.request_id
                temp['approver_id'] = int(leave_request.approver)
                temp['approver_name'] = self.get_full_name_by_user_id(leave_request.approver)
                temp['notify_list'] = self.convert_to_list(leave_request.notify)
                leaves.append(temp)
            result["leaves"] = leaves
        except Exception as err:
            result['status'] = 499
            result["error"] = settings.ERROR_MSG['application_error']\
                .format(str(err), self.__log.error(self.__exception.get_exception()))
        return result

    def convert_to_list(self, data):
        li = []
        if data:
            li = list((data).split(','))
            li = [int(x) for x in li]
        return li

    def get_full_name_by_user_id(self, user_id):
        user = UserDA().get_user_by_id(user_id)
        if user:
            return user.first_name + ' ' + user.last_name
        else:
            return None

    def format_cancel_leave_request(self, data, type=0):
        try:
            leave_request= LeaveDA().get_leave_request(data.get("leave_request_id"))

            if type: # for approve and reject
                action = data.get("action", '')
                if action == "APPROVED":
                    status = 2
                elif action == "REJECTED":
                    status = 4
                data = {
                "req_id": data.get("leave_request_id"),
                "status":status,
                "emp_id":leave_request.employee_id,
                "comment":data.get("comment",''),
            }
            else:
                data = {
                "req_id": data.get("leave_request_id"),
                "status":3,
                "emp_id":leave_request.employee_id
            }
            return data
        except:
            return None

    def format_team_leave_request_data(self, user_id, page=1, status=None, include_only_direct_reporting = None):
        if include_only_direct_reporting:
            if include_only_direct_reporting.upper() == "TRUE":
                direct_reporting = 1
            else:
                direct_reporting = 0
        today = date.today()
        start_date= date(today.year, 1, 1)
        end_date= date(today.year, 12, 31)
        data = {
            "startDate": start_date,
            "endDate": end_date,
        }
        res = {}
        if status=="pending": #TODO
            # status = 1 #requested
            data["status"] = 1  #requested
        elif status=="verified":
            data["status__in"] = [2, 3, 4] #except requested
        else:
            res["leaves"] = []
            return res
        LEAVE_REQUEST_STATUS = settings.MOBILE_LEAVE_REQUEST_STATUS
        leave_request = LeaveBL().get_team_leave_summary(user_id, data, 1, direct_reporting)
        if leave_request:
            user_dic = {}
            team_members = UserDA().get_all_active_users()
            for user in team_members:
                user_dic[user.id] = user.first_name + " " + user.last_name
            min, max = Utility().cutomPageLimits(page)
            request_list = leave_request.get('leave_items', [])

            if page:
                request_list = leave_request.get('leave_items', [])[min:max]
            for row,each in  enumerate(request_list):
                each['duration'] = LeaveDA().get_leave_day_type( each["request_id"])
                each['no_of_days'] = each["total_days"]
                each["leave_request_id"] = each["request_id"]
                each["status"] = LEAVE_REQUEST_STATUS.get(each['status'])
                each["approver_name"] = user_dic.get(int(each["approver_id"]), "")
                each["notify_list"] = self.convert_to_list(each["notify_list"])
                each["leave_type_id"] = int(each.get("leave_type",0))
                each = self.__exclude_leave_keys(each)
                each["emp_image"] = self.__get_image_url(each.get("emp_id",0))
                request_list[row] = each
        # if request_list:
        #     request_list = sorted(request_list, key = lambda i: i['status'])
        res["leaves"] = request_list
        if res.get("error"):
            res = {"error": res.get("error"), "status": 499}
        return res

    def __get_image_url(self, user_id):
        img_url = UserDA().get_user_profile_by_id(user_id)
        if img_url:
            return f"{settings.DEFAULT_SITE_MEDIA_URL}{img_url.profile_photo}"
        else:
            return None
    
    def format_date_validation(self, start_date, end_date):
        return {'start_date':start_date, 'end_date':end_date}
    
    def leave_date_validation(self, data , user_id):
        response = {"msg": "", "is_valid": True, "status": 200}
        try:
            start_date = data.get('start_date', None)
            end_date = data.get('end_date', None)
            leave_type = data.get('type_id', None)
            edit_id = data.get('request_id', 0)
            leave_day_type = data.get('leave_day_type', None)
            start = datetime.strptime(start_date, "%Y-%m-%d")
            end = datetime.strptime(end_date, "%Y-%m-%d")
            duration = Utility().get_date_range(start, end)
            leave_period = LeaveDA().get_leave_period_by_date(start)
            if start.year != end.year:
                response['msg'] = "Leave start date and end date should be in the same year."
                response["is_valid"] = False
                response['status'] = 499
                return response

            if leave_period is None:
                response['msg'] = f'''You can't apply leave for this date range. Leave period is missing in system.'''
                response['status'] = 499
                response["is_valid"] = False
                return response

            if leave_type:
                leave_balance = self.get_user_leave_balance(leave_type, user_id, leave_period.leave_period_id, edit_id)

                if leave_balance is not None:
                    if leave_balance >= 0:
                        if float(leave_balance) < float(len(duration)):
                            if not (leave_balance == .5 and len(duration) == 1) :
                                response['msg'] = f'''Insufficient leave balance for selected leave type. Leave balance is {leave_balance}'''
                                response["is_valid"] = False
                                return response
                            if leave_balance == .5 and len(duration) == 1 and leave_day_type == '1':
                                response['msg'] = f'''Insufficient leave balance for selected leave type. Leave balance is{leave_balance}.'''
                                response["is_valid"] = False
                                response['status'] = 499
                                return response
                else:
                    response['msg'] = "You can't apply for leave right now. Please contact your respective LEAD or HR  "
                    response["is_valid"] = False
                    response['status'] = 499
                    return response
            if duration:
                if len(duration) > settings.MAXIMUM_LEAVE_DURATION:
                    response['msg'] = "Leave duration exceed maximum limit. Limit is {0}".format(settings.MAXIMUM_LEAVE_DURATION)
                    response["is_valid"] = False
                    response['status'] = 499
                    return response
            result = LeaveDA().get_leave_date_overlap(start_date, end_date, user_id)
            if result:
                if edit_id:
                    edit_excluded_result = result.exclude(
                        leave_request_id=edit_id)
                    if edit_excluded_result:
                        response['msg'] = f'''Leave dates are overlapping with previous leave request. Please change dates'''
                        response["is_valid"] = False
                        response['status'] = 499
                else:
                    response['msg'] = "dates overlapping with previous leave request dates"
                    response["is_valid"] = False
                    response['status'] = 499
                return response
            is_start_or_end_date_in_holiday = self.is_start_date_or_end_date_in_holiday(start, end)
            if is_start_or_end_date_in_holiday:
                response['message'] = "Start date or end date can't be a holiday"
                response["is_valid"] = False
                response['status'] = 499
                return response
        except Exception as err:
            response['status'] = 499
            response = { "error" : settings.ERROR_MSG['application_error']\
                .format(str(err), self.__log.error(self.__exception.get_exception())) }
            return response
        return response

    def format_notfy_list(self, notify):
        res = []
        if notify:
            for each in notify:
                res.append({"id":each})
        return res

    def get_user_leave_summary_by_emp_id(self, user_id, emp_id):
        response ={"error":'', "general":{}, "lop": {}, "official": {}, "compOff": {}, "maternity": {},"status": 200}
        try:
            permitted = False
            role_id, role_name = UserDA().get_user_role_by_id(user_id)
            is_team_member = UserDA().is_team_member(emp_id, user_id)
            if user_id == emp_id:
                permitted = True
            elif role_id in (1, 2, 3):
                permitted =  True
            elif is_team_member:
                permitted =  True
            if not permitted:
                response['error'] = settings.ERROR_MSG.get('access_denied')
                response['status'] = 403
                return response
            leave_period = LeaveDA().get_leave_period_by_date(datetime.now().date())
            if leave_period:
                leave_summary = LeaveHelperBL().generate_leave_summary(emp_id, leave_period.leave_period_id)
                if leave_summary:
                    response['general'] = leave_summary.get("General",{})
                    response['lop'] = leave_summary.get("LOP",{})
                    response['official'] = leave_summary.get("Official",{})
                    response['compOff'] = leave_summary.get("Comp_Off",{})
                    response['maternity'] = leave_summary.get("Maternity",{})

        except Exception as err:
            response['status'] = 499
            response = { "error" : settings.ERROR_MSG['application_error']\
                .format(str(err), self.__log.error(self.__exception.get_exception())) }
            return response
        return response

    def is_start_date_or_end_date_in_holiday(self, start_date, end_date):
        in_holiday = False
        date_list = [start_date, end_date ]
        holidays = HolidayDA().get_holidays_in_date_list(date_list)
        if holidays:
            in_holiday = True
        return in_holiday