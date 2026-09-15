import json
from types import SimpleNamespace
from datetime import datetime, date, timedelta


from django.conf import Settings, settings
from django.db import  DatabaseError, transaction
from django.http import response
from django.template import loader


from pTracker.common.utility import Utility
from pTracker.common.exception_handler import ExceptionHandler
from pTracker.common.logs import Logs

from pTracker.api.leave.leave_helper import LeaveHelperBL
from pTracker.api.leave.leave_reports_biz import LeaveReportsBL

from pTracker.dataaccess.ptracker_access.leave_da import LeaveDA
from pTracker.dataaccess.ptracker_access.user_da import UserDA
from pTracker.dataaccess.ptracker_access.holiday_da import HolidayDA
from pTracker.api.leave.leave_notification_biz import LeaveNotificationBL

from pTracker.settings import constants
from pTracker.notification_center.email_engine import Email
from pTracker.cronjobs.email_sender import send_email_notification



def new_dto():
    dto = SimpleNamespace()
    return dto

class CompOffBL():
    def __init__(self):
        self.__log = Logs()
        self.__exception = ExceptionHandler()
        self.__utility = Utility()


    def __create_comp_off_leave_request(self, comp_off, emp_id, status, user_id, comp_off_id):
        leave_request_data = {
            "type_id": comp_off.leave_type_id,
            "leave_period_id": comp_off.leave_period_id,
            "employee_id": emp_id,
            "reason": comp_off.reason,
            "length_days": settings.LEAVE_LENGTH['Fullday'],
            "start_date": comp_off.scheduled_date,
            "end_date": comp_off.scheduled_date,
            "status": status,  # Requested
            "approver": UserDA().get_lead_id_by_user(user_id),
            "comment": "",
            "notify": ""
        }
        leave_request_data['comp_off_id'] = comp_off_id
        leave_request = LeaveDA().create_leave_request(leave_request_data)
        return leave_request

    def __create_comp_off_leave(self, comp_off, leave_request, emp_id, status, comp_off_id, user_id, user_name):
        helper = LeaveHelperBL()
        date_time = datetime.now().strftime('%d/%m/%y %H:%M %p')
        leave_data = helper.get_leave_data_template()
        if leave_request:
            leave_data['leave_request_id'] = leave_request.request_id
            leave_data['leave_period_id'] = comp_off.leave_period_id
            leave_data['leave_date'] = comp_off.scheduled_date
            leave_data['employee_id'] = emp_id
            leave_data['leave_day_type'] = settings.LEAVE_DAY_TYPE['Fullday']
            leave_data['length_hours'] = settings.LEAVE_HOURS['Fullday']
            leave_data['type_id'] = comp_off.leave_type_id
            leave_data['status'] = status  # Requested
            leave = LeaveDA().create_leave(leave_data)
            leave_log = helper.get_leave_log_data_template()
            leave_log['action'] = "Leave request for the compensatory off id #{0} approved by {1} at {2}".format\
                (comp_off_id, user_name, date_time)
            leave_log['employee_id'] = user_id
            leave_log['request_id'] = leave.leave_request_id
            LeaveDA().create_leave_log(leave_log)

    def update_compensatory_leaves(self, data, user):
        response = {
            "message": "",
            "error": ""
        }
        email_content_dto = new_dto()
        approver_id = 0
        lead_name = ''
        emp_name = ''
        to_email = ''
        message = 'Compensatory Leave Request '
        try:
            helper = LeaveHelperBL()
            user_id = user.id
            user_name = user.first_name + " " + user.last_name
            req_type = data.get('req_type', '')
            comp_off_id = data.get('editId', 0)
            comp_off_log_data = helper.get_comp_off_log_data()
            comp_off_log_data['comp_off_id'] = comp_off_id
            comp_off_log_data['employee_id'] = user_id
            date_time = datetime.now().strftime('%d/%m/%y %I:%M %p')
            comp_off = LeaveDA().get_compensatory_leave_by_id(comp_off_id)
            leave_log = helper.get_leave_log_data_template()
            #APPROVE
            if req_type.upper() == 'APPROVE':
                emp_id = data.get('employee_id', 0)
                comment = data.get('comment', '')
                status = data.get('status', '')
                if not UserDA().is_team_member(emp_id, user_id):
                    response["error"] = settings.ERROR_MSG['no_permission']
                    return response

                comp_off_duration = 1 #compensatory leave can be applied for 1 day only
                leave_duration = 1 #compensatory leave can be applied for 1 day only
                if comp_off.leave_type_id == '5': #hard code to be removed for maternity leave
                    if leave_duration > settings.MAXIMUM_MATERNITY_LEAVE_DURATION:
                        response['error'] = 'Maximum leave duration for maternity is 180'
                        return response
                if leave_duration >  settings.MAXIMUM_COMP_LEAVE_DURATION:
                    response['error'] = f'''Maximum leave duration for the
                                            selected leave type is {settings.MAXIMUM_COMP_LEAVE_DURATION}'''
                    return response
                comp_off_request = LeaveDA().\
                    update_comp_off_request(comp_off_id, {"status":status, "comment": comment, 'approver_id': user_id})
                #To Do hard code to be removed
                if comp_off.is_flag and status == '2':
                    leave_request = self.__create_comp_off_leave_request(comp_off, emp_id, status, user_id, comp_off_id)
                    self.__create_comp_off_leave(comp_off, leave_request, emp_id, status, comp_off_id, user_id, user_name)

                if status == '2':
                    leave_qouta = LeaveDA().updateLeaveQuota(comp_off.leave_type_id,comp_off.employee_id,\
                        comp_off_duration,comp_off.leave_period_id)
                    d = datetime.now()
                    action = settings.COMP_LEAVE_ACTION_LOG[settings.LEAVE_REQUEST_STATUS['Approved']]\
                        .format(user_name, date_time)
                    response["message"] = "Request approved successfully"
                    email_content_dto.heading = "Compensatory Off Request Approved"
                    email_content_dto.status = 'approved'

                else:
                    action = settings.COMP_LEAVE_ACTION_LOG[settings.LEAVE_REQUEST_STATUS['Rejected']]\
                        .format(user_name, date_time)
                    response["message"] = "Request rejected successfully"
                    email_content_dto.heading = "Compensatory Off Request Rejected"
                    email_content_dto.status = "rejected"
                message = "Compensatory Off Request"

                employee = UserDA().get_user_by_id(comp_off.employee_id)
                leave_types = helper.get_leave_type_dict()
                email_content_dto.lead_name = user_name
                email_content_dto.emp_name = employee.first_name+ ' '+employee.last_name
                email_content_dto.start_date = comp_off.start_date.strftime("%d-%m-%Y")
                email_content_dto.message = message
                email_content_dto.no_of_days = '1 day' # compo off can be applied only for one day
                email_content_dto.comment = comment
                email_msg = LeaveNotificationBL().generate_email_message(email_content_dto)

                # remove comment for pro
                to_email = employee.email
                LeaveNotificationBL().send_leave_request_update_notification(email_msg, user_name, to_email,message)

            #CANCEL
            elif req_type.upper() == 'CANCEL':
                if comp_off.status in (2, '2'):
                    leave_qouta = LeaveDA().updateLeaveQuota(comp_off.leave_type_id,comp_off.employee_id,\
                        -1,comp_off.leave_period_id)
                comment = data.get('comment', '')
                status = settings.LEAVE_REQUEST_STATUS['Cancelled']
                LeaveDA().update_comp_off_request(comp_off_id, {"status": status, "comment": comment},\
                    comp_off.employee_id)

                cancel_leave_request = LeaveDA().get_leave_request_by_comp_off_id(comp_off_id)
                if cancel_leave_request: # cancel leave requests if scheduled
                    LeaveDA().update_leave_status(cancel_leave_request.request_id, \
                        settings.LEAVE_REQUEST_STATUS['Cancelled'], comment, user_id)
                    leave_log = helper.get_leave_log_data_template()
                    leave_log['action'] = "Leave request for the compensatory off id #{0} cancelled by {1} at {2}".format\
                            (comp_off_id, user_name, date_time)
                    leave_log['employee_id'] = comp_off.employee_id
                    leave_log['request_id'] = cancel_leave_request.request_id
                    LeaveDA().create_leave_log(leave_log)

                action = settings.COMP_LEAVE_ACTION_LOG[settings.LEAVE_REQUEST_STATUS['Cancelled']]\
                    .format(user_name, date_time)
                response["message"] = "Request Cancelled successfully"

            #EDIT
            elif req_type.upper() == 'EDIT':
                comp_off_data = {"leave_type_id": 0,"start_date": "", "end_date": "", "reason": ""}
                comp_off_data['leave_type_id'] = data.get('leave_type_id', None)
                comp_off_data['start_date'] = data.get('start_date', None)
                comp_off_data['end_date'] = data.get('end_date', None)
                comp_off_data['reason'] = data.get('reason', None)
                comp_off_data['is_flag'] = data.get('is_flag', 0)
                comp_off_data['scheduled_date'] = data.get('scheduled_date', None)

                dt_start = datetime.strptime(comp_off_data['start_date'], "%Y-%m-%d")
                dt_end = datetime.strptime(comp_off_data['end_date'], "%Y-%m-%d")
                leave_period = LeaveDA().get_leave_period_by_date(dt_start)

                if not helper.is_date_range_valid(dt_start, dt_end):
                    response['error'] = "Start date should be less than or equal to end date."
                    return response

                if not helper.is_date_range_in_same_year(dt_start, dt_end):
                    response['error'] = "Start date and end date should be in same year."
                    return response

                if helper.is_date_range_overlapped(dt_start, dt_end, user_id, comp_off_id):
                    response['error'] = "Your compensatory leave request dates overlapping with previous request."
                    return response

                if not leave_period:
                    response['error'] = f'''You can't apply for compensatory leave in selected leave period'''
                    return response

                err_msg = helper.is_valid_leave_duration(dt_start, dt_end, comp_off_data['leave_type_id'])
                if err_msg:
                    response['error'] = err_msg
                    return response


                dt_start = datetime.strptime(comp_off_data['start_date'], "%Y-%m-%d")
                dt_end = datetime.strptime(comp_off_data['end_date'], "%Y-%m-%d")
                off_days_length = helper.get_all_off_days_for_date_range(dt_start,dt_end)
                applied_leave_length = Utility().get_date_range(dt_start,dt_end)
                comp_off_data['no_of_days'] = len(applied_leave_length) - off_days_length
                LeaveDA().update_comp_off_request(comp_off_id, comp_off_data, user_id)
                action = settings.COMP_LEAVE_ACTION_LOG[5].format(user_name, datetime.now().strftime('%d/%m/%y %I:%M %p')) #update
                    # .format(user_name, date_time)
                response["message"] = "Request Updated successfully"
            comp_off_log_data['action'] = action
            comp_off_log = LeaveDA().create_comp_off_log(comp_off_log_data)

        except Exception as err:
            response["error"] = settings.ERROR_MSG['application_error']\
                .format(err, self.__log.error(self.__exception.get_exception()))
        return response

    def create_compensatory_leave(self, request, user):
        response = {"message": "", "error": ''}
        helper = LeaveHelperBL()
        email_content_dto = new_dto()
        approver_id = 0
        lead_name = ''
        emp_name = ''
        to_email = '' #TODO this will be delete in PRO
        message = 'Compensatory Off Request'
        try:
            user_id = user.id
            user_name = user.first_name + " " + user.last_name
            str_start_date = request.data.get("start_date", None)
            str_end_date = request.data.get("end_date", None)
            str_scheduled_date = request.data.get("scheduled_date", None)
            edit_id = request.data.get("edit_id", None)
            leave_type_id = request.data.get("leave_type_id", None)
            start_date = datetime.strptime(str_start_date, "%Y-%m-%d")
            end_date = datetime.strptime(str_end_date, "%Y-%m-%d")
            is_flag = int(request.data.get('is_flag', 0))

            leave_period = LeaveDA().get_leave_period_by_date(start_date)

            if not helper.is_date_range_valid(start_date, end_date):
                response['error'] = "Start date should be less than or equal to end date."
                return response

            if not helper.is_date_range_in_same_year(start_date, end_date):
                response['error'] = "Start date and end date should be in same year."
                return response

            if helper.is_date_range_overlapped(start_date, end_date, user_id, edit_id):
                response['error'] = f'''Your compensatory off request dates overlapping previous request.'''
                return response

            if not leave_period:
                response['error'] = f'''You can't apply for compensatory
                            leave in selected leave period'''
                return response

            err_msg = helper.is_valid_leave_duration(
                start_date, end_date, leave_type_id)
            if err_msg:
                response['error'] = err_msg
                return response

            comp_off_data = helper.get_comp_off_data_template()
            comp_off_data['start_date'] = str_start_date
            comp_off_data['end_date'] = str_end_date
            comp_off_data['leave_type_id'] = leave_type_id
            comp_off_data['reason'] = request.data.get("reason", None)
            comp_off_data['employee_id'] = user_id
            comp_off_data['leave_period_id'] = leave_period.leave_period_id
            comp_off_data['is_flag'] = is_flag
            comp_off_data['scheduled_date'] = str_scheduled_date
            lead_user = UserDA().get_my_lead(user_id)
            if lead_user:
                comp_off_data['approver_id'] = lead_user.lead_id
                lead = UserDA().get_user_by_id(lead_user.lead_id)
                lead_name = lead.first_name
                # remove comment for pro
                to_email = lead.email
            else:
                comp_off_data['approver_id'] = 0

            off_days_length = LeaveHelperBL().get_all_off_days_for_date_range(start_date, end_date)
            applied_leave_length = Utility().get_date_range(start_date, end_date)
            comp_off_data['no_of_days'] = len(
                applied_leave_length) - off_days_length

            with transaction.atomic():
                comp_off_request = LeaveDA().create_comp_off_request(comp_off_data)
                if comp_off_request:
                    comp_off_log_data = helper.get_comp_off_log_data()
                    comp_off_log_data['comp_off_id'] = comp_off_request.comp_off_id
                    action = settings.COMP_LEAVE_ACTION_LOG[settings.LEAVE_REQUEST_STATUS['Requested']]\
                        .format(user_name, datetime.now().strftime('%d/%m/%y %I:%M %p'))  # create
                    comp_off_log_data['action'] = action
                    comp_off_log_data['employee_id'] = user_id
                    comp_off_log = LeaveDA().create_comp_off_log(comp_off_log_data)
                response['message'] = "Compensatory off requested successfully."
            # mail
            leave_types = helper.get_leave_type_dict()
            email_content_dto.heading = "Compensatory Off Request"
            email_content_dto.lead_name = lead_name
            if start_date == end_date:
                email_content_dto.request = "Please  grant me compensatory off on {0} ".format(
                    start_date.strftime("%d/%m/%Y"))
            else:
                email_content_dto.request = "Please  grant me compensatory off from {0} to {1} ".format(
                    start_date.strftime("%d/%m/%Y"), end_date.strftime("%d/%m/%Y"))
            email_content_dto.emp_name = user_name
            email_content_dto.submitted_date = date.today().strftime("%d/%m/%Y")
            email_content_dto.status = 'Requested'
            email_content_dto.reason = comp_off_data['reason']
            email_content_dto.category = leave_types.get(
                int(comp_off_data['leave_type_id']), '')
            email_content_dto.start_date = start_date.strftime("%d/%m/%Y")
            email_content_dto.end_date = end_date.strftime("%d/%m/%Y")
            email_content_dto.link = f"{settings.BASE_URL}leave/compensatory-leaves"
            email_msg = LeaveNotificationBL().generate_leave_email_message(email_content_dto)
            LeaveNotificationBL().send_leave_request_notification(
                email_msg, user_name, to_email, message)

        except Exception as err:
            response["error"] = settings.ERROR_MSG['application_error']\
                .format(err, self.__log.error(self.__exception.get_exception()))
        return response


    def get_all_team_compensatory_leaves(self, user_id, emp_dict, leave_period):
        response = {
            "my_team_comp_off_requests": [],
            "error": None
        }
        team_requests = []
        try:
            role_id, role_name = UserDA().get_user_role_by_id(user_id)
            if not self.__is_access_to_team_comp_off_request(user_id, role_id):
                return response

            if role_id == 4:
                team_member_list = UserDA().get_current_team_members_by_lead_id(user_id)
            else:
                team_member_list = UserDA().get_all_active_users()
            team = []
            for each in team_member_list:
                team.append(each.id)
            if user_id in team:
                team.remove(user_id)
            all_comp_off_requests = LeaveDA()\
                .get_all_comp_off_requests_by_status(leave_period.leave_period_id)
            all_comp_off_log = LeaveDA().get_all_comp_off_logs()
            if team:
                for emp_id in team:
                    comp_off_requests = all_comp_off_requests.filter(employee_id=emp_id)

                    if comp_off_requests:

                        for each_request in comp_off_requests:
                            #if each_request.employee_id in team:
                            date_range = Utility().get_date_range(each_request.start_date,each_request.end_date)
                            no_of_days = 0
                            if date_range:
                                no_of_days = len(date_range)
                            log_list = []
                            emp_logs = all_comp_off_log.filter(comp_off_id=each_request.comp_off_id)
                            for log in emp_logs:
                                if each_request.comp_off_id ==  log.comp_off_id:
                                    log_list.append(log.action)
                            temp = {
                                'comp_off_id': each_request.comp_off_id,
                                'applied_date': each_request.applied_date,
                                'start_date': each_request.start_date,
                                'end_date': each_request.end_date,
                                'leave_type_id': each_request.leave_type_id,
                                'reason': each_request.reason,
                                'approver': emp_dict.get(each_request.approver_id, ''),
                                'emp_name': emp_dict.get(each_request.employee_id, ''),
                                'status': each_request.status,
                                'no_of_days': each_request.no_of_days,
                                'employee_id': each_request.employee_id,
                                'log_list': log_list,
                                'comment' : each_request.comment,
                                'scheduled_date' : each_request.scheduled_date
                            }
                            team_requests.append(temp)
                        if team_requests:
                            team_requests = sorted(team_requests, key = lambda i: i['comp_off_id'],reverse=True)
                response['my_team_comp_off_requests'] = team_requests

        except Exception as err:
            response["error"] = settings.ERROR_MSG['application_error']\
                .format(err, self.__log.error(self.__exception.get_exception()))
        return response

    def __is_access_to_team_comp_off_request(self, user_id, role_id):
        is_access = False
        if role_id in (1, 2, 3, 4, "1", "2", "3", "4"):
            is_access = True
        return is_access

    def get_all_compensatory_leave_request(self, user_id):
        response = {
            "my_comp_off_requests": [],
            "team_comp_off_requests": [],
            "error":None
        }
        try:
            leave_period = LeaveDA().get_leave_period_by_date(datetime.now())
            emps = UserDA().get_all_active_users()
            emp_dict = {}
            if emps:
                for emp in emps:
                    emp_dict[emp.id] = emp.first_name + " " + emp.last_name
            my_requests = self.get_all_my_compensatory_leaves(user_id, emp_dict,leave_period)
            response['my_comp_off_requests'] = my_requests['my_comp_off_requests']
            if my_requests['error']:
                response['error'] = my_requests['error']
            team_requests = self.get_all_team_compensatory_leaves(user_id, emp_dict,leave_period)
            response['team_comp_off_requests'] = team_requests['my_team_comp_off_requests']
            if team_requests['error']:
                response['error'] = team_requests['error']
        except Exception as err:
            response["error"] = settings.ERROR_MSG['application_error']\
                .format(err, self.__log.error(self.__exception.get_exception()))
        return response

    def get_all_my_compensatory_leaves(self, user_id, emp_dict, leave_period):
        response = {
            "my_comp_off_requests": [],
            "error": None
        }
        try:
            comp_off_request = []
            all_my_comp_offs = LeaveDA().get_all_my_comp_off_requests(user_id, leave_period.leave_period_id)
            all_comp_off_log = LeaveDA().get_all_comp_off_logs()
            for each in all_my_comp_offs:
                temp = {}
                log_list = []
                for log in all_comp_off_log:
                    if each.comp_off_id == log.comp_off_id:
                        log_list.append(log.action)
                date_range = Utility().get_date_range(each.start_date, each.end_date)
                no_of_days = 0
                if date_range:
                    no_of_days = len(date_range)
                temp['comp_off_id'] = each.comp_off_id
                temp['applied_date'] = each.applied_date
                temp['start_date'] = each.start_date
                temp['end_date'] = each.end_date
                temp['leave_type_id'] = each.leave_type_id
                temp['no_of_days'] = each.no_of_days
                temp['reason'] = each.reason
                temp['approver'] = emp_dict.get(each.approver_id, ''),
                temp['status'] = each.status
                temp['log_list'] = log_list
                temp['comment'] = each.comment
                temp['scheduled_date'] = each.scheduled_date
                comp_off_request.append(temp)
            response['my_comp_off_requests'] = comp_off_request
        except Exception as err:
            response["error"] = settings.ERROR_MSG['application_error']\
                .format(err, self.__log.error(self.__exception.get_exception()))
        return response

    def compensatory_leave_filter(self, request, user_id):
        response = {
            "team_request": None,
            "error": ""
        }
        try:
            leave_period = LeaveDA().get_leave_period_by_date(datetime.now())
            emps = UserDA().get_all_active_users()
            emp_dict = {}
            if emps:
                for emp in emps:
                    emp_dict[emp.id] = emp.first_name + " " + emp.last_name
            team_leave = self.get_all_team_compensatory_leaves(
                user_id, emp_dict, leave_period)
            selected_team = request.get('filter_data', '')
            selected_team_list = []
            for each in selected_team:
                selected_team_list.append(each['id'])
            filtered_data = list(filter(lambda x: x['employee_id']
                                        in selected_team_list, team_leave['my_team_comp_off_requests']))
            response['team_request'] = filtered_data
        except Exception as err:
            response["error"] = settings.ERROR_MSG['application_error']\
                .format(err, self.__log.error(self.__exception.get_exception()))
        return response

    def get_compo_off_form_dropdowns(self, user_id):
        response = {
            "error": None,
            "leave_type": [],
        }
        try:
            all_leave_types = []
            # leave types
            leave_types = LeaveDA().get_all_leave_types().exclude(leave_type_name='General')
            user_profile = UserDA().get_user_profile_by_id(user_id)
            if str(user_profile.gender).lower() == "male":
                leave_types = leave_types.exclude(leave_type_name='Maternity')
            if leave_types:
                for each in leave_types:
                    all_leave_types.append({"id": each.leave_type_id,
                                            "leave_type": each.leave_type_name})
                response['leave_type'] = all_leave_types
        except Exception as error:
            response["error"] = settings.ERROR_MSG['application_error']\
                .format(error, self.__log.error(self.__exception.get_exception()))
        return response

    def compo_off_date_validation(self,data,user_id):
        response = {"message": "",
                    "error": "",
                    "is_valid": 1
        }
        try:
            start_date = data.get("start_date",None)
            end_date = data.get("end_date",None)
            leave_type_id = data.get("type_id",None)
            edit_id = data.get("edit_id",None)
            start = datetime.strptime(start_date, "%Y-%m-%d")
            end = datetime.strptime(end_date, "%Y-%m-%d")
            duration = Utility().get_date_range(start, end)
            leave_period = LeaveDA().get_leave_period_by_date(start)
            if start.year != end.year:
                response['message'] = "Dates can't be in different years"
                response['is_valid'] = 0
                return response
            if start > end:
                response['message'] = "Invalid date range"
                response['is_valid'] = 0
                return response
            else:
                if leave_period is None:
                    response['message'] = f'''Contact HR you can't apply for
                                             compensatory leave in
                                            selected date period'''
                    response['is_valid'] = 0
                    return response
            if leave_type_id:
                if leave_type_id == '5': #hard code to be removed for maternity leave
                    if len(duration) > settings.MAXIMUM_MATERNITY_LEAVE_DURATION:
                        response['message'] = f'''Maximum leave duration for maternity is 180'''
                        response['is_valid'] = 0
                        return response
                else:
                    if len(duration) >  settings.MAXIMUM_COMP_LEAVE_DURATION:
                        response['message'] = f'''Maximum leave duration for the
                                                selected leave type is {settings.MAXIMUM_COMP_LEAVE_DURATION}'''
                        response['is_valid'] = 0
                        return response
            result = LeaveDA().get_comp_off_dates_overlap(start_date,end_date,user_id)
            if result:
                if edit_id:
                    result = result.exclude(comp_off_id=edit_id)
                    if result:
                        response['message'] = f'''Compensatory Off request dates
                                     overlapping with previous request'''
                        response['is_valid'] = 0
                        return response
                else:
                    response['message'] = f'''Compensatory Off request dates
                                        overlapping with previous request'''
                    response['is_valid'] = 0
                    return response
        except Exception as error:
            response["error"] = settings.ERROR_MSG['application_error']\
                .format(error, self.__log.error(self.__exception.get_exception()))
        return response

    def leave_request_date_validate(self, start_date, end_date, user_id, req_id = 0):
        response = {'message':'', 'error':''}
        try:
            result = LeaveDA().get_leave_date_overlap(start_date, end_date, user_id)
            if req_id:
                comp_off = LeaveDA().get_compensatory_leave_by_id(comp_off_id = req_id)
                if comp_off:
                    if str(comp_off.scheduled_date) == start_date:
                        return response
            if result:
                response['message'] = "dates overlapping with previous leave request dates"
        except Exception as error:
            response['error'] = settings.ERROR_MSG['application_error']\
                .format(error, self.__log.error(self.__exception.get_exception()))
        finally:
            return response
