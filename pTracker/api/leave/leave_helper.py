from datetime import datetime
from datetime import date, timedelta
from django.conf import settings

from types import SimpleNamespace


from pTracker.common.utility import Utility
from pTracker.common.exception_handler import ExceptionHandler
from pTracker.common.logs import Logs

from pTracker.notification_center.email_engine import Email

from pTracker.dataaccess.ptracker_access.leave_da import LeaveDA
from pTracker.dataaccess.ptracker_access.user_da import UserDA
from pTracker.user_management.holiday_da import HolidayDA


from pTracker.api.leave.leave_notification_biz import LeaveNotificationBL
# from pTracker.dataaccess.ptracker_access.leave_da import LeaveRequestLog

def new_dto():
    dto = SimpleNamespace()
    return dto

class LeaveHelperBL():
    def __init__(self):
        self.__log = Logs()
        self.__exception = ExceptionHandler()
        self.__utility = Utility()

    def get_leave_request_data_template(self):
        leave_request_data = {
            "type_id": 0,
            "leave_period_id": 0,
            "employee_id": 0,
            "reason": "",
            "length_days": 0.0,
            "start_date": "",
            "end_date": "",
            "status": settings.LEAVE_REQUEST_STATUS['Requested'],  # Requested
            "approver": 0,
            "comment": "",
            "notify": ""
        }
        return leave_request_data

    def get_leave_data_template(self):
        leave_data = {
            "leave_date": "",
            "length_hours": 0,
            "status": settings.LEAVE_REQUEST_STATUS['Requested'],  # Requested
            "leave_request_id": 0,
            "leave_day_type": 0,
            "employee_id": 0,
            "type_id": 0,
            "leave_period_id": 0
        }
        return leave_data

    def get_leave_log_data_template(self):
        leave_log = {
            "action": "",
            "employee_id": 0,
            "request_id": 0
        }
        return leave_log

    def get_comp_off_data_template(self):
        comp_off_data = {
                "start_date" :'',
                "end_date" : '',
                "employee_id" : 0,
                "leave_type_id" : 0,
                "leave_period_id" : 0,
                "approver_id" : 0,
                "status" : settings.LEAVE_REQUEST_STATUS['Requested'],
                "reason" : '',
                'comment' : '',
                'no_of_days' : 0,
            }
        return comp_off_data

    def get_comp_off_log_data(self):
        comp_off_log_data = {
            "comp_off_id" : '',
            'action' :'',
            'employee_id' : ''
        }
        return comp_off_log_data

    def get_all_user_dict(self):
        user_dict = {}
        active_users = UserDA().get_all_users()
        for user in active_users:
            user_name = user.first_name + " " + user.last_name
            if user.is_active == 0:
                user_name = user_name + " (Past Employee)"
            user_dict[user.id] = user_name
        return user_dict

    def get_leave_type_dict(self):
        leave_type_dict = {}
        leave_types = LeaveDA().get_all_leave_types()
        for leave_type in leave_types:
            leave_type_dict[leave_type.leave_type_id] = leave_type.leave_type_name
        return leave_type_dict

    def get_all_off_days_for_date_range(self, start_date, end_date):
        holiday_list = []
        work_days = []
        holiday_length =  0
        week_ends = Utility().get_all_weekends(start_date, end_date)
        if week_ends:
            for each_day in week_ends:
                holiday_list.append(each_day)
        start_date = start_date.strftime("%Y-%m-%d")
        end_date = end_date.strftime("%Y-%m-%d")

        obj_holidays = HolidayDA().get_holidays(start_date, end_date)
        if obj_holidays:
            for each_item in obj_holidays:
                holiday_list.append(each_item.holiday_date)

        obj_workingdays = HolidayDA().get_additional_working_days(start_date, end_date)
        if obj_workingdays:
            for day in obj_workingdays:
                work_days.append(day.working_date)
        holiday_length = len(holiday_list) - len(work_days)

        return holiday_length

    def get_total_leave_quota_by_period(self, period):
        leave_quota_dict = {}
        result_set, error = LeaveDA().get_total_leave_quota_by_period(period)
        if result_set:
            for each_row in result_set:
                leave_quota_dict[each_row[0]] = each_row[1]
        return leave_quota_dict

    # def get_all_user_dict_by_lead_id(self, user_id):
    #     user_dict = {}
    #     active_users = UserDA().get_current_team_members_by_lead_id(user_id)
    #     for user in active_users:
    #         user_name = user.first_name + " " + user.last_name
    #         if user.is_active == 0:
    #             user_name = user_name + " (Past Employee)"
    #         user_dict[user.id] = user_name
    #     return user_dict
    def is_date_range_valid(self, start_date, end_date):
        is_valid = False
        if start_date <= end_date:
            is_valid = True
        return is_valid

    def is_date_range_in_same_year(self, start_date, end_date):
        is_valid = False
        if start_date.year == end_date.year:
            is_valid = True
        return is_valid

    def is_date_range_overlapped(self, start_date, end_date, user_id, comp_off_id=0):
        is_overlapped = False
        result = LeaveDA().get_comp_off_dates_overlap(start_date, end_date, user_id)
        if result:
            if comp_off_id:
                result = result.exclude(comp_off_id=comp_off_id)
                if result:
                    is_overlapped = True
            else:
                is_overlapped = True
        return is_overlapped

    def is_valid_leave_duration(self, start_date, end_date, leave_type_id):
        msg = None
        duration = self.__utility.get_date_range(start_date, end_date)
        if leave_type_id == '5': #hard code to be removed for maternity leave
            if len(duration) > settings.MAXIMUM_MATERNITY_LEAVE_DURATION:
                msg = f'''Maximum leave duration for maternity is 180'''
        else:
            if len(duration) > settings.MAXIMUM_COMP_LEAVE_DURATION:
                msg = f'''Maximum leave duration for the selected leave type is {settings.MAXIMUM_COMP_LEAVE_DURATION}'''
        return msg


    def get_length_of_off_days_for_date_range(self, start_date, end_date):
        holiday_list = []
        work_days = []
        length_of_off_days =  0
        week_ends = Utility().get_all_weekends(start_date, end_date)
        if week_ends:
            for each_day in week_ends:
                holiday_list.append(each_day.strftime("%Y-%m-%d"))
        start_date = start_date.strftime("%Y-%m-%d")
        end_date = end_date.strftime("%Y-%m-%d")
        obj_holidays = HolidayDA().get_holidays(start_date, end_date)
        if obj_holidays:
            for each_item in obj_holidays:
                holiday_list.append(each_item.holiday_date.strftime("%Y-%m-%d"))
        holiday_list = list(set(holiday_list))
        obj_workingdays = HolidayDA().get_additional_working_days(start_date, end_date)
        if obj_workingdays:
            for day in obj_workingdays:
                work_days.append(day.working_date.strftime("%Y-%m-%d"))
        all_off_days = [x for x in holiday_list if x not in work_days]
        if all_off_days:
            length_of_off_days = len(all_off_days)
        return length_of_off_days


    def send_wfh_notification_to_lead(self, email_dto):
        mail_dto = new_dto()
        mail_dto.subject = "DM DESK: {0} By {1} !!!".format(email_dto.message,email_dto.emp_name)
        mail_dto.from_address = settings.EMAIL_ADDRESS['do_not_reply']['name']
        mail_dto.body = email_dto.message
        mail_dto.to_addresses = [email_dto.to_email]
        mail_dto.smtp_username = settings.EMAIL_ADDRESS['do_not_reply']['mailID']
        mail_dto.smtp_password = settings.EMAIL_ADDRESS['do_not_reply']['password']
        Email().send_html_mail(mail_dto)

    def get_cc_adresses(self, notify_list, user_id):
        user_dict = {}
        cc_list = []
        notify = notify_list.split(',')
        if str(user_id) in notify:
            notify.remove(str(user_id))

        if '0' in notify:
            notify.remove('0')
        all_users = UserDA().get_all_active_users()
        for each_user in all_users:
            user_dict[str(each_user.id)] = each_user.email

        if notify:
            for each in notify:
                if each == '':
                    continue
                # user = all_users.get(id = each)
                email = user_dict.get(each,None)
                if email:
                    cc_list.append(email)
        return cc_list

    def send_not_punch_notification(self, user, data):
        response = {'error': None, 'message': None}
        try:
            cc_list = []
            role_id, role_name = UserDA().get_user_role_by_id(user.id)
            if role_id not in (1, 2, 3, '1', '2', '3'):
                response["error"] = settings.ERROR_MSG.get('access_denied')
                return response
            comment = data.get('comment', None)
            emp_id = data.get('emp_id', 0)
            missed_date = data.get('missed_dates', [])

            lead_id = UserDA().get_lead_id_by_user(emp_id)

            if lead_id:
                lead = UserDA().get_user_by_id(lead_id)
                cc_list.append(lead.email)

            if emp_id:
                employee = UserDA().get_user_by_id(emp_id)
                emp_name = employee.first_name + ' ' + employee.last_name
                subject = 'Not Punched Days'
                content = """
                    <p>Hi {0}.</p>\
                    <h5>{1}</h5>\
                    <p>Thank you,\n DM DESK</p>""".format(emp_name, comment)
                LeaveNotificationBL().send_leave_request_update_notification(content, emp_name,
                                                                             employee.email, subject, cc_list)
                response["message"] = 'Mail Send Succesfully'

        except Exception as error:
            response["error"] = settings.ERROR_MSG['application_error']\
                .format(error, self.__log.error(self.__exception.get_exception()))
        return response

    def get_team_leave_calendar(self, user_id):
        response = {"leave": [], "error": None}
        user_da = UserDA()
        leaves = []
        try:
            start_date = date.today().replace(day=1)
            end_date = start_date + timedelta(days=settings.UPCOMING_MONTH)
            role_id, role_name = user_da.get_user_role_by_id(user_id)
            if role_id in (1, 2, 3):
                response['leave'] = []
                team_member_list = user_da.get_all_active_users()
            elif role_id == 4:
                team_member_list = user_da.get_current_team_members_by_lead_id(
                    user_id)
            else:
                team_member_list = user_da.get_current_team_members_by_emp_id(
                    user_id)

            leave_status = [
                settings.LEAVE_REQUEST_STATUS['Requested'],
                settings.LEAVE_REQUEST_STATUS['Approved']
            ]
            leave_list = LeaveDA().get_all_leaves_by_date_range(
                start_date, end_date, leave_status)

            user_leave_list = leave_list.filter(employee_id=user_id)
            if user_leave_list:
                for leave in user_leave_list:
                    leave_date = leave.leave_date.strftime("%Y-%m-%d")
                    if leave_date not in leaves:
                        leaves.append(leave_date)
                        team_leaves = {"date": leave_date, "type": "Leave", "color": "green"}
                        response['leave'].append(team_leaves)

            if team_member_list:
                for each_user in team_member_list:
                    user_leave_list = leave_list.filter(
                        employee_id=each_user.id)
                    if user_leave_list:
                        for leave in user_leave_list:
                            leave_date = leave.leave_date.strftime("%Y-%m-%d")
                            if leave_date not in leaves:
                                leaves.append(leave_date)
                                team_leaves = {"date": leave_date,
                                               "type": "Leave", "color": "green"}
                                response['leave'].append(team_leaves)
            holidays = HolidayDA().get_holidays(start_date, end_date)
            if holidays:
                for holiday in holidays:
                    holiday_date = holiday.holiday_date.strftime("%Y-%m-%d")
                    if holiday_date not in leaves:
                        leaves.append(holiday_date)
                        all_holiday = {"date": holiday_date,
                                       "type": "Holyday", "color": "blue"}
                        response['leave'].append(all_holiday)
            weekdays = self.__utility.get_week_days(start_date, end_date)
            if weekdays:
                for weekday in weekdays:
                    if weekday not in leaves:
                        leaves.append(weekday)
                        all_weekday = {"date": weekday,
                                       "type": "Weekday", "color": "red"}
                        response['leave'].append(all_weekday)
        except Exception as err:
            response["error"] = settings.ERROR_MSG['application_error']\
                .format(str(err), self.__log.error(self.__exception.get_exception()))
        return response

    def fill_leave_apply_form_dropdowns(self):
        response = {
            "error": None,
            "leave_type": [],
            "notify": []
        }
        try:
            all_leave_types = []
            # leave types
            leave_types = LeaveDA().get_all_leave_types()
            if leave_types:
                for each in leave_types:
                    all_leave_types.append({"id": each.leave_type_id,
                                            "leave_type": each.leave_type_name})
                response['leave_type'] = all_leave_types
            supervisors, aaa = UserDA().get_all_supervisors_for_leave()
            # supervisors
            if supervisors:
                temp_list = []
                for supervisor in supervisors:
                    temp_list.append(
                        {"id": supervisor[0], "name": supervisor[1] + " " + supervisor[2]})
                response['notify'] = temp_list

        except Exception as err:
            response["error"] = settings.ERROR_MSG['application_error']\
                .format(str(err), self.__log.error(self.__exception.get_exception()))
        return response

    def leave_date_validation(self, request, user_id):
        response = {"message": "", "error": ""}
        try:
            start_date = request.data.get('start_date', None)
            end_date = request.data.get('end_date', None)
            leave_type = request.data.get('type_id', None)
            edit_id = request.data.get('request_id', 0)
            leave_day_type = request.data.get('leave_day_type', None)
            start = datetime.strptime(start_date, "%Y-%m-%d")
            end = datetime.strptime(end_date, "%Y-%m-%d")
            duration = Utility().get_date_range(start, end)
            leave_period = LeaveDA().get_leave_period_by_date(start)
            if start.year != end.year:
                response['message'] = "Leave start date and end date should be in the same year."
                return response

            if leave_period is None:
                response['message'] = f'''You can't apply leave for this date range. Leave period is missing in system.'''
                return response

            if leave_type:
                leave_balance = self.get_user_leave_balance(leave_type, user_id, leave_period.leave_period_id, edit_id)

                if leave_balance is not None:
                    if leave_balance >= 0:
                        if float(leave_balance) < float(len(duration)):
                            if not (leave_balance == .5 and len(duration) == 1) :
                                response['message'] = f'''Insufficient leave balance for selected leave type. Leave balance is {leave_balance}'''
                                return response
                            if leave_balance == .5 and len(duration) == 1 and leave_day_type == '1':
                                response['message'] = f'''Insufficient leave balance for selected leave type. Leave balance is{leave_balance}.'''
                                return response
                else:
                    response['message'] = "You can't apply for leave right now. Please contact your respective LEAD or HR  "
                    return response
            if duration:
                if len(duration) > settings.MAXIMUM_LEAVE_DURATION:
                    response['message'] = "Leave duration exceed maximum limit. Limit is {0}".format(settings.MAXIMUM_LEAVE_DURATION)
                    return response
            result = LeaveDA().get_leave_date_overlap(start_date, end_date, user_id)
            if result:
                if edit_id:
                    edit_excluded_result = result.exclude(
                        leave_request_id=edit_id)
                    if edit_excluded_result:
                        response['message'] = f'''Leave dates are overlapping with previous leave request. Please change dates'''
                else:
                    response['message'] = "dates overlapping with previous leave request dates"
                return response

            is_start_or_end_date_in_holiday = self.is_start_date_or_end_date_in_holiday(start, end)
            if is_start_or_end_date_in_holiday:
                response['message'] = "Leave from  or leave to can't be a holiday"
                return response
        except Exception as err:
            response["error"] = settings.ERROR_MSG['application_error']\
                .format(str(err), self.__log.error(self.__exception.get_exception()))
            return response
        return response

    def get_user_leave_balance(self, leave_type_id, user_id, leave_period_id, leave_request_id=0):
        balance = 0
        halfdays = []
        fulldays = []
        quota = LeaveDA().get_leave_quota(user_id, leave_period_id, leave_type_id)
        taken = LeaveDA().get_leave_taken(leave_type_id, user_id, leave_period_id)
        if quota:
            if taken:
                if leave_request_id:
                    taken = taken.exclude(leave_request_id=leave_request_id)
                halfdays = taken.exclude(length_hours=settings.LEAVE_HOURS['Fullday'])
                fulldays = taken.exclude(length_hours=settings.LEAVE_HOURS['Halfday'])
            balance = (float(quota.no_of_days_allotted) - float(len(fulldays)) - float(len(halfdays) / 2))
        return balance

    def __get_leave_type_name(self, leave_type_id):
        if leave_type_id in (1, '1'):
            type_name = 'General'
        elif leave_type_id in (2, '2'):
            type_name = 'Official'
        elif leave_type_id in (3, '3'):
            type_name = 'Comp_Off'
        elif leave_type_id in (4, '4'):
            type_name = 'LOP'
        else:
            type_name = 'Maternity'
        return type_name

    def generate_leave_summary(self, user_id, period):
        temp = {}
        leave_quota = LeaveDA().get_leave_quota_by_user_id(user_id, period)
        if leave_quota:
            user_leaves = LeaveDA().get_leaves_by_user_id(user_id, period)
            for each in leave_quota: # set scheduled number and balance  based on leave status
                each.no_of_days_allotted = float(each.no_of_days_allotted)
                scheduled = 0
                balance = each.no_of_days_allotted
                total = each.no_of_days_allotted
                taken = total - balance - scheduled
                for leave in user_leaves:
                    if leave[0] in (1, 2, '2', '1'):
                        if leave[2] == int(each.leave_type_id):
                            if leave[3] <= date.today():
                                taken += float(leave[1] / 8)
                                balance -= float(leave[1] / 8)
                            else:
                                scheduled += float(leave[1] / 8)
                                balance -= float(leave[1] / 8)
                if each.leave_type_id:
                    type_name = self.__get_leave_type_name(each.leave_type_id)
                temp[type_name] = {
                    'total': total,
                    'taken': taken,
                    'scheduled': scheduled,
                    'balance': balance
                }
            return temp
    
    def is_start_date_or_end_date_in_holiday(self, start_date, end_date):
        in_holiday = False
        date_list = [start_date, end_date ]
        holidays = HolidayDA().get_holidays_in_date_list(date_list)
        if holidays:
            in_holiday = True
        return in_holiday

