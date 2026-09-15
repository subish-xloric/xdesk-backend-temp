from http.client import error
import json
from types import SimpleNamespace
from datetime import datetime, date, timedelta
# import datetime

from django.conf import Settings, settings
from django.db import  DatabaseError, transaction
from django.http import response
from django.template import loader

from pTracker.common.utility import Utility
from pTracker.common.exception_handler import ExceptionHandler
from pTracker.common.logs import Logs

from pTracker.api.leave.leave_helper import LeaveHelperBL
from pTracker.api.leave.leave_reports_biz import LeaveReportsBL
from pTracker.api.leave.comp_off_biz import CompOffBL
from pTracker.api.attendance.attendance_biz import AttendanceBL

from pTracker.dataaccess.ptracker_access.leave_da import LeaveDA
from pTracker.dataaccess.ptracker_access.user_da import UserDA
from pTracker.dataaccess.ptracker_access.holiday_da import HolidayDA
from pTracker.api.leave.leave_notification_biz import LeaveNotificationBL
from pTracker.settings import constants
from pTracker.notification_center.email_engine import Email
from pTracker.common.utility import Utility


def new_dto():
    dto = SimpleNamespace()
    return dto

class LeaveBL():
    def __init__(self):
        self.__log = Logs()
        self.__exception = ExceptionHandler()
        self.__utility = Utility()

    def get_team_leave_calendar(self, user_id):
        return LeaveHelperBL().get_team_leave_calendar(user_id)

    def fill_leave_apply_form_dropdowns(self):
        return LeaveHelperBL().fill_leave_apply_form_dropdowns()

    def get_user_leave_summary(self, user_id):
        result = {'error': None, 'summary': None, 'leave_items': []}
        temp = {}
        log_list = []
        type_name = None
        try:
            # get leave details
            current_date = date.today()
            period = LeaveDA().get_leave_period_by_date(current_date)
            if not period:
                result['error'] = "Invalid leave period."
                return result
            period = period.leave_period_id
            result['summary'] = LeaveHelperBL().generate_leave_summary(user_id, period)

            leave_requests = LeaveDA().get_leave_requests_by_user_id(user_id, period)
            # log_data = LeaveDA().get_leave_action_log_()
            for leave_request in leave_requests:
                log_list = []
                temp = {}
                is_cancel = 0

                log_data = LeaveDA().get_leave_log_by_req_id(leave_request.request_id)
                for log in log_data:
                    if int(log.request_id) == leave_request.request_id:
                        log_list.append(log.action)

                if leave_request.status in (1, 2, '1', '2'):
                    if leave_request.start_date >= current_date:
                        is_cancel = 1
                temp['is_cancel'] = is_cancel
                temp['comment'] = leave_request.comment
                temp['date_applied'] = leave_request.date_applied
                temp['start_date'] = leave_request.start_date
                temp['end_date'] = leave_request.end_date
                temp['leave_type'] = leave_request.type_id
                temp['status'] = leave_request.status
                temp['total_days'] = leave_request.length_days
                temp['reason'] = leave_request.reason
                temp['request_id'] = leave_request.request_id
                temp['emp_id'] = leave_request.employee_id
                temp['log'] = log_list
                result["leave_items"].append(temp)
        except Exception as err:
            result["error"] = settings.ERROR_MSG['application_error']\
                .format(str(err), self.__log.error(self.__exception.get_exception()))
        return result

    def leave_date_validation(self, request, user_id):
        return LeaveHelperBL().leave_date_validation(request, user_id)


    def __get_notification_list(self, notify, approver_id):
        notify_list = []
        if notify:
            for each_user in notify:
                notify_list.append(str(each_user['id']))
            notify_list.append(str(approver_id))
            notify_list = list(set(notify_list))
        return str(','.join(notify_list))

    def create_leave_request(self, request, user, is_mobile=0):
        response = {'status': "", "error": "", "status_code": 200}
        helper = LeaveHelperBL()
        leave_period_id = 0
        email_content_dto = new_dto()
        lead_name = ''
        emp_name = ''
        to_email = ''  #TODO this will be delete in PRO
        mail_subject = ' Leave Request'

        try:
            length_hours = settings.LEAVE_HOURS['Fullday']
            user_id = user.id
            user_name = user.first_name + " " + user.last_name
            validation = helper.leave_date_validation(request, user_id)
            if validation['message']:
                response['error'] = validation['message']
                response['status_code'] = 499
                return response
            approver_id = UserDA().get_lead_id_by_user(user_id)
            start_date = request.data.get('start_date', None)
            end_date = request.data.get('end_date', None)
            leave_type_id = request.data.get('type_id', 0)
            notify = request.data.get('notify', None)
            leave_day_type = request.data.get('leave_day_type', None)

            dt_start = datetime.strptime(start_date, "%Y-%m-%d")
            dt_end = datetime.strptime(end_date, "%Y-%m-%d")
            date_range = Utility().get_date_range(dt_start, dt_end)

            leave_period = LeaveDA().get_leave_period_by_date(dt_start)  # current leave period
            if leave_period:
                leave_period_id = leave_period.leave_period_id

            leave_request_data = helper.get_leave_request_data_template()
            leave_request_data['start_date'] = start_date
            leave_request_data['end_date'] = end_date
            leave_request_data['leave_period_id'] = leave_period_id
            leave_request_data['type_id'] = leave_type_id
            leave_request_data['employee_id'] = user_id
            leave_request_data['reason'] = request.data.get('reason', "")
            leave_request_data['approver'] = approver_id
            leave_request_data['notify'] = self.__get_notification_list(notify, approver_id)
            leave_request_data['length_days'] = len(date_range)
            no_of_days = leave_request_data['length_days']
            if is_mobile:
                if no_of_days>1:
                    day_name = 'days'
                else:
                    day_name = 'day'
            if leave_day_type:
                leave_request_data['length_days'] = 1
                no_of_days = leave_request_data['length_days']
                if leave_day_type != '1':
                    leave_request_data['length_days'] = .5
                    length_hours = settings.LEAVE_HOURS['Halfday']
                    if leave_day_type == '2':
                        no_of_days = str(leave_request_data['length_days']) + '({0})'\
                            .format('Morning')
                    else:
                        no_of_days = str(leave_request_data['length_days']) + '({0})'\
                            .format('Afternoon')
            else:
                leave_day_type = 1

            with transaction.atomic():
                leave_request = LeaveDA().create_leave_request(leave_request_data)
                if leave_request:
                    for each_date in date_range:
                        leave_data = helper.get_leave_data_template()
                        leave_data['type_id'] = leave_type_id
                        leave_data['leave_day_type'] = leave_day_type
                        leave_data['leave_period_id'] = leave_period_id
                        leave_data['leave_date'] = each_date.strftime("%Y-%m-%d")
                        leave_data['length_hours'] = length_hours
                        leave_data['leave_request_id'] = leave_request.request_id
                        leave_data['employee_id'] = user_id
                        leave = LeaveDA().create_leave(leave_data)

                    leave_log = helper.get_leave_log_data_template()
                    leave_log['employee_id'] = user_id
                    leave_log['request_id'] = leave_request.request_id
                    action = settings.LEAVE_ACTION_LOG[settings.\
                                LEAVE_REQUEST_STATUS['Requested']].format(user_name,\
                                        datetime.now().strftime('%d/%m/%y %I:%M %p'))
                    leave_log['action'] = action
                    leave_log = LeaveDA().create_leave_log(leave_log)
                    response['status'] = "Leave requested successfully."
            # To Do :Notification mail
            leave_types = helper.get_leave_type_dict()
            email_content_dto, cc_addresses, to_email = LeaveNotificationBL()\
                .setup_leave_request_email_content\
                    (user_id, leave_types, start_date, end_date, dt_start, dt_end, user_name, \
                        leave_request_data, notify, no_of_days)

            email_msg = LeaveNotificationBL().generate_leave_email_message(email_content_dto)
            LeaveNotificationBL().send_leave_request_notification(email_msg, user_name, to_email, mail_subject, cc_addresses)
            if is_mobile:
                approver_name = ''
                emp_image= ''
                approver_details = UserDA().get_user_by_id(approver_id)
                if approver_details:
                    approver_name = approver_details.first_name + ' ' + approver_details.last_name
                user_profile = UserDA().get_user_profile_by_id(leave_request.employee_id)
                if user_profile:
                    emp_image =  f"{settings.DEFAULT_SITE_MEDIA_URL}{user_profile.profile_photo}"
                title = "Notification from DM Desk"
                msg = user_name + " has applied leave for " + str(len(date_range)) +' '+ day_name +'.'
                if leave_day_type in (2, 3, '2', '3'):
                    msg = user.first_name + ' ' + user.last_name +" has applied for a half day leave"
                try:
                    duration = int(leave_day_type)
                except :
                    duration = 0

                data =  {
                "notificationType" : "LEAVE_REQUEST",
                "notificationInfo" : {
                    "id": leave_request.request_id,
                    "comment":leave_request.comment,
                    "start_date": leave_request.start_date,
                    "end_date": leave_request.end_date,
                    "status": settings.MOBILE_LEAVE_REQUEST_STATUS[leave_request.status],
                    "reason": request.data.get('reason', ""),
                    "emp_id": leave_request.employee_id,
                    "approver_id": leave_request.approver,
                    "notify_list": self.__get_notification_list(notify, approver_id),
                    "emp_name": user.first_name + ' ' + user.last_name,
                    "duration": duration,
                    "no_of_days": leave_request_data['length_days'],
                    "leave_request_id": leave_request.request_id,
                    "approver_name": approver_name,
                    "leave_type_id": leave_type_id,
                    "emp_image": emp_image
                    }
                }
                LeaveNotificationBL().send_single_push_notification(approver_id, title, msg, sound="default", extra_kwargs=data)

        except Exception as err:
            response['status_code'] = 499
            response["error"] = settings.ERROR_MSG['application_error']\
                .format(str(err), self.__log.error(self.__exception.get_exception()))
        return response

    def update_leave_status(self, data, user, is_mobile= 1):
        result = {'error': None, 'success': None, "status": 200}
        leave_log = {}
        action_log = ''
        email_content_dto = new_dto()
        approver_id = 0
        lead_name = ''
        emp_name = ''
        to_email = ''
        message = 'leave request '
        cc_adresses = []
        try:
            user_id = user.id
            user_name = user.first_name + " " + user.last_name
            req_id = int(data.get('req_id', 0))
            status_id = int(data.get('status', 0))
            emp_id = int(data.get('emp_id', 0))
            comment = data.get('comment', '')
            permitted = self.__check_status_change_permission(user_id, status_id, emp_id)
            if not permitted:
                result["error"] = settings.ERROR_MSG.get('access_denied')
                result['status'] = 403
                return result

            if req_id and status_id:
                #TODO confirm with dev team
                leave_request = LeaveDA().get_leave_request(req_id)
                if leave_request:
                    if leave_request.status == 3:
                        result['success'] = "Leave Request Already Cancelled, Not Able To Process."
                        result['status'] = 499
                        return result
                    if leave_request.status == status_id:
                        result['success'] = "Nothing To Change."
                        result['status'] = 499
                        return result
                status = LeaveDA().update_leave_status(req_id, status_id, comment, user_id)

            if status:
                leave_log['employee_id'] = user_id
                leave_log['request_id'] = req_id
                d = datetime.now().strftime('%d/%m/%y %I:%M %p')
                action = settings.LEAVE_ACTION_LOG[status_id].format(user_name, d)
                leave_log['action'] = action
                leave_log = LeaveDA().create_leave_log(leave_log)

                result['success'] = action
                # notification mail
                leave_request = LeaveDA().get_leave_request(req_id)
                cc_adresses = LeaveHelperBL().get_cc_adresses(leave_request.notify, user_id)
                employee = UserDA().get_user_by_id(emp_id)
                email_content_dto.lead_name = user_name
                email_content_dto.emp_name = employee.first_name + ' '+employee.last_name
                email_content_dto.start_date = leave_request.start_date.strftime(
                    "%d/%m/%Y")
                if comment:
                    email_content_dto.comment = comment
                else:
                    email_content_dto.comment = ''
                no_days = str(int(leave_request.length_days)) + ' ' + 'days'

                if int(leave_request.length_days) == 1:
                    no_days = '1 day'
                elif int(leave_request.length_days) < 1:
                    no_days = '.5 day'

                email_content_dto.no_of_days = no_days
                #TODO Confirm with Dev
                if status_id in (2, 4, '2', '4'):
                    if status_id == 2:
                        email_content_dto.heading = 'Leave Request Approved'
                        email_content_dto.status = 'approved'
                        notificationType = "LEAVE_APPROVED"
                    if status_id == 4:
                        email_content_dto.heading = 'Leave Request Rejected'
                        email_content_dto.status = 'rejected'
                        notificationType = "LEAVE_REJECTED"
                    email_content_dto.message = message
                    email_msg = LeaveNotificationBL()\
                        .generate_email_message(email_content_dto)
                    to_email = employee.email
                    LeaveNotificationBL()\
                        .send_leave_request_update_notification(email_msg, user_name, to_email, email_content_dto.heading, cc_adresses) #cc_adresses TODO
                    if is_mobile:
                        emp_image= ''
                        leave_day_type = LeaveDA().get_leave_day_type(leave_request.request_id)
                        if leave_day_type is None:
                            leave_day_type = 1 # in case of full day
                        user_profile = UserDA().get_user_profile_by_id(leave_request.employee_id)
                        if user_profile:
                            emp_image =  f"{settings.DEFAULT_SITE_MEDIA_URL}{user_profile.profile_photo}"
                        title = "Notification from DM Desk"
                        msg = user_name + " has "+ email_content_dto.status +" your leave request."
                        data =  {
                        "notificationType" : notificationType,
                        "notificationInfo" : {
                            "id": leave_request.request_id,
                            "comment":leave_request.comment,
                            "start_date": leave_request.start_date.strftime("%Y-%m-%d"),
                            "end_date": leave_request.end_date.strftime("%Y-%m-%d"),
                            "status": settings.MOBILE_LEAVE_REQUEST_STATUS[leave_request.status],
                            "reason": leave_request.reason,
                            "emp_id": leave_request.employee_id,
                            "approver_id": user_id,
                            "notify_list": leave_request.notify,
                            "emp_name": employee.first_name + ' ' + employee.last_name,
                            "duration": int(leave_day_type),
                            "no_of_days": str(leave_request.length_days),
                            "leave_request_id": leave_request.request_id,
                            "approver_name": user_name,
                            "leave_type_id": leave_request.type_id,
                            "emp_image": emp_image
                            }
                        }
                        LeaveNotificationBL().send_single_push_notification(leave_request.employee_id, title, msg, sound="default", extra_kwargs=data)

        except Exception as err:
            result['status'] = 499
            result["error"] = settings.ERROR_MSG['application_error']\
                .format(str(err), self.__log.error(self.__exception.get_exception()))
        return result

    def get_leave_request_by_id(self, data, user_id):
        response = {"data": [], "error": ""}
        try:
            user_id = int(user_id)
            request_id = data.get('id', 0)
            permitted = False
            if not request_id:
                response["error"] = "Something went wrong, Please try again."
                return response
            leave_request = LeaveDA().get_leave_request(request_id)
            if not leave_request:
                response['error'] = "Invalid  Request ID."
                return response

            if leave_request.employee_id != user_id:
                response["error"] = settings.ERROR_MSG.get('access_denied')
                return response

            notify = leave_request.notify
            supervisors, error = UserDA().get_all_supervisors()
            if supervisors:
                temp_list = []
                for supervisor in supervisors:
                    if str(supervisor[0]) in notify:
                        emp_dict = {"id": supervisor[0], "name": supervisor[1] + " " + supervisor[2]}
                        temp_list.append(emp_dict)
                        del emp_dict

            leave_day_type = LeaveDA().get_leave_day_type(leave_request.request_id)
            request_data = {
                'request_id': leave_request.request_id,
                "type_id": leave_request.type_id,
                "leave_day_type": leave_day_type,
                "start_date": leave_request.start_date.strftime("%Y-%m-%d"),
                "end_date": leave_request.end_date.strftime("%Y-%m-%d"),
                "reason": leave_request.reason,
                "notify": temp_list
            }
            response['data'] = request_data
            return response
        except Exception as err:
            response["error"] = settings.ERROR_MSG['application_error']\
                .format(err, self.__log.error(self.__exception.get_exception()))
        return response

    def update_leave_request(self, request, user):
        response = {'status': "", "error": "", "status_code": 200}
        helper = LeaveHelperBL()
        leave_period_id = 0
        try:
            user_id = user.id
            user_name = user.first_name + " " + user.last_name
            edit_request_id = request.data.get('request_id', None)
            leave_request = LeaveDA().get_leave_request(edit_request_id)
            if not leave_request:
                response['error'] = "Invalid leave request."
                response['status_code'] = 499
                return response

            if leave_request.employee_id != user_id:
                response['error'] = settings.ERROR_MSG.get('no_permission')
                response['status_code'] = 403
                return response

            validation = helper.leave_date_validation(request, user_id)
            if validation['message']:
                response['error'] = validation['message']
                response['status_code'] = 499
                return response

            length_hours = settings.LEAVE_HOURS['Fullday']
            approver_id = UserDA().get_lead_id_by_user(user_id)

            start_date = request.data.get('start_date', None)
            end_date = request.data.get('end_date', None)
            leave_type_id = request.data.get('type_id', 0)
            notify = request.data.get('notify', None)
            leave_day_type = request.data.get('leave_day_type', None)

            dt_start = datetime.strptime(start_date, "%Y-%m-%d")
            dt_end = datetime.strptime(end_date, "%Y-%m-%d")
            date_range = Utility().get_date_range(dt_start, dt_end)
            leave_period = LeaveDA().get_leave_period_by_date(dt_start)  # current leave period
            if leave_period:
                leave_period_id = leave_period.leave_period_id
            leave_request_data = helper.get_leave_request_data_template()
            leave_request_data['start_date'] = start_date
            leave_request_data['leave_period_id'] = leave_period_id
            leave_request_data['type_id'] = leave_type_id
            leave_request_data['employee_id'] = user_id
            leave_request_data['reason'] = request.data.get('reason', "")
            leave_request_data['end_date'] = end_date
            leave_request_data['approver'] = approver_id
            leave_request_data['notify'] = self.__get_notification_list(notify, approver_id)
            leave_request_data['length_days'] = len(date_range)
            if leave_day_type:
                if int(leave_day_type) != 1:
                    leave_request_data['length_days'] = .5
                    length_hours = settings.LEAVE_HOURS['Halfday']
                else:
                    leave_request_data['length_days'] = 1
                    length_hours = settings.LEAVE_HOURS['Fullday']
            else:
                leave_day_type = 1
            with transaction.atomic():
                leave_request = LeaveDA().update_leave_request(edit_request_id, leave_request_data)
                if leave_request:
                    LeaveDA().delete_leaves(edit_request_id)
                    for each_date in date_range:
                        leave_data = helper.get_leave_data_template()
                        leave_data['type_id'] = leave_type_id
                        leave_data['leave_day_type'] = leave_day_type
                        leave_data['leave_period_id'] = leave_period_id
                        leave_data['leave_date'] = each_date.strftime("%Y-%m-%d")
                        leave_data['length_hours'] = length_hours
                        leave_data['leave_request_id'] = edit_request_id
                        leave_data['employee_id'] = user_id
                        leave = LeaveDA().create_leave(leave_data)
                    leave_log = helper.get_leave_log_data_template()
                    leave_log['employee_id'] = user_id
                    leave_log['request_id'] = edit_request_id
                    action = settings.LEAVE_ACTION_LOG[5].format(user_name, datetime.now().strftime('%d/%m/%y %I:%M %p')) #update
                    leave_log['action'] = action
                    leave_log = LeaveDA().create_leave_log(leave_log)
                    response['status'] = "Leave requested edited successfully"
        except Exception as error:
            response['status_code'] = 499
            response["error"] = settings.ERROR_MSG['application_error']\
                .format(error, self.__log.error(self.__exception.get_exception()))
        return response

    def team_leave_dropdowns(self, user_id):
        members_list = []
        result = {'error': None, 'status': [], 'team_members': []}
        try:
            if user_id:
                role_id, role_name = UserDA().get_user_role_by_id(user_id)
                if role_id not in (1, 2, 3, 4, "1", "2", "3", "4"):
                    result['error'] = settings.ERROR_MSG.get('access_denied')
                    return result
                if role_id in (1, 2, 3):
                    members_list = UserDA().get_all_active_users()
                else:
                    members_list = UserDA().get_current_team_members_by_lead_id(user_id)
                for each in members_list:
                    if each.id == user_id:
                        continue
                    member = {}
                    member = {'label': each.first_name + ' ' + each.last_name, 'value': each.id}
                    result['team_members'].append(member)
                    # status list
                for each in settings.LEAVE_REQUEST_STATUS.items():
                    result['status'].append({'label': each[0], 'value': each[1]})

        except Exception as err:
            result["error"] = settings.ERROR_MSG['application_error']\
                .format(err, self.__log.error(self.__exception.get_exception()))
        return result

    def get_team_leave_summary(self, user_id, data, is_mobile=0, direct_reporting =0):
        result = {'error': None, 'summary': None, 'leave_items': []}
        try:
            temp = {}
            user_dic = {}

            role_id, role_name = UserDA().get_user_role_by_id(user_id)
            # check permission
            if role_id not in (1, 2, 3, 4, "1", "2", "3", "4"):
                result["error"] = settings.ERROR_MSG.get('access_denied')
                return result

            emp_id = data.get('emp_id', 0)
            status = int(data.get('status', 0))
            filter_date = data.get('month', 0)
            startDate = data.get('startDate', 0)
            endDate = data.get('endDate', 0)
            period_filter = data.get('periodfilter',0)

            obj_start = self.__utility.convert_string_to_date_time(startDate, "%Y-%m-%d")
            obj_end = self.__utility.convert_string_to_date_time(endDate, "%Y-%m-%d")
            if filter_date:
                month = int(filter_date.split('_')[0])
                year = int(filter_date.split('_')[1])
                startDate = str(year) + "-" + str(month) + "-01"
                obj_start = self.__utility.convert_string_to_date_time(startDate, "%Y-%m-%d")
                obj_end = self.__utility.get_last_day_of_month(obj_start)

            period = LeaveDA().get_leave_period_by_date(obj_start)
            leave_details =self.get_all_halfday_leaves_detail_dict_by_period_id(period.leave_period_id)
            if period:
                period = period.leave_period_id
                if emp_id:
                    if not UserDA().is_team_member(emp_id, user_id):
                        result["error"] = settings.ERROR_MSG.get('access_denied')
                        return result

                    leave_data = LeaveDA().get_team_leaves_by_user_id(emp_id, period)
                    user = UserDA().get_user_by_id(emp_id)
                else:
                    leave_data = LeaveDA().get_all_leave_requests_by_period(period)
                    if is_mobile and leave_data:
                        leave_data = leave_data.order_by('-start_date')
                    if role_id in (1, 2, 3):
                        team_members = UserDA().get_all_active_users()
                    else:
                        team_members = UserDA().get_current_team_members_by_lead_id(user_id)
                    if is_mobile and direct_reporting:
                        team_members = UserDA().get_current_team_members_by_lead_id(user_id)
                    team_members_id_list = []
                    for user in team_members:
                        user_dic[user.id] = user.first_name + " " + user.last_name
                        if user.id == user_id:
                            continue
                        team_members_id_list.append(user.id)
                    leave_data = leave_data.filter(employee_id__in=team_members_id_list)
                if leave_data:
                    if period_filter == 'LEAVE DATE':
                        leave_data1 = leave_data.filter(start_date__month=month, start_date__year = year)
                        leave_data2 = leave_data.filter(end_date__month=month, end_date__year = year)
                        leave_data = (leave_data1 | leave_data2).distinct()
                    else:
                        leave_data = leave_data.filter(date_applied__gte=obj_start, date_applied__lte=obj_end)
                    if status:
                        # filter data if status is not null
                        leave_data = leave_data.filter(status=status)
                    #for mobile
                    if is_mobile:
                        status_in = data.get("status__in",0)
                        if status_in: #TODO
                            leave_data = leave_data.filter(status__in=status_in)

                    for row in leave_data:
                        log_list = []
                        temp = {}
                        is_cancel = 0

                        log_data = LeaveDA().get_leave_log_by_req_id(row.request_id)
                        for log in log_data:
                                if int(log.request_id) == row.request_id:
                                    log_list.append(log.action)

                        if row.status in (1, 2, '1', '2'):
                            is_cancel = 1
                        temp['is_cancel'] = is_cancel
                        temp['comment'] = row.comment
                        temp['date_applied'] = row.date_applied
                        temp['start_date'] = row.start_date
                        temp['end_date'] = row.end_date
                        temp['leave_type'] = row.type_id
                        temp['status'] = row.status
                        temp['total_days'] = row.length_days
                        temp['reason'] = row.reason
                        temp['request_id'] = row.request_id
                        temp['emp_id'] = row.employee_id
                        temp['log'] = log_list
                        temp["approver_id"] = row.approver
                        temp["notify_list"] = row.notify

                        leave = leave_details.get(row.request_id, None)
                        if leave:
                            if leave.leave_day_type == settings.LEAVE_DAY_TYPE['Halfday(fornoon)']:
                                temp['leave_section'] = '(AM)'
                            else:
                                temp['leave_section'] = '(PM)'
                        else:
                            temp['leave_section'] = ''

                        if emp_id:
                            temp['emp_name'] = user.first_name + ' ' + user.last_name
                        else:
                            temp['emp_name'] = user_dic.get(row.employee_id)
                        result["leave_items"].append(temp)
                result['summary'] = LeaveHelperBL().generate_leave_summary(emp_id, period)
        except Exception as err:
            result["error"] = str(settings.ERROR_MSG['application_error'])\
                .format(str(err), str(self.__log.error(self.__exception.get_exception())))
        return result

    def __check_status_change_permission(self, user_id, status_id, emp_id):
        # permission to change leave request status
        permitted = False
        if status_id == 3:
            if emp_id == user_id:
                permitted = True
        if UserDA().is_team_member(emp_id, user_id):
            permitted = True
        return permitted

    def leave_report_dropdowns(self, user, data):
        response = {
            'error': None,
            'members_list': [],
            'leave_types': [],
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
            # get all leave types
            leave_type = LeaveDA().get_all_leave_types()
            for each in leave_type:
                    l_type = {}
                    l_type = {'label': each.leave_type_name ,
                        'value': each.leave_type_id
                    }
                    response['leave_types'].append(l_type)
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

    def leave_report_list(self, data, user_id):
        response = { 'error': None, 'reports': [] }
        try:
            permitted = False
            role_id, role_name = UserDA().get_user_role_by_id(user_id)
            if role_id in (1, 2, 3, 4):
                permitted =  True
            if not permitted:
                response['error'] = settings.ERROR_MSG.get('access_denied')
                return response
            employee_list = data.get('employees', None)
            custom_date_range = data.get('custom_date', None)
            startDate = custom_date_range.get('startDate', 0)
            endDate = custom_date_range.get('endDate', 0)
            month = data.get('month', None)
            year = data.get('year', None)
            lead = data.get('lead', None)
            leave_type = data.get('type', None)
            if leave_type in (0,'0'):
                leave_type = None
            current_date = date.today()
            period = LeaveDA().get_leave_period_by_date(current_date)
            period = period.leave_period_id
            if employee_list:
                result_list = []
                for each in employee_list:
                    user = UserDA().get_user_by_id(each.get('value'))
                    leave_data = self.__filter_leave_report(user.id, startDate, endDate,\
                        month, year, leave_type)
                    if leave_data:
                        result_list.append(self.__format_leave_reports(leave_data, user))
                response['reports'] = result_list

            else:
                if lead:
                    user_id = int(lead)
                    team_members = UserDA().get_current_team_members_by_lead_id(user_id)
                    user = UserDA().get_user_by_id(user_id)
                    team_members.append(user)
                else:
                    team_members = UserDA().get_all_active_users()
                result_list = []
                for each in team_members:
                    leave_data = self.__filter_leave_report(each.id, startDate, endDate,\
                        month, year, leave_type)
                    if leave_data:
                        result_list.append(self.__format_leave_reports(leave_data, each))
                response['reports'] = result_list
        except Exception as err:
           response["error"] = settings.ERROR_MSG['application_error']\
                .format(err, self.__log.error(self.__exception.get_exception()))
        return response

    def __filter_leave_report(self,user_id, start_date='', end_date='', \
        month='', year='', leave_type=''):
        current_date = date.today()
        obj_start = Utility().convert_string_to_date_time(start_date, "%Y-%m-%d")
        obj_end = Utility().convert_string_to_date_time(end_date, "%Y-%m-%d")
        # change period if start date is not null
        if start_date:
            period = LeaveDA().get_leave_period_by_date(obj_start).leave_period_id
        # change period if year is not null
        elif year:
            current_date = datetime(int(year),1,1)
            period = LeaveDA().get_leave_period_by_date(current_date).leave_period_id
        # change period if both start date and year is null
        else:
            period = LeaveDA().get_leave_period_by_date(current_date).leave_period_id
        # get leave reports from leave request table
        leave_data = LeaveDA().get_team_leaves_by_user_id(user_id, period)
        # filter leave reports if leave type is not null
        if leave_type:
            leave_data = leave_data.filter(type_id=int(leave_type))
        # filter leave reports if start date is not null
        if start_date and end_date:
            # filter leave reports if date range is not null
            leave_data = leave_data.filter(
                start_date__gte=obj_start, start_date__lte=obj_end)
        if month:
            # filter leave reports if month is not null
            month = month.split('_')[0]
            leave_data = leave_data.filter(start_date__month=month)
        if year:
            # filter leave reports if year is not null
            leave_data = leave_data.filter(start_date__year=year)
        return leave_data

    def __format_leave_reports(self, leave_data, user):
        result = []
        for row in leave_data:
            temp = {}
            temp['emp_name'] = user.first_name + ' ' + user.last_name
            temp['date_applied'] = row.date_applied
            temp['start_date'] = row.start_date
            temp['end_date'] = row.end_date
            temp['leave_type'] = row.type_id
            temp['status'] = row.status
            temp['length'] = row.length_days
            approver =  UserDA().get_user_by_id(row.approver)
            if approver:
                temp['approver'] = approver.first_name + ' ' + approver.last_name
            else:
                temp['approver'] = None
            temp['req_id'] = row.request_id
            temp['comment'] = row.comment
            result.append(temp)
        return result

    def get_team_members_by_lead_id(self, user_id):
        response={
            "error":None,
            "team_members":[]
        }
        try:
            role_id, role_name = UserDA().get_user_role_by_id(user_id)
            if role_id in (1,2,3):
                members = UserDA().get_all_active_users()
            else:
                members= UserDA().get_current_team_members_by_lead_id(user_id)
            member_list = []
            if members:
                for each in members:
                    temp = {}
                    temp = {
                        'id':each.id,
                        'name': str(each.first_name)+' '+str(each.last_name)
                    }
                    response['team_members'].append(temp)
            # response['team_members'].append({"id":0,'name':"ALL"})
        except Exception as err:
                 response["error"] = settings.ERROR_MSG['application_error']\
                .format(err, self.__log.error(self.__exception.get_exception()))
        return response

    def send_not_punch_notification(self, user, data):
        return LeaveHelperBL().send_not_punch_notification(user, data)

    def get_all_halfday_leaves_detail_dict_by_period_id(self, period_id):
        all_halfday_leave_dict = {}
        leave_day_type_in = [2, '2', 3, '3']
        all_leaves = LeaveDA().get_leave_details_by_period_id_and_leave_day_types(period_id, leave_day_type_in)
        for leave in all_leaves:
            all_halfday_leave_dict[leave.leave_request_id] = leave
        return all_halfday_leave_dict


    def __check_leave_avalability(self, emp_id, leave_type_id, leave_period_id):
        is_available = 0
        total_taken = 0
        leave_quota = LeaveDA().get_available_leaves(emp_id, leave_period_id, leave_type_id)
        leave_details = LeaveDA().get_leaves_by_user_id(emp_id, leave_period_id)
        if leave_details:
            for each in leave_details:
                if int(each[0]) not in (1, 2):
                    continue
                total_taken+=1
        for each in leave_quota:
            total_quota = each.no_of_days_allotted
            is_available+= (total_quota-total_taken)
        return is_available>0

    def deabit_leaves(self, request):
        # TODO -Send Mail
        # TODO Title
        response = {'status': "", "error": "", "status_code": 200}
        helper = LeaveHelperBL()
        leave_period_id = 0
        completed_dates = []

        try:
            user = request.user
            length_hours = settings.LEAVE_HOURS['Fullday']
            user_id = user.id
            user_name = user.first_name + " " + user.last_name
            role_id, role_name = UserDA().get_user_role_by_id(user_id)
            access_denied = 1
            if role_id == 2 or user_id == 7: #Added Ajith as per his request
                access_denied = 0
                
            if access_denied:
                response['error'] = settings.ERROR_MSG.get('access_denied')
                return response

            emp_id = request.data.get('emp_id')
            start_date = request.data.get('start_date', None)
            end_date = request.data.get('end_date', None)
            comment = request.data.get('comment', "")
            missed_dates = request.data.get('selected_dates', None) #ALL or  [date, date]

            if not missed_dates:
                response['status_code'] = 499
                response["error"] =  "We are unable to process your request, as we cannot find a leave period."

            leave_period = LeaveDA().get_leave_period_by_date(start_date)  # current leave period
            if  not leave_period:
                response['status_code'] = 499
                response["error"] =  "We are unable to process your request since no date has been selected for debit leave."

            leave_period_id = leave_period.leave_period_id
            leave_day_type = 1 #fullday

            for each_date in missed_dates:
                leave_type = 0

                if self.__check_leave_avalability(emp_id, 1, leave_period_id): #check general leave
                    leave_type = 1
                elif self.__check_leave_avalability(emp_id, 4, leave_period_id): #check LOP leave
                    leave_type = 4

                if not leave_type:
                    response['error'] = "We sincerely apologize, but we cannot debit any more leaves for this\
                            employee as their leave quota has been fully utilized. Please allow for a new quota."
                    response['status_code'] = 499
                    return response

                with transaction.atomic():
                    leave_request_data = helper.get_leave_request_data_template()
                    leave_request_data['start_date'] = each_date
                    leave_request_data['end_date'] = each_date
                    leave_request_data['leave_period_id'] = leave_period_id
                    leave_request_data['type_id'] = leave_type
                    leave_request_data['employee_id'] = emp_id
                    leave_request_data['reason'] = comment
                    leave_request_data['approver'] = user_id
                    leave_request_data['notify'] = None
                    leave_request_data['length_days'] = 1
                    leave_request_data['status'] = settings.LEAVE_REQUEST_STATUS['Approved']  # Approved

                    leave_request = LeaveDA().create_leave_request(leave_request_data)

                    if leave_request:
                        leave_data = helper.get_leave_data_template()
                        leave_data['type_id'] = leave_type
                        leave_data['leave_day_type'] = leave_day_type
                        leave_data['leave_period_id'] = leave_period_id
                        leave_data['leave_date'] = each_date
                        leave_data['length_hours'] = length_hours
                        leave_data['leave_request_id'] = leave_request.request_id
                        leave_data['employee_id'] = emp_id
                        leave_data['status'] = settings.LEAVE_REQUEST_STATUS['Approved'] # Approved
                        leave = LeaveDA().create_leave(leave_data)

                        leave_log = helper.get_leave_log_data_template()
                        leave_log['employee_id'] = emp_id
                        leave_log['request_id'] = leave_request.request_id
                        action = settings.LEAVE_ACTION_LOG[6].format(user_name,\
                                            datetime.now().strftime('%d/%m/%y %I:%M %p'))
                        leave_log['action'] = action
                        leave_log = LeaveDA().create_leave_log(leave_log)

                        completed_dates.append(datetime.strptime(each_date, "%Y-%m-%d").strftime("%d/%m/%Y"))

                response['status'] = "Leave debited successfully."

            if len(completed_dates)>0:
                # To Do :Notification mail
                employee = UserDA().get_user_by_id(emp_id)
                mail_dto = new_dto()
                mail_dto.emp_name = employee.first_name +' '+employee.last_name
                mail_dto.dates = ', '.join(completed_dates)
                mail_dto.sender = user_name
                mail_dto.contact = user.email
                mail_dto.designation = self.__utility.get_designation_of_employee(user_id)
                email_body = LeaveNotificationBL().generate_debit_leave_content(mail_dto)
                subject = 'Leave Deduction Notification'
                LeaveNotificationBL().send_debit_leave_notification(employee.email, subject, email_body)

        except Exception as err:
            response['status_code'] = 499
            response["error"] = settings.ERROR_MSG['application_error']\
                .format(str(err), self.__log.error(self.__exception.get_exception()))
        finally:
            return response