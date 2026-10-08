from datetime import datetime
from datetime import date, timedelta
from django.conf import settings

from types import SimpleNamespace


from pTracker.common.utility import Utility
from pTracker.common.company_context import get_active_company_id
from pTracker.common.exception_handler import ExceptionHandler
from pTracker.common.logs import Logs

from pTracker.notification_center.email_engine import Email

from pTracker.dataaccess.ptracker_access.leave_da import LeaveDA
from pTracker.dataaccess.ptracker_access.user_da import UserDA
from pTracker.user_management.holiday_da import HolidayDA
from pTracker.api.attendance_v2.processing_biz import AttendanceProcessorBL
from pTracker.dataaccess.attendance_v2_access.constants import DAY_WORKING
from pTracker.dataaccess.attendance_v2_access.org_da import OrgDA
from pTracker.common.company_authorization import has_capability
from pTracker.common.company_authorization import users_with_capability


from pTracker.api.leave.leave_notification_biz import LeaveNotificationBL
from pTracker.common.company_authorization import data_scope, SCOPE_ALL, SCOPE_TEAM
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

    def is_company_leave_type(self, employee_id, leave_type_id):
        """ The leave type is enabled and belongs to the employee's company. """
        try:
            leave_type_id = int(leave_type_id)
            company_id = UserDA().get_user_organization(employee_id)
        except Exception:
            return False
        leave_type = LeaveDA().get_company_leave_type(company_id, leave_type_id)
        return bool(leave_type and leave_type.available_flag == 1)

    def get_leave_type_id_by_code(self, employee_id, code):
        """ Id of the employee's company's leave type with this system code, or None. """
        leave_type = LeaveDA().get_leave_type_by_code(UserDA().get_user_organization(employee_id), code)
        return leave_type.leave_type_id if leave_type else None

    def is_valid_leave_duration(self, start_date, end_date, leave_type_id):
        msg = None
        duration = self.__utility.get_date_range(start_date, end_date)
        leave_types = LeaveDA().get_leave_type_code_name_dict()
        if leave_types.get(int(leave_type_id or 0), (None,))[0] == 'maternity':
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
            if not has_capability(user.id, 'leave.manage_all'):
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
            scope = data_scope(user_id, 'leave')
            if scope == SCOPE_ALL:
                response['leave'] = []
                team_member_list = user_da.get_all_active_users()
            elif scope == SCOPE_TEAM:
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
            leave_types = LeaveDA().get_all_leave_types(get_active_company_id())
            if leave_types:
                for each in leave_types:
                    all_leave_types.append({"id": each.leave_type_id,
                                            "leave_type": each.leave_type_name})
                response['leave_type'] = all_leave_types
            supervisors, aaa = UserDA().get_all_supervisors_for_leave(
                users_with_capability('leave.approve'))
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
        """ {'message': validation error or '', 'error': unexpected error or ''}. """
        try:
            return {"message": self.validate_leave_dates(request.data, user_id), "error": ""}
        except Exception:
            log_id = self.__log.error(self.__exception.get_exception())
            return {"message": "", "error": f"Leave validation failed. LogID: {log_id}"}

    def validate_leave_dates(self, data, user_id):
        """ The single leave-request validation used by web, mobile and the
        validate-date endpoint. data: start_date, end_date (YYYY-MM-DD), type_id,
        request_id (when editing), leave_day_type (1 full, 2/3 half day).
        Returns an error message, or '' when the request is valid. """
        try:
            start = datetime.strptime(str(data.get('start_date')), "%Y-%m-%d").date()
            end = datetime.strptime(str(data.get('end_date')), "%Y-%m-%d").date()
        except ValueError:
            return "Invalid start or end date."
        if start > end:
            return "Leave start date should be on or before the end date."
        if start.year != end.year:
            return "Leave start date and end date should be in the same year."
        leave_period = LeaveDA().get_employee_leave_period(user_id, start)
        if leave_period is None:
            return "You can't apply leave for this date range. Leave period is missing in system."

        leave_days, non_working = self.get_leave_days(user_id, start, end)
        if start in non_working or end in non_working:
            return "Leave from or leave to can't be a holiday or weekly off."
        if len(leave_days) > settings.MAXIMUM_LEAVE_DURATION:
            return "Leave duration exceed maximum limit. Limit is {0}".format(settings.MAXIMUM_LEAVE_DURATION)

        edit_id = data.get('request_id', 0)
        leave_type = data.get('type_id', None)
        if leave_type:
            balance = self.get_user_leave_balance(leave_type, user_id, leave_period.leave_period_id, edit_id)
            if balance is None:
                return "You can't apply for leave right now. Please contact your respective LEAD or HR"
            if float(balance) < self.requested_days(leave_days, data.get('leave_day_type')):
                return f"Insufficient leave balance for selected leave type. Leave balance is {balance}"

        overlap = LeaveDA().get_leave_date_overlap(start.isoformat(), end.isoformat(), user_id)
        if overlap and edit_id:
            overlap = overlap.exclude(leave_request_id=edit_id)
        if overlap:
            return "Leave dates are overlapping with a previous leave request. Please change dates."
        return ""

    def get_leave_days(self, employee_id, start, end):
        """ (leave_days, non_working): the dates of start..end that count as leave
        for the employee, and the range's weekly offs / holidays. Working days
        come from the employee's Attendance V2 shift and the company's holiday
        calendar (no shift assigned: Saturday and Sunday are off). With the
        company's sandwich-leave rule on, weekly offs and holidays inside the
        range count as leave too; otherwise only working days count. """
        company = OrgDA().get_company(UserDA().get_user_organization(employee_id))
        if company is None:
            raise ValueError('Employee has no active company')
        planner = AttendanceProcessorBL(company).planner(employee_id, start, end)
        all_days, non_working = [], set()
        day = start
        while day <= end:
            plan = planner.plan(day)
            if plan.day_type != DAY_WORKING or (plan.snapshot is None and day.weekday() >= 5):
                non_working.add(day)
            all_days.append(day)
            day += timedelta(days=1)
        if company.leave_sandwich_rule:
            return all_days, non_working
        return [d for d in all_days if d not in non_working], non_working

    def requested_days(self, leave_days, leave_day_type):
        """ Days to deduct: half a day for a half-day leave (types 2 / 3). """
        if str(leave_day_type) in ('2', '3'):
            return 0.5
        return float(len(leave_days))

    def invalid_notify_ids(self, user_id, notify):
        """ Notify targets that are not active employees of the caller's company. """
        company_employees = set(UserDA().get_all_active_users().filter(
            id__in=UserDA().get_user_ids_by_company(UserDA().get_user_organization(user_id)))
            .values_list('id', flat=True))
        invalid = []
        for each in notify or []:
            try:
                notify_id = int(each['id'] if isinstance(each, dict) else each)
            except (TypeError, ValueError, KeyError):
                invalid.append(each)
                continue
            if notify_id not in company_employees:
                invalid.append(notify_id)
        return invalid

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

    LEAVE_SUMMARY_LABELS = {'general': 'General', 'official': 'Official', 'comp_off': 'Comp_Off',
                            'lop': 'LOP', 'maternity': 'Maternity'}

    def leave_summary_by_type(self, user_id, period):
        """ One entry per leave quota of the employee in the period:
        {leave_type_id, code, leave_type, total, taken, scheduled, balance}.
        taken = requested/approved leave days up to today, scheduled = after today. """
        summary = []
        leave_quota = LeaveDA().get_leave_quota_by_user_id(user_id, period)
        if not leave_quota:
            return summary
        leave_types = LeaveDA().get_leave_type_code_name_dict()
        user_leaves = LeaveDA().get_leaves_by_user_id(user_id, period)
        for each in leave_quota:
            total = float(each.no_of_days_allotted)
            taken = scheduled = 0.0
            for leave in user_leaves:
                if leave[0] in (1, 2, '2', '1') and leave[2] == int(each.leave_type_id):
                    if leave[3] <= date.today():
                        taken += float(leave[1] / 8)
                    else:
                        scheduled += float(leave[1] / 8)
            code, name = leave_types.get(int(each.leave_type_id), (None, ''))
            summary.append({'leave_type_id': int(each.leave_type_id), 'code': code, 'leave_type': name,
                            'total': total, 'taken': taken, 'scheduled': scheduled,
                            'balance': total - taken - scheduled})
        return summary

    def generate_leave_summary(self, user_id, period):
        """ {label: {total, taken, scheduled, balance}}; label is the fixed one for
        system leave types (General, LOP, ...) and the type's name otherwise. """
        temp = {}
        for item in self.leave_summary_by_type(user_id, period):
            label = self.LEAVE_SUMMARY_LABELS.get(item['code'], item['leave_type'])
            temp[label] = {key: item[key] for key in ('total', 'taken', 'scheduled', 'balance')}
        return temp

    def is_start_date_or_end_date_in_holiday(self, start_date, end_date):
        in_holiday = False
        date_list = [start_date, end_date ]
        holidays = HolidayDA().get_holidays_in_date_list(date_list)
        if holidays:
            in_holiday = True
        return in_holiday

