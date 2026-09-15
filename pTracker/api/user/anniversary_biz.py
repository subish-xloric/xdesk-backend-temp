
import math
import calendar
from  datetime import datetime, date, timedelta
from dateutil.relativedelta import relativedelta
from django.conf import settings
from types import SimpleNamespace

from pTracker.settings import ATT_DEVICE
from pTracker.settings import PUNCH_IN_CONFIG

from pTracker.common.utility import Utility
from pTracker.dataaccess.ptracker_access.project_da import  ProjectDA

from pTracker.dataaccess.essl_access.attendance import  AttendanceDA
from pTracker.user_management.holiday_da import HolidayDA
from pTracker.dataaccess.ptracker_access.user_da import UserDA
from pTracker.api.attendance.mapping_biz import UserMappingBL
from pTracker.wiki.utils.exception import ExceptionHandler
from pTracker.dataaccess.ptracker_access.holiday_da import HolidayDA
from pTracker.settings import constants


def new_dto():
    dto = SimpleNamespace()
    return dto




class AnniversaryBL():
    def __init__(self):
        self.__exception = ExceptionHandler()

    def __get_date_range(self, start, end):
        try:
            date_list = []
            delta = end - start
            for i in range(delta.days + 1):
                current_date = start + timedelta(days=i)
                date_list.append(datetime.strptime(current_date.strftime("%Y-%m-%d"),"%Y-%m-%d"))
        except Exception as err:
            print(err)
        return date_list

    def get_employee_work_anniversaries(self,request):
        response = []
        try:
            future_days = 4
            past_days = 3
            current_date = date.today()
            start_date  = current_date - timedelta(days=past_days)
            end_date  = current_date + timedelta(days=future_days)
            days = self.__get_date_range(start_date,end_date)
            work_anniversaries = UserDA().get_employee_work_anniversaries(days)
            if work_anniversaries:
                for emp in work_anniversaries:
                    total_experience = current_date.year - emp.date_joined.year
                    emp_data = {
                        "emp_name": f"{emp.first_name} {emp.last_name}",
                        "emp_id" : emp.id,
                        "emp_code": emp.username,
                        "date_joined": emp.date_joined.strftime("%Y-%m-%d"),
                        "no_of_years": f"{total_experience} Years"
                    }
                    response.append(emp_data)
            else:
                response = [{"error":'No Records found'}]
        except Exception as error:
            response = [{"error":error}]
            print(self.__exception.exception())
        return response

    def get_employee_birthdays(self):
        response = {
            "birthdays": [],
            "error": None
        }
        try:
            start_date = date.today()
            end_date = start_date + timedelta(days=constants.UPCOMING_DAYS)
            days = self.__get_date_range(start_date, end_date)
            birthdays = UserDA().get_upcoming_birthdays(days)
            if birthdays:
                birthday_list = []
                for each in birthdays:
                    for bday in each:
                        emp_data = {"emp_name": f"{bday[1]} {bday[2]}"}
                        if bday[0].strftime("%d-%m") == start_date.strftime("%d-%m"):
                            emp_data["birthday"] = "Today"
                        elif bday[0].strftime("%d-%m") == (start_date + timedelta(days=1)).strftime("%d-%m"):
                            emp_data["birthday"] = "Tomorrow"
                        else:
                            emp_data["birthday"] = bday[0].strftime("%B %d")
                        emp_data["emp_image"] = self.__get_image_url(bday[3])
                        birthday_list.append(emp_data)
                response['birthdays'] = birthday_list
        except Exception as error:
            response['error'] = str(error)
            msg = """Error in the method get_employee_birthdays,
            Error: {0}""".format(str(error))
            Utility().log(msg)
        return response

    def get_upcoming_holidays(self):
        response = {
            "holidays": [],
            "error": None
        }
        holiday_list = []
        try:
            start_date = date.today()
            end_date = start_date + relativedelta(months=constants.FUTURE_MONTHS)
            holidays = HolidayDA().get_holidays(start_date, end_date)
            if holidays:
                for holiday in holidays:
                    temp_dict = {
                        "date": holiday.holiday_date.strftime("%B %d, %Y"),
                        "title": f"{holiday.title}",
                        "background_image":self.__get_holiday_image_url(holiday)
                    }
                    holiday_list.append(temp_dict)
                    del temp_dict
                response['holidays'] = holiday_list
        except Exception as error:
            response['error'] = str(error)
            msg = """Error in the method get_all_holidays,
            Error: {0}""".format(str(error))
            Utility().log(msg)
        return response

    def __get_days_list(self, date_range):
        days_list = []
        for days in date_range:
            days_list.append(days.strftime("%d-%m"))
        return days_list

    def get_work_anniversaries(self):
        response = {
            'anniversaries': [],
            'error': None
        }
        work_anniversaries = []
        try:
            current_date = datetime.today()
            start_date = current_date - timedelta(days=constants.PAST_DAYS)
            end_date = current_date + timedelta(days=constants.FUTURE_DAYS)
            all_users = UserDA().get_all_active_users().order_by('date_joined')
            days_list = self.__get_days_list(self.__get_date_range(start_date, end_date))
            for user in all_users:
                if user.date_joined.year != current_date.year:
                    work_years = current_date.year - user.date_joined.year
                    joining_date = user.date_joined.strftime("%d-%m")
                    if joining_date in days_list:
                        if user.date_joined.day == current_date.day:
                            anniversarsary = "Today"
                        elif user.date_joined.day == (current_date + timedelta(days=1)).day:
                            anniversarsary = "Tomorrow"
                        else:
                            anniversarsary = user.date_joined.strftime("%B %d")
                        anniversary = {
                            "emp_name": f"{user.first_name} {user.last_name}",
                            "anniversary": f"{anniversarsary}",
                            "years": work_years,
                            "emp_image": self.__get_image_url(user.id)
                        }
                        work_anniversaries.append(anniversary)
            response['anniversaries'] = work_anniversaries
        except Exception as error:
            response['error'] = str(error)
            msg = """Error in the method get_work_anniversaries,
            Error: {0}""".format(str(error))
            Utility().log(msg)
        return response

    def get_dashboard_anniversaries(self, request):
        response = {
            "work_anniversaries": [],
            "holidays": [],
            "birthdays": [],
            "error": None
        }
        anniversaries = self.get_work_anniversaries()
        if anniversaries.get('error', None):
            response['error'] = anniversaries.get('error', None)
        response['work_anniversaries'] = anniversaries.get('anniversaries', [])
        holidays = self.get_upcoming_holidays()
        if holidays.get('error', None):
            response['error'] = holidays.get('error', None)
        response['holidays'] = holidays.get('holidays', [])
        birthdays = self.get_employee_birthdays()
        if birthdays.get('error', None):
            response['error'] = birthdays.get('error', None)
        response['birthdays'] = birthdays.get('birthdays', [])
        return response



















    # def send_work_anniversary_email(self):
    #     import random
    #     from pTracker.settings.constants import EMAIL_ADDRESS
    #     from pTracker.notification_center.email_engine import Email
    #     from django.template import loader
    #     try:
    #         email_template_list = ['email_template1.html',
    #                                 'email_template2.html',
    #                                 'email_template3.html',
    #                                 ]
    #         current_date = date.today()
    #         work_anniversaries = UserDA().get_current_day_work_anniversary(current_date)
    #         if work_anniversaries:
    #             for row in work_anniversaries:
    #                 email_template = random.choice(email_template_list)
    #                 total_experience = current_date.year - row.date_joined.year
    #                 context = {}
    #                 context['username'] = f"{row.first_name} {row.last_name}"
    #                 context['years'] = total_experience
    #                 html_email = loader.render_to_string(email_template,context)
    #                 mail_dto = new_dto()
    #                 mail_dto.subject = 'Happy Anniversary'
    #                 mail_dto.from_address = EMAIL_ADDRESS['donotreply']['name']
    #                 mail_dto.body = html_email
    #                 mail_dto.to_addresses = [row.email]
    #                 mail_dto.smtp_username = EMAIL_ADDRESS['donotreply']['mailID']
    #                 mail_dto.smtp_password = EMAIL_ADDRESS['donotreply']['password']
    #                 Email().send_html_mail(mail_dto)
    #                 del mail_dto
    #     except Exception as error:
    #         print(error)
    #         msg = "Error in the job send_work_anniversary_email, Error is : {0} ".format(str(error))
    #         Utility().log(msg)

    # def get_employee_work_anniversaries(self):
    #     pass

        # future_days = 4
        # past_days = 3

        # current_date = datetime.date.today()

        # start_date  = current_date - datetime.timedelta(days=past_days)
        # end_date  = current_date + datetime.timedelta(days=future_days)
        # UserDA().get_employee_work_anniversaries(start_date, end_date )




        # log_dict = {}
        # res_list = []

        # date_dict = {}
        # work_percentage = 0
        # required_work_hrs = 28800

        # punctual_time_str = PUNCH_IN_CONFIG['punctual']['end_time']
        # start_date = Utility().get_first_day_of_month(dt=None, d_years=year, d_months=month)
        # end_date = Utility().get_last_day_of_month(start_date)
        # att_logs = AttendanceDA().get_emp_access_log(emp_code, start_date.strftime("%Y-%m-%d"), end_date.strftime("%Y-%m-%d"))
        # #att_logs = AttendanceDA().get_emp_access_log('529', '2020-01-16', '2020-01-16')
        # log_dict = self.__pre_process_logs(att_logs)

        # if log_dict:
        #     for log_date in log_dict:

        #         dm_data, em_data = self.__segregate_access_log(log_dict[log_date])
        #         dto = emp_dto()
        #         if dm_data:
        #             temp_dto = self.__process_in_and_out(dm_data)
        #             dto.log_time = temp_dto.log_time
        #             dto.dm_access = temp_dto.access
        #             dto.dm_arrival = temp_dto.arrival
        #             dto.dm_departure = temp_dto.departure
        #             dto.dm_floor_hours = temp_dto.floor_hours
        #             if temp_dto.message:
        #                 dto.error_message = temp_dto.message
        #             del temp_dto

        #         if em_data:
        #             temp_dto = self.__process_in_and_out(em_data)
        #             dto.log_time = temp_dto.log_time
        #             dto.em_access = temp_dto.access
        #             dto.em_arrival = temp_dto.arrival
        #             dto.em_departure = temp_dto.departure
        #             dto.em_floor_hours = temp_dto.floor_hours
        #             if temp_dto.message:
        #                 dto.error_message = dto.error_message + " ." + temp_dto.message
        #             del temp_dto

        #         dto.arrival = self.__set_arrival_time(dto.dm_arrival, dto.em_arrival)
        #         dto.departure = self.__set_departure_time(dto.dm_departure, dto.em_departure)

        #         if dto.arrival and dto.departure:
        #             dto.total_hours = Utility().time_diff_in_seconds(dto.arrival, dto.departure)

        #         dto.total_floor_hours = dto.dm_floor_hours + dto.em_floor_hours
        #         work_percentage = int(math.floor((dto.total_floor_hours/required_work_hrs)*100))

        #         if len(dto.dm_access) < len(dto.em_access):
        #             dto.is_dm_employee = False

        #         punctual_time = Utility().create_date_time(log_date, punctual_time_str)

        #         is_late = 0
        #         late_hours = ''
        #         if dto.arrival > punctual_time:
        #             is_late = 1
        #             late_hours = Utility().time_diff_in_seconds(punctual_time, dto.arrival)
        #             late_hours = Utility().seconds_to_hour_and_minute(late_hours) + " hrs late"

        #             if dto.total_floor_hours >= required_work_hrs:
        #                 is_late = 2


        #         if dto.is_dm_employee:
        #             first_log = "DM"
        #         else:
        #             first_log = "EM"

        #         res_dict = {
        #             "error": "",
        #             "date_status": "working",
        #             "date_remark": "",
        #             "work_percentage": work_percentage,
        #             "date": log_date,
        #             "effective_hours": Utility().seconds_to_hour_and_minute(dto.total_floor_hours),
        #             "gross_hours": Utility().seconds_to_hour_and_minute(dto.total_hours),
        #             "arrival": {
        #                 "is_late": is_late,
        #                 "late_hours": late_hours
        #             },
        #             "log": {
        #                 "first_log": first_log,
        #                 "dm_log": self.__generate_access_log_list(dto.dm_access),
        #                 "em_log": self.__generate_access_log_list(dto.em_access),
        #             }
        #         }

        #         date_dict[log_date] = res_dict
        #         del res_dict

        #     date_list = self.__get_date_range(start_date, end_date)
        #     holiday_dict = self.__get_all_holidays(start_date, end_date)
        #     week_ends_list = self.__get_all_weekends(start_date, end_date)

        #     for each_date in date_list:
        #         curr_date = Utility().convert_string_to_date_time(each_date, "%Y-%m-%d")
        #         if curr_date > datetime.now():
        #             # temp_dict = {
        #             #     "error": "",
        #             #     "date_status": "future",
        #             #     "date_remark": "-",
        #             #     "date": each_date
        #             # }
        #             # res_list.append(temp_dict)
        #             continue

        #         temp_dict = date_dict.get(each_date, None)
        #         if not temp_dict:
        #             holiday = holiday_dict.get(each_date, None)
        #             if holiday:
        #                 temp_dict = {
        #                     "error": "",
        #                     "date_status": "holiday",
        #                     "date_remark": holiday,
        #                     "date": each_date
        #                 }
        #             else:
        #                 if each_date in week_ends_list:
        #                     temp_dict = {
        #                     "error": "",
        #                     "date_status": "weekend",
        #                     "date_remark": 'Weekly Off',
        #                     "date": each_date
        #                     }
        #                 else:
        #                     temp_dict = {
        #                     "error": "",
        #                     "date_status": "leave",
        #                     "date_remark": 'Leave',
        #                     "date": each_date
        #                     }
        #         res_list.append(temp_dict)
        #         del temp_dict

        # return res_list


    def get_team_attendance_average(self, user_id, month, year):
        pass

        # start_date = Utility().get_first_day_of_month(dt=None, d_years=year, d_months=month)
        # end_date = Utility().get_last_day_of_month(start_date)
        # punctual_time_str = PUNCH_IN_CONFIG['punctual']['end_time']

        # total_days = 0
        # punctual_days = 0
        # total_work_hours = 0
        # team_avg_hours = 0
        # team_avg_punctual_time = 0
        # team_count = 0

        # role_id, role_name = UserDA().get_user_role_by_id(user_id)
        # if role_id in (1, 2, 3):
        #     temp_dict = {
        #         "team_avg_hours": "NA",
        #         "team_avg_punctual_time": 'NA'
        #     }
        #     return temp_dict

        # if role_id == 4:
        #     team_member_list = UserDA().get_current_team_members_by_lead_id(user_id)
        # else:
        #     team_member_list = UserDA().get_current_team_members_by_emp_id(user_id)

        # if team_member_list:
        #     for each_user in team_member_list:
        #         team_count += 1
        #         emp_code = UserMappingBL().get_employee_code(each_user.id)
        #         att_logs = AttendanceDA().get_emp_attendance_log(emp_code, start_date.strftime("%Y-%m-%d"), end_date.strftime("%Y-%m-%d"))
        #         if att_logs:
        #             emp_avg_hours = 0
        #             emp_avg_punctual_time = 0

        #             for each_item in att_logs:
        #                 total_days += 1
        #                 attendance_date = str(each_item[0])
        #                 work_hours = each_item[1]
        #                 arrival = each_item[2]
        #                 total_work_hours += work_hours
        #                 punctual_time = Utility().create_date_time(attendance_date, punctual_time_str)
        #                 if arrival < punctual_time:
        #                     punctual_days += 1

        #             emp_avg_hours = int(total_work_hours / total_days)
        #             emp_avg_punctual_time = int((punctual_days / total_days) * 100)

        #             team_avg_hours += emp_avg_hours
        #             team_avg_punctual_time += emp_avg_punctual_time

        #     team_avg_hours = int(team_avg_hours / team_count)
        #     team_avg_hours = Utility().seconds_to_hour_and_minute(team_avg_hours)
        #     team_avg_punctual_time = int(team_avg_punctual_time / team_count)
        # temp_dict = {
        #    "team_avg_hours": str(team_avg_hours) + " hrs",
        #     "team_avg_punctual_time": str(team_avg_punctual_time) + " %"
        # }
        # return temp_dict




    def get_emp_attendance_average(self, user_id, emp_code, month, year):
        pass

        # start_date = Utility().get_first_day_of_month(dt=None, d_years=year, d_months=month)
        # end_date = Utility().get_last_day_of_month(start_date)
        # punctual_time_str = PUNCH_IN_CONFIG['punctual']['end_time']

        # total_days = 0
        # punctual_days = 0
        # total_work_hours = 0
        # emp_avg_hours = 0
        # emp_avg_punctual_time = 0
        # att_logs = AttendanceDA().get_emp_attendance_log(emp_code, start_date.strftime("%Y-%m-%d"), end_date.strftime("%Y-%m-%d"))
        # if att_logs:
        #     for each_item in att_logs:
        #         total_days += 1
        #         attendance_date = str(each_item[0])
        #         work_hours = each_item[1]
        #         arrival = each_item[2]
        #         total_work_hours += work_hours

        #         punctual_time = Utility().create_date_time(attendance_date, punctual_time_str)
        #         if arrival < punctual_time:
        #             punctual_days += 1

        # emp_avg_hours = int(total_work_hours / total_days)
        # emp_avg_hours = Utility().seconds_to_hour_and_minute(emp_avg_hours)
        # emp_avg_punctual_time = int((punctual_days / total_days) * 100)

        # temp_dict = self.get_team_attendance_average(user_id, month, year)
        # temp_dict["my_avg_hours"] = str(emp_avg_hours) + " hrs"
        # temp_dict["my_avg_punctual_time"] = str(emp_avg_punctual_time) + " %"

        # return temp_dict

    def __get_image_url(self, user_id):
        img_url = UserDA().get_user_profile_by_id(user_id)
        if img_url:
            return f"{settings.DEFAULT_SITE_MEDIA_URL}{img_url.profile_photo}"
        else:
            return None

    def __get_holiday_image_url(self, holiday_obj):
        if holiday_obj.holiday_image:
            image_url = f"{settings.HOLIDAY_IMAGE_URL}{holiday_obj.holiday_image}"
        else:
            image_url = None
        return image_url
