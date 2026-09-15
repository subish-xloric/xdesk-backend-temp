
import math
import time
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
from pTracker.api.timesheet.timesheet_report_biz import TimesheetReportBL


def new_dto():
    dto = SimpleNamespace()
    return dto

def emp_dto():
    dto = SimpleNamespace()
    dto.emp_code = None
    dto.emp_name = None
    dto.arrival = None
    dto.departure = None
    dto.dm_access = []
    dto.em_access = []

    dto.dm_arrival = None
    dto.dm_departure = None

    dto.em_arrival = None
    dto.em_departure = None

    dto.dm_floor_hours = 0
    dto.em_floor_hours = 0

    dto.total_floor_hours = 0
    dto.total_hours =  0
    dto.break_hours = 0
    dto.error_message = ''
    dto.arrival_status = None
    dto.departure_status = None
    dto.is_dm_employee = True
    dto.log_time = None
    return dto


class AttendanceBL():

    def __init__(self):
        self.__log = Logs()
        self.__exception = ExceptionHandler()
        self.__utility = Utility()


    def __pre_process_logs(self, att_logs):
        log_dict = {}
        if att_logs:
            for log in att_logs:
                log_time = Utility().convert_string_to_date_time(log[1])
                log_date = log_time.strftime("%Y-%m-%d")
                dto = new_dto()
                dto.employee_code = str(log[0]).strip()
                dto.log_time = log_time
                dto.direction = str(log[2]).strip()
                dto.device_serial_no = str(log[3]).strip()
                if log_date in log_dict:
                    temp_list = log_dict[log_date]
                    temp_list.append(dto)
                    log_dict[log_date] = temp_list
                    del dto, temp_list
                else:
                    log_dict[log_date] = [dto]
                    del dto
        return log_dict

    def __segregate_access_log(self, log_data):
        dm_data = []
        em_data = []
        dm_device_in = settings.ATT_DEVICE['DM' + "_IN"]['SerialNumber']
        dm_device_out = settings.ATT_DEVICE['DM' + "_OUT"]['SerialNumber']
        em_device_in = settings.ATT_DEVICE['EM' + "_IN"]['SerialNumber']
        em_device_out = settings.ATT_DEVICE['EM' + "_OUT"]['SerialNumber']
        if log_data:
            for log in log_data:
                if log.device_serial_no == dm_device_in:
                    log.direction = 'IN'
                    dm_data.append(log)

                elif log.device_serial_no == dm_device_out:
                    log.direction = 'OUT'
                    dm_data.append(log)

                elif log.device_serial_no == em_device_in:
                    log.direction = 'IN'
                    em_data.append(log)
                elif log.device_serial_no == em_device_out:
                    log.direction = 'OUT'
                    em_data.append(log)
        return dm_data, em_data

    def __process_in_and_out(self, punch_data):

        #temp_missed_log = []
        j = 1
        floor_hours = 0
        arrival = None
        departure = None

        temp_dto = new_dto()
        temp_dto.arrival = None
        temp_dto.departure = None
        temp_dto.floor_hours = 0
        temp_dto.message = ''
        temp_dto.access = []
        temp_dto.log_time = None

        number_of_log = len(punch_data)

        access_list = []
        for log in punch_data:

            access = new_dto()
            if log.direction == 'IN':
                access.direction = 'IN'
                access.time = log.log_time
                access_list.append(access)
                del access
            else:
                access.direction = 'OUT'
                access.time = log.log_time
                access_list.append(access)
                del access

            if log.direction == 'IN':
                if arrival:
                    if log.log_time < arrival:
                        arrival = log.log_time
                else:
                    arrival = log.log_time

                last_direction = 'IN'
                if number_of_log == j:
                    #msg = """Missed the OUT for IN at {0}""".format(Utility().split_time_from_date_time(log.log_time))
                    #temp_missed_log.append(msg)
                    break

                if punch_data[j].direction == 'OUT':
                    start_time = log.log_time
                    end_time = punch_data[j].log_time
                    floor_hours += Utility().time_diff_in_seconds(start_time, end_time)
                # else:
                #     pass

                # else:
                #     msg = """Missed the OUT for IN at {0}""".format(Utility().split_time_from_date_time(log.log_time))
                #     temp_missed_log.append(msg)
            else:
                if departure:
                    if log.log_time > departure:
                        departure = log.log_time
                else:
                    departure = log.log_time

                # if last_direction != "IN":
                #     msg = """Missed the IN for OUT at {0}""".format(Utility().split_time_from_date_time(log.log_time))
                #     temp_missed_log.append(msg)
                last_direction = "OUT"
            j += 1

        temp_dto.log_time = log.log_time
        temp_dto.access = access_list
        temp_dto.arrival = arrival
        temp_dto.departure = departure
        temp_dto.floor_hours = floor_hours
        temp_dto.message = ''
        # if temp_missed_log:
        #     temp_dto.message = ", ".join(temp_missed_log)
        return temp_dto

    def __generate_access_log_list(self, access_logs):
        access_list = []
        for each_item in access_logs:
            temp_dict = {
                "time": each_item.time.strftime('%I:%M %p'),
                "direction": each_item.direction
            }
            access_list.append(temp_dict)
            del temp_dict
        return access_list

    def __set_arrival_time(self, dm_arrival, em_arrival):
        arrival = None
        if dm_arrival:
            arrival = dm_arrival
        if em_arrival:
            if arrival:
                if em_arrival < arrival:
                    arrival = em_arrival
            else:
                arrival = em_arrival
        return arrival

    def __set_departure_time(self, dm_departure, em_departure):
        departure = None
        if dm_departure:
            departure = dm_departure

        if em_departure:
            if not departure:
                departure = em_departure
            else:
                if departure < em_departure:
                    departure = em_departure
        return departure

    def __get_date_range(self, start, end):
        try:
            date_list = []
            delta = end - start
            for i in range(delta.days + 1):
                current_date = start + timedelta(days=i)
                date_list.append(current_date.strftime("%Y-%m-%d"))
        except Exception as err:
            pass
        return date_list

    def __get_all_holidays(self, start_date, end_date):
        holiday_dict = {}
        start_date = start_date.strftime("%Y-%m-%d")
        end_date = end_date.strftime("%Y-%m-%d")

        obj_holidays = HolidayDA().get_all_holidays(start_date, end_date)
        if obj_holidays:
            for each_item in obj_holidays:
                try:
                    holiday_dict[each_item.holiday_date.strftime("%Y-%m-%d")] = each_item.title
                except Exception as err:
                    pass
        return holiday_dict

    def __get_all_weekends(self, start_date, end_date):
        week_end_list = []

        week_ends = Utility().get_all_weekends(start_date, end_date)
        if week_ends:
            for each_day in week_ends:
                try:
                    week_end_list.append(each_day.strftime("%Y-%m-%d"))
                except:
                    pass
        return week_end_list


    def process_employee_attendance_records(self, att_logs):
        attendace_data = {}
        attendace_data["working_hours"] = 0
        attendace_data["first_punch_in"] = ""
        attendace_data["last_punch_out"] = ""
        try:

            log_dict = self.__pre_process_logs(att_logs)

            if log_dict:
                for log_date in log_dict:
                    dm_arrival = None
                    dm_departure = None
                    dm_floor_hours = 0

                    em_arrival = None
                    em_departure = None
                    em_floor_hours = 0

                    dm_data, em_data = self.__segregate_access_log(log_dict[log_date])
                    dto = emp_dto()
                    if dm_data:
                        temp_dto = self.__process_in_and_out(dm_data)
                        dm_arrival = temp_dto.arrival
                        dm_departure = temp_dto.departure
                        dm_floor_hours = temp_dto.floor_hours
                    if em_data:
                        temp_dto = self.__process_in_and_out(em_data)
                        em_arrival = temp_dto.arrival
                        em_departure = temp_dto.departure
                        em_floor_hours = temp_dto.floor_hours

                    arrival = self.__set_arrival_time(dm_arrival, em_arrival)
                    departure = self.__set_departure_time(dm_departure, em_departure)
                    if arrival:
                        attendace_data["first_punch_in"] = arrival.strftime("%I:%M %p")
                    if departure:
                        attendace_data["last_punch_out"] = departure.strftime("%I:%M %p")
                    attendace_data["working_hours"] = dm_floor_hours + em_floor_hours
        except  Exception as err:
            result = {'error': str(err), "status": 499}
        return attendace_data


    def get_emp_attendance_log(self, user_id, emp_code, month, year):
        try:
            log_dict = {}
            res_list = []

            date_dict = {}
            work_percentage = 0
            required_work_hrs = 28800

            punctual_time_str = settings.PUNCH_IN_CONFIG['punctual']['end_time']
            start_date = Utility().get_first_day_of_month(dt=None, d_years=year, d_months=month)
            end_date = Utility().get_last_day_of_month(start_date)
            att_logs = AttendanceDA().get_emp_access_log(emp_code, start_date.strftime("%Y-%m-%d"), end_date.strftime("%Y-%m-%d"))
            log_dict = self.__pre_process_logs(att_logs)


            if log_dict:
                for log_date in log_dict:

                    dm_data, em_data = self.__segregate_access_log(log_dict[log_date])
                    dto = emp_dto()
                    if dm_data:
                        temp_dto = self.__process_in_and_out(dm_data)
                        dto.log_time = temp_dto.log_time
                        dto.dm_access = temp_dto.access
                        dto.dm_arrival = temp_dto.arrival
                        dto.dm_departure = temp_dto.departure
                        dto.dm_floor_hours = temp_dto.floor_hours
                        if temp_dto.message:
                            dto.error_message = temp_dto.message
                        del temp_dto

                    if em_data:
                        temp_dto = self.__process_in_and_out(em_data)
                        dto.log_time = temp_dto.log_time
                        dto.em_access = temp_dto.access
                        dto.em_arrival = temp_dto.arrival
                        dto.em_departure = temp_dto.departure
                        dto.em_floor_hours = temp_dto.floor_hours
                        if temp_dto.message:
                            dto.error_message = dto.error_message + " ." + temp_dto.message
                        del temp_dto

                    dto.arrival = self.__set_arrival_time(dto.dm_arrival, dto.em_arrival)
                    dto.departure = self.__set_departure_time(dto.dm_departure, dto.em_departure)

                    if dto.arrival and dto.departure:
                        dto.total_hours = Utility().time_diff_in_seconds(dto.arrival, dto.departure)

                    dto.total_floor_hours = dto.dm_floor_hours + dto.em_floor_hours
                    work_percentage = int(math.floor((dto.total_floor_hours/required_work_hrs)*100))

                    if len(dto.dm_access) < len(dto.em_access):
                        dto.is_dm_employee = False

                    punctual_time = Utility().create_date_time(log_date, punctual_time_str)

                    is_late = 0
                    late_hours = ''
                    if (dto.arrival and punctual_time) and (dto.arrival > punctual_time):
                        is_late = 1
                        late_hours = Utility().time_diff_in_seconds(punctual_time, dto.arrival)
                        late_hours = Utility().seconds_to_hour_and_minute(late_hours) + " hrs late"

                        if (dto.total_floor_hours and required_work_hrs) and  dto.total_floor_hours >= required_work_hrs:
                            is_late = 2


                    if dto.is_dm_employee:
                        first_log = "DM"
                    else:
                        first_log = "EM"

                    res_dict = {
                        "error": "",
                        "date_status": "working",
                        "date_remark": "",
                        "work_percentage": work_percentage,
                        "date": log_date,
                        "effective_hours": Utility().seconds_to_hour_and_minute(dto.total_floor_hours),
                        "gross_hours": Utility().seconds_to_hour_and_minute(dto.total_hours),
                        "arrival": {
                            "is_late": is_late,
                            "late_hours": late_hours
                        },
                        "log": {
                            "first_log": first_log,
                            "dm_log": self.__generate_access_log_list(dto.dm_access),
                            "em_log": self.__generate_access_log_list(dto.em_access),
                        }
                    }

                    date_dict[log_date] = res_dict
                    del res_dict

                date_list = self.__get_date_range(start_date, end_date)
                holiday_dict = self.__get_all_holidays(start_date, end_date)
                week_ends_list = self.__get_all_weekends(start_date, end_date)

                for each_date in date_list:
                    curr_date = Utility().convert_string_to_date_time(each_date, "%Y-%m-%d")
                    if curr_date > datetime.now():
                        # temp_dict = {
                        #     "error": "",
                        #     "date_status": "future",
                        #     "date_remark": "-",
                        #     "date": each_date
                        # }
                        # res_list.append(temp_dict)
                        continue

                    temp_dict = date_dict.get(each_date, None)
                    if not temp_dict:
                        holiday = holiday_dict.get(each_date, None)
                        if holiday:
                            temp_dict = {
                                "error": "",
                                "date_status": "holiday",
                                "date_remark": holiday,
                                "date": each_date
                            }
                        else:
                            if each_date in week_ends_list:
                                temp_dict = {
                                "error": "",
                                "date_status": "weekend",
                                "date_remark": 'Weekly Off',
                                "date": each_date
                                }
                            else:
                                temp_dict = {
                                "error": "",
                                "date_status": "leave",
                                "date_remark": 'Leave',
                                "date": each_date
                                }
                    res_list.append(temp_dict)
                    del temp_dict
        except  Exception as err:
            result = {'error': str(err), "status": 499}
            self.__log.error(self.__exception.get_exception())
            return result

        return res_list


    def get_team_attendance_average(self, user_id, start_date, end_date):
        response = {
            'team_avg_hours': "",
            'team_avg_punctual_time': "",
            'error': None}
        try:
            punctual_time_str = settings.PUNCH_IN_CONFIG['punctual']['end_time']
            total_days = 0
            punctual_days = 0
            total_work_hours = 0
            team_avg_hours = 0
            team_avg_punctual_time = 0
            team_count = 0
            role_id, role_name = UserDA().get_user_role_by_id(user_id)
            if role_id in (1, 2, 3):
                response['team_avg_hours'] = 'N.A'
                response['team_avg_punctual_time'] = 'N.A'
                return response
            if role_id == 4:
                team_member_list = UserDA().get_current_team_members_by_lead_id(user_id)
            else:
                team_member_list = UserDA().get_current_team_members_by_emp_id(user_id)

            if team_member_list:
                for each_user in team_member_list:
                    team_count += 1
                    emp_code = UserMappingBL().get_employee_code(each_user.id)
                    att_logs = AttendanceDA().get_emp_attendance_log(emp_code, start_date, end_date)

                    if att_logs:
                        emp_avg_hours = 0
                        emp_avg_punctual_time = 0
                        for each_item in att_logs:
                            total_days += 1
                            attendance_date = str(each_item[0])
                            work_hours = each_item[1]
                            arrival = each_item[2]
                            total_work_hours += work_hours
                            punctual_time = Utility().create_date_time(attendance_date, punctual_time_str)
                            if arrival and punctual_time:
                                if arrival < punctual_time:
                                    punctual_days += 1
                        emp_avg_hours = int(total_work_hours / total_days)
                        emp_avg_punctual_time = int((punctual_days / total_days) * 100)
                        team_avg_hours += emp_avg_hours
                        team_avg_punctual_time += emp_avg_punctual_time

                team_avg_hours = int(team_avg_hours / team_count)
                team_avg_hours = Utility().seconds_to_hour_and_minute(team_avg_hours)
                team_avg_punctual_time = int(team_avg_punctual_time / team_count)
            response['team_avg_hours'] = str(team_avg_hours)
            response['team_avg_punctual_time'] = str(team_avg_punctual_time) + "%"
            return response
        except Exception as error:
            response["error"] = settings.ERROR_MSG['application_error']\
                .format(error, self.__log.error(self.__exception.get_exception()))

            return response

    def get_emp_attendance_average(self, emp_code, start_date, end_date):
        response = {
            "my_avg_hours": '00:00',
            "my_avg_punctual_time": "0%",
            "error": None
        }
        try:
            punctual_time_str = settings.PUNCH_IN_CONFIG['punctual']['end_time']
            total_days = 0
            punctual_days = 0
            total_work_hours = 0
            emp_avg_hours = 0
            emp_avg_punctual_time = 0
            att_logs = AttendanceDA().get_emp_attendance_log(emp_code, start_date, end_date)
            if att_logs:
                for each_item in att_logs:
                    total_days += 1
                    attendance_date = str(each_item[0])
                    work_hours = each_item[1]
                    arrival = each_item[2]
                    total_work_hours += work_hours
                    punctual_time = Utility().create_date_time(attendance_date, punctual_time_str)
                    if arrival and punctual_time:
                        if arrival < punctual_time:
                            punctual_days += 1
                emp_avg_hours = int(total_work_hours / total_days)
                emp_avg_hours = Utility().seconds_to_hour_and_minute(emp_avg_hours)
                emp_avg_punctual_time = int((punctual_days / total_days) * 100)
                response["my_avg_hours"] = str(emp_avg_hours)
                response["my_avg_punctual_time"] = str(emp_avg_punctual_time) + "%"
        except Exception as error:
            response["error"] = settings.ERROR_MSG['application_error']\
                .format(error, self.__log.error(self.__exception.get_exception()))
        return response

    def utc2local(self):
        return datetime.now() + timedelta(hours=5, minutes=30)

    def get_web_punch_check(self, emp_code):
        res_dict = {}
        res_dict["direction"] = None
        res_dict["is_display"] = True
        str_date = datetime.now().strftime("%Y-%m-%d")
        att_log = AttendanceDA().get_emp_last_access_log(emp_code, str_date)
        if att_log:
            direction = str(att_log[2]).strip()
            if direction.lower() == "in":
                res_dict["direction"] = "OUT"
            else:
                res_dict["direction"] = "IN"
            res_dict["is_display"] = "TRUE"

            # TODO commented when time zone changed from  utc to asia/kolkota
            # current_time = self.utc2local().strftime("%Y-%m-%d %H:%M:%S" )


            # TODO comment if timezone change back to utc
            current_time = datetime.now().strftime("%Y-%m-%d %H:%M:%S" )

            log_time = Utility().convert_string_to_date_time(att_log[1])
            current_time = Utility().convert_string_to_date_time(current_time)
            # Convert to Unix timestamp
            d1_ts = time.mktime(current_time.timetuple())
            d2_ts = time.mktime(log_time.timetuple())
            if int(d1_ts - d2_ts) < 180:
                res_dict["is_display"] = "FALSE"
        else:
            res_dict["direction"] = "IN"
            res_dict["is_display"] = "TRUE"
        return res_dict

    def create_web_punch(self, emp_code, data):
        result = {"error": "", "success": "", "status": 200}
        try:
            dto = new_dto()
            dto.emp_code = emp_code
            dto.direction = data.get('direction', None)
            # commented when time zone changed from utc to asia/kolkota

            # dt_time = self.utc2local()
            # dto.log_date = dt_time.strftime("%Y-%m-%d %H:%M:%S")

            #comment if  time change back to utc
            dto.log_date = datetime.now().strftime("%Y-%m-%d %H:%M:%S")

            user=UserDA().get_user_by_emp_id(emp_code)
            if(self.is_work_from_home_allowed(user.id)):
                if dto.direction:
                    dto.direction = str(dto.direction).lower()
                    if dto.direction == "in":
                        dto.device_serial_no = settings.ATT_DEVICE['DM' + "_IN"]['SerialNumber']
                        dto.device_name = "Web IN"
                        msg = "You successfully punched in remotely."
                    elif dto.direction == "out":
                        dto.device_serial_no = settings.ATT_DEVICE['DM' + "_OUT"]['SerialNumber']
                        dto.device_name = "Web OUT"
                        msg = "You successfully punched out remotely."

                    AttendanceDA().cretate_emp_access_log(dto)
                    result["success"] = msg
                else:
                    msg = "Not able to do a remote punch in/out this time."
                    result["success"] = msg
                    result['status'] = 499
            else:
                msg = settings.ERROR_MSG.get('access_denied') # "No approved work from home request"
                result['status'] = 403
                result["success"] = msg

        except Exception as err:
            result['status'] = 499
            result["error"] = settings.ERROR_MSG['application_error']\
                .format(str(err), self.__log.error(self.__exception.get_exception()))
        finally:
            return result


    def get_all_upcoming_holidays(self):
        response = []
        try:
            current_date = date.today()
            holidays = HolidayDA().get_upcoming_holidays(current_date)
            if holidays:
                for row in holidays:
                    result = {
                        "company_id":row.company_id,
                        "holiday_date":row.holiday_date,
                        "holiday_title":row.title,
                        "description":row.description
                    }
                    response.append(result)
            else:
                response = [{"error":'No Records found'}]
        except Exception as err:
            response = [{"error":err}]
        return response

    def __get_user_dict(self):
        user_dict = {}
        users = UserDA().get_all_active_users()
        if users:
            for user in  users:
                user_dict[str(user.username)] = f'{user.first_name} {user.last_name}'
        return user_dict

    def get_wfh_employees(self, user_id, work_date):
        wfh_emps = []
        role_id, role_name = UserDA().get_user_role_by_id(user_id)
        if role_id not in (1, 2, 3):
            return [{"error": "You have no permission to view this page !!!"}]

        att_log = AttendanceDA().get_wfh_employees(work_date)

        if att_log:
            user_dict = self.__get_user_dict()
            for each_item in att_log:
                emp_name = user_dict.get(str(each_item[0]), '-')
                wfh_emps.append({"emp_name":emp_name,"emp_code":each_item[0]})
        return wfh_emps

    def previous_week_range(self, date):
        end = datetime.now() - timedelta(days=((datetime.now().isoweekday() + 1) % 7))
        start = end - timedelta(days=6)
        return start, end

    def is_work_from_home_allowed(self, user_id):
        #TODO WFH module
        date=datetime.today().strftime("%Y-%m-%d")
        approved_wfh=pAttendanceDA().get_approved_wfh_request(user_id,date)
        if approved_wfh:
            return 1
        else:
            return 0

    def get_dashboard_attendance_average(self, user_id):
        attendance = {
            "this_week": {},
            "last_week": {},
            "error": None,
            "direction": "",
            "is_display": "",
            "is_work_from_home": 0,
            "today_attendance_stats": {}
        }
        emp_code = UserMappingBL().get_employee_code(user_id)
        last_week_start, last_week_end = self.previous_week_range(date.today())
        this_week_start = date.today().today() - timedelta(days=date.today().today().weekday()+1)
        this_week_end = date.today()
        if date.today().weekday() == 6:
            this_week_start = date.today()
        this_week_end = date.today()

        attendance['is_work_from_home'] = self.is_work_from_home_allowed(user_id)
        res_dict = self.get_web_punch_check(emp_code)
        attendance['is_display'] = res_dict["is_display"]
        attendance['direction'] = res_dict["direction"]

        last_week_emp_avg = self.get_emp_attendance_average(emp_code, last_week_start.date(), last_week_end.date())
        this_week_emp_avg = self.get_emp_attendance_average(emp_code, this_week_start, this_week_end)
        this_week_team_avg = self.get_team_attendance_average(user_id, this_week_start, this_week_end)
        last_week_team_avg = self.get_team_attendance_average(user_id, last_week_start.date(), last_week_end.date())
        this_week_time_sheet = TimesheetReportBL().get_team_timesheet_summary(user_id, this_week_start, this_week_end)
        last_week_time_sheet = TimesheetReportBL().get_team_timesheet_summary(user_id, last_week_start.date(), last_week_end.date())

        attendance['this_week'] = {
            "emp_avg_hours": this_week_emp_avg['my_avg_hours'],
            "emp_on_arrival": this_week_emp_avg['my_avg_punctual_time'],
            "team_avg_hours": this_week_team_avg['team_avg_hours'],
            "team_on_arrival": this_week_team_avg['team_avg_punctual_time'],
            "team_time_sheet_per": this_week_time_sheet['team_time_sheet_submit'],
            "emp_time_sheet_per": this_week_time_sheet['emp_time_sheet_submit']
        }
        attendance['last_week'] = {
            "emp_avg_hours": last_week_emp_avg['my_avg_hours'],
            "emp_on_arrival": last_week_emp_avg['my_avg_punctual_time'],
            "team_avg_hours": last_week_team_avg['team_avg_hours'],
            "team_on_arrival": last_week_team_avg['team_avg_punctual_time'],
            "team_time_sheet_per": last_week_time_sheet['team_time_sheet_submit'],
            "emp_time_sheet_per": last_week_time_sheet['emp_time_sheet_submit']
        }

        attendance['today_attendance_stats'] = self.get_today_attendance_stats(user_id)


        if last_week_emp_avg['error'] !=None:
            attendance['error'] = str(last_week_emp_avg['error'])
        if last_week_team_avg['error'] !=None:
            attendance['error'] = str(last_week_team_avg['error'])
        if this_week_emp_avg['error'] !=None:
            attendance['error'] = str(this_week_emp_avg['error'])
        if this_week_team_avg['error'] !=None:
            attendance['error'] = str(this_week_team_avg['error'])
        return attendance

    def __get_list_diff(self, li1, li2):
        return list(set(li1) - set(li2)) + list(set(li2) - set(li1))

    def __get_todays_leaves(self, current_date):
        #TODO Leave Management
        return []

    def get_today_attendance_stats(self, user_id):
        response = {
            "is_display": 0,
            "no_of_present": 0,
            "no_of_wfh": 0,
            "no_of_leave": 0,
            "no_of_not_punch": 0,
        }
        all_employees = []
        total_employees = 0
        c_level_emps = []
        active_users_emp_code = []
        puched_emps = []

        no_of_wfh = 0
        no_of_present = 0
        no_of_leave = 0
        no_of_not_punch = 0
        try:
            role_id, role_name = UserDA().get_user_role_by_id(user_id)
            if role_id in (1, 2, 3, 4):
                response['is_display'] = 1

            emps = UserDA().get_all_active_users()
            for emp in emps:
                try:
                    total_employees += 1
                    active_users_emp_code.append(int(emp.username))
                except :
                    pass

            results = Employee().get_att_exclude_employees_code()
            if results:
                for each_item in results:
                    try:
                        c_level_emps.append(int(each_item.emp_code))
                        total_employees = total_employees - 1
                    except :
                        pass


            active_users_emp_code = self.__get_list_diff(active_users_emp_code, c_level_emps)

            current_date = date.today().strftime("%Y-%m-%d")
            attendance_details, err = AttendanceDA().get_attendance_details_by_date(current_date, current_date)
            if attendance_details:
                for attendance in attendance_details:
                    emp_code = int(attendance[0])
                    device = str(attendance[1]).lower()
                    if emp_code in active_users_emp_code:
                        if emp_code in puched_emps:
                            continue
                        else:
                            puched_emps.append(emp_code)
                            if device == "web in":
                                no_of_wfh += 1
                            else:
                                no_of_present += 1

            active_users_emp_code = self.__get_list_diff(active_users_emp_code, puched_emps)

            #TO DO get_leaves_by_date_range
            status_requested_id = settings.LEAVE_REQUEST_STATUS['Requested']
            status_approved_id = settings.LEAVE_REQUEST_STATUS['Approved']
            leaves = LeaveDA().get_all_leaves_by_date_range(date.today(), date.today(), \
            status = [status_requested_id, status_approved_id])
            for each_emp in active_users_emp_code:
                emp = emps.get(username=each_emp)
                try:
                    leave = leaves.get(employee_id=emp.id)
                    no_of_leave += 1
                except:
                    continue

            no_of_not_punch = len(active_users_emp_code) - no_of_leave
            response['no_of_present'] = no_of_present
            response['no_of_wfh'] = no_of_wfh
            response['no_of_not_punch'] = no_of_not_punch
            response['no_of_leave'] = no_of_leave
            #TODO leave number
        except Exception as err:
            self.__logs.error(self.__exception.get_exception())
        return response

    def get_attendance_details_by_date(self, att_date, user_id, is_mobile=False):
        result = {"error": None, "detail_items": None, 'summary':None}
        # dto = new_dto()
        # dto.date = data.get('date', None)

        all_employees = []
        total_employees = 0
        c_level_emps = []
        active_users_emp_code = []
        puched_emps = []
        leave_emps = []

        no_of_wfh = 0
        no_of_present = 0
        no_of_leave = 0
        no_of_not_punch = 0

        summary = {
            "is_display": 1,
            "no_of_present": 0,
            "no_of_wfh": 0,
            "no_of_leave": 0,
            "no_of_not_punch": 0,
        }

        active_users_dict = {}
        detail_items_list = []

        try:
            role_id, role_name = UserDA().get_user_role_by_id(user_id)
            if role_id not in (1, 2, 3, 4):
                result['error'] = settings.ERROR_MSG.get('access_denied')
                return result

            if is_mobile and role_id == 4:
                emps = UserDA().get_current_team_members_by_lead_id(user_id)
            else:
                emps = UserDA().get_all_active_users()
            for emp in emps:
                try:
                    total_employees += 1
                    active_users_emp_code.append(int(emp.username))
                    active_users_dict[int(emp.username)] = emp.first_name + " " + emp.last_name
                except :
                    pass

            results = Employee().get_att_exclude_employees_code()
            if results:
                for each_item in results:
                    try:
                        c_level_emps.append(int(each_item.emp_code))
                        total_employees = total_employees - 1
                    except :
                        pass
            if is_mobile and role_id==4:
                if active_users_emp_code:
                    active_users_emp_code = active_users_emp_code
            else:
                active_users_emp_code = self.__get_list_diff(active_users_emp_code, c_level_emps)

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
                            temp_dict = {}
                            temp_dict["emp_id"] = emp_code
                            temp_dict["emp_name"] = active_users_dict.get(emp_code)
                            temp_dict["punch_in"] = punch_in.strftime("%I %M %S %p")

                            puched_emps.append(emp_code)
                            if device == "web in":
                                no_of_wfh += 1
                                temp_dict["status"] = "WFH"
                            else:
                                no_of_present += 1
                                temp_dict["status"] = "Present"

                            detail_items_list.append(temp_dict)
                            del temp_dict

            active_users_emp_code = self.__get_list_diff(active_users_emp_code, puched_emps)

            #no of leave
            obj_att_date = datetime.strptime(att_date, "%Y-%m-%d")
            status_requested_id = settings.LEAVE_REQUEST_STATUS['Requested']
            status_approved_id = settings.LEAVE_REQUEST_STATUS['Approved']
            leaves = LeaveDA().get_all_leaves_by_date_range(obj_att_date,obj_att_date, \
            status = [status_requested_id, status_approved_id])

            for each_emp in active_users_emp_code:
                if is_mobile and role_id==4:
                    for ec in emps:
                        if ec.username==each_emp:
                            emp=ec
                else:
                    emp = emps.get(username=each_emp)
                try:
                    leave = leaves.get(employee_id=emp.id)
                    temp_dict = {}
                    temp_dict["emp_id"] = emp.id
                    temp_dict["emp_name"] = active_users_dict.get(each_emp)
                    temp_dict["status"] = "Leave"
                    temp_dict["punch_in"] = "-"
                    detail_items_list.append(temp_dict)
                    del temp_dict
                    leave_emps.append(each_emp)
                    no_of_leave += 1
                except:
                    continue

            no_of_not_punch = len(active_users_emp_code) - no_of_leave

            active_users_emp_code = self.__get_list_diff(active_users_emp_code, leave_emps)

            for each_item in active_users_emp_code:
                temp_dict = {}
                temp_dict["emp_id"] = each_item
                temp_dict["emp_name"] = active_users_dict.get(each_item)
                temp_dict["status"] = "Not Punched Yet"
                temp_dict["punch_in"] = "-"
                detail_items_list.append(temp_dict)
                del temp_dict

            summary['no_of_present'] = no_of_present
            summary['no_of_wfh'] = no_of_wfh
            summary['no_of_not_punch'] = no_of_not_punch
            summary['no_of_leave'] = no_of_leave

            result['summary'] = summary
            result['detail_items'] = detail_items_list
            result['error'] = att_date
            return result
        except Exception as err:
            result["error"] = settings.ERROR_MSG['application_error']\
                .format(str(err), self.__log.error(self.__exception.get_exception()))
            return result



    def __get_all_off_days(self, start_date, end_date):
        holiday_list = []
        work_days = []

        week_ends = Utility().get_all_weekends(start_date, end_date)

        start_date = start_date.strftime("%Y-%m-%d")
        end_date = end_date.strftime("%Y-%m-%d")

        obj_workingdays = HolidayDA().get_additional_working_days(start_date, end_date)
        if obj_workingdays:
            for day in obj_workingdays:
                work_days.append(day.working_date.strftime("%Y-%m-%d"))


        # week_ends = Utility().get_all_weekends(start_date, end_date)
        # print(week_ends)
        if week_ends:
            for each_day in week_ends:
                each_day = each_day.strftime("%Y-%m-%d")
                if each_day in work_days:
                    continue
                holiday_list.append(each_day)

        obj_holidays = HolidayDA().get_holidays(start_date, end_date)
        if obj_holidays:
            for each_item in obj_holidays:
                each_day = each_item.holiday_date.strftime("%Y-%m-%d")
                if each_day in work_days:
                    continue
                holiday_list.append(each_day)
        return holiday_list




    def get_not_punched_employee_list(self, start_date, end_date, user_id):
        # start_date :  Should be string with format yyyy-mm-dd
        # end_date :  Should be string with format yyyy-mm-dd

        result = {"error": None, "emp_list": None}
        c_level_emps = []
        active_users_emp_code = []
        missed_list = []
        emp_code_mapping = {}

        try:
            leave_status = [
                settings.LEAVE_REQUEST_STATUS['Requested'],
                settings.LEAVE_REQUEST_STATUS['Approved']
            ]
            obj_start_date = datetime.strptime(start_date, "%Y-%m-%d")
            obj_end_date = datetime.strptime(end_date, "%Y-%m-%d")
            if obj_end_date.month == datetime.now().month:
                obj_end_date = datetime.now()
            role_id, role_name = UserDA().get_user_role_by_id(user_id)
            if role_id not in (1, 2, 3,):
                result['error'] = settings.ERROR_MSG.get('access_denied')
                return result

            emps = UserDA().get_all_active_users()
            for emp in emps:
                try:
                    emp_code_mapping[emp.id] = int(emp.username)
                except :
                    pass

            results = Employee().get_att_exclude_employees_code()
            if results:
                for each_item in results:
                    try:
                        c_level_emps.append(int(each_item.emp_code))
                    except :
                        pass

            emp_work_dict = {}
            emp_leave_dict = {}
            attendance_details, err = AttendanceDA().get_attendance_details_by_date(start_date, end_date)
            if attendance_details:
                for attendance in attendance_details:
                    emp_code = int(attendance[0])
                    #device = str(attendance[1]).lower()
                    punch_in = str(attendance[2]).lower()
                    punch_in = Utility().convert_string_to_date_time(punch_in)
                    if punch_in:
                        punch_in = punch_in.strftime("%Y-%m-%d")
                    if emp_code in emp_work_dict:
                        temp_list = emp_work_dict[emp_code]
                        temp_list.append(punch_in)
                        emp_work_dict[emp_code] = temp_list
                        del temp_list
                    else:
                        emp_work_dict[emp_code] = [punch_in]

            emp_leaves = LeaveDA().get_leaves_by_date_range(obj_start_date, obj_end_date)
            if emp_leaves:
                for each_leave in emp_leaves:
                    status = each_leave.status
                    if status not in leave_status:
                        continue
                    emp_code = emp_code_mapping.get(each_leave.employee_id, 0)
                    leave_date = each_leave.leave_date.strftime("%Y-%m-%d")
                    if emp_code in emp_leave_dict:
                        temp_list = emp_leave_dict[emp_code]
                        temp_list.append(leave_date)
                        emp_leave_dict[emp_code] = temp_list
                        del temp_list
                    else:
                        emp_leave_dict[emp_code] = [leave_date]

            dates_in_range = Utility().get_date_range(obj_start_date, obj_end_date)
            month_days = []
            if dates_in_range:
                for each_date in dates_in_range:
                    month_days.append(each_date.strftime("%Y-%m-%d"))

            holiday_list = self.__get_all_off_days(obj_start_date, obj_end_date)
            #self.__log.error(str(emp_work_dict))
            if emps:
                for emp in emps:
                    if int(emp.username) in c_level_emps:
                        continue

                    try:
                        date_joined= Utility().convert_string_to_date_time(emp.date_joined.strftime("%Y-%m-%d"), "%Y-%m-%d")
                    except:
                        date_joined = None

                    missed_dates = []
                    emp_name = emp.first_name + " " + emp.last_name
                    emp_id = emp.id
                    emp_code = int(emp.username) #todo
                    emp_worked_dates = emp_work_dict.get(emp_code, [])
                    emp_leave_dates = emp_leave_dict.get(emp_code, [])
                    if month_days:
                        for each_day in month_days:
                            obj_each_day = Utility().convert_string_to_date_time(each_day, "%Y-%m-%d")

                            if date_joined:
                                if obj_each_day < date_joined:
                                    continue

                            if each_day in holiday_list:
                                continue
                            elif each_day in emp_worked_dates:
                                continue
                            elif each_day in emp_leave_dates:
                                continue
                            else:
                                missed_dates.append(each_day)

                    if missed_dates:
                        temp_dict = {"emp_name":emp_name, "emp_id":emp_id, "missed_date":missed_dates}
                        missed_list.append(temp_dict)
                        del temp_dict

                result['emp_list'] = missed_list

        except Exception as err:
            result["error"] = settings.ERROR_MSG['application_error']\
                .format(str(err), self.__log.error(self.__exception.get_exception()))
        return result

