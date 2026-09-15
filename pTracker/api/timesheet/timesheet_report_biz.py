from  datetime import datetime, timedelta

from django.conf import settings
from types import SimpleNamespace
from calendar import monthrange

from django.http.response import HttpResponse

from pTracker.common.utility import Utility
from pTracker.common.logs import Logs
from pTracker.dataaccess.ptracker_access.timesheet_da import  TimeSheetDA
from pTracker.dataaccess.ptracker_access.project_da import  ProjectDA
from pTracker.dataaccess.ptracker_access.user_da import UserDA
from pTracker.dataaccess.ptracker_access.leave_da import LeaveDA
from pTracker.dataaccess.ptracker_access.attendance import AttendanceDA
from pTracker.wiki.utils.exception import ExceptionHandler
from pTracker.user_management.holiday_da import HolidayDA
from pTracker.user_management.employee import Employee


def new_dto():
    dto = SimpleNamespace()
    return dto

class TimesheetReportBL():
    def __init__(self):
        self.__exception = ExceptionHandler()
        self.__log = Logs()

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

    def __get_all_leaves(self, emp_id, start_date, end_date):
        leave_list = []
        #TODO Leave List Logic

        # week_ends = Utility().get_all_weekends(start_date, end_date)
        # if week_ends:
        #     for each_day in week_ends:
        #         try:
        #             week_end_list.append(each_day.strftime("%Y-%m-%d"))
        #         except:
        #             pass
        return leave_list

    def __get_user_leaves(self, user_id, start_date_obj, end_date_obj):
        leaves = LeaveDA().get_employee_leave_by_date(start_date_obj,end_date_obj,user_id)
        return leaves.count()

    def get_timesheet_summary(self, user_id, start_date, end_date, is_include_not_missing_emp=1):
        result = {"error": "", "success": ""}
        all_employees = []
        missed_employees = []
        c_level_emps = []

        try:
            obj_start = Utility().convert_string_to_date_time(start_date, "%Y-%m-%d")
            if not obj_start:
                return [{"error": "Invalid start date !!!"}]
            obj_end = Utility().convert_string_to_date_time(end_date, "%Y-%m-%d")
            if not obj_end:
                return [{"error": "Invalid end date !!!"}]

            if obj_start > obj_end:
                return [{"error": "Start date should be less than end date !!!"}]

            delta = obj_end - obj_start
            if delta.days > 90:
                return [{"error": "The date difference between dates should be less than 90 !!!"}]

            if obj_end > datetime.now():
                end_date = (datetime.now() - timedelta(days=1)).strftime("%Y-%m-%d")
                obj_end = datetime.now() - timedelta(days=1)
                # end_date = datetime.now().strftime("%Y-%m-%d")
                # obj_end = datetime.now()

            user_dict, all_employees = self.__get_user_dict()

            total_dates = self.__get_date_range(obj_start, obj_end)
            number_of_days = len(total_dates)

            role_id, role_name = UserDA().get_user_role_by_id(user_id)
            if role_id in (1, 2, 3):
                emp_ids = []
            elif role_id == 4:
                emp_ids = [user_id]
                all_employees = [user_id]
                team_member_list = UserDA().get_current_team_members_by_lead_id(user_id)
                for each_user in team_member_list:
                    emp_ids.append(each_user.id)
                    all_employees.append(each_user.id)
            else:
                emp_ids = [user_id]
                all_employees = [user_id]

            from_date = datetime.strptime(start_date,'%Y-%m-%d')
            to_date = datetime.strptime(end_date,'%Y-%m-%d')
            weekends_in_month = Utility().get_all_weekends(from_date, to_date)
            weekends = int(len(weekends_in_month))
            # holidays = HolidayDA().get_all_holidays(start_date, end_date)
            work_hours_dict = self.get_actual_wrk_hr_employee_dict(obj_start, obj_end )

            holiday_count_excluded_weekends = self.holiday_count_excluding_week_days(obj_start,obj_end)
            total_working_days = number_of_days - weekends - int(holiday_count_excluded_weekends)

            # total_working_days = number_of_days - weekends - int(holidays.count())

            # holidays_list = [holiday.holiday_date for holiday in holidays]
            timesheets = TimeSheetDA().get_all_time_sheets(start_date, end_date)
            approved = {}
            submitted = {}
            rejected = {}
            users = []
            report_list = []
            total_claimed_hrs = {}

            for sheet in timesheets:
                if sheet.user_id not in all_employees:
                    continue

                if emp_ids:
                    if sheet.user_id not in emp_ids:
                        continue

                # if sheet.timesheet_date not in weekends_in_month\
                #     and sheet.timesheet_date not in holidays_list:

                if sheet.user_id in users:
                    if sheet.status == 'SUBMITTED':
                        if sheet.user_id in submitted:
                            submitted[sheet.user_id].append(sheet)
                        else:
                            submitted[sheet.user_id] = [sheet]
                    if sheet.status == 'APPROVED':
                        if sheet.user_id in approved:
                            approved[sheet.user_id].append(sheet)
                        else:
                            approved[sheet.user_id] = [sheet]
                    if sheet.status == 'REJECTED':
                        if sheet.user_id in rejected:
                            rejected[sheet.user_id].append(sheet)
                        else:
                            rejected[sheet.user_id] = [sheet]
                    total_claimed_hrs[sheet.user_id] = total_claimed_hrs[sheet.user_id]+sheet.total_duration
                else:
                    if sheet.status == 'SUBMITTED':
                        submitted[sheet.user_id] = [sheet]
                    if sheet.status == 'APPROVED':
                        approved[sheet.user_id] = [sheet]
                    if sheet.status == 'REJECTED':
                        rejected[sheet.user_id] = [sheet]
                    users.append(sheet.user_id)
                    total_claimed_hrs[sheet.user_id] = sheet.total_duration

            timesheet_report_list = {
                'user' : '',
                'submitted_cnt' : 0,
                'approved_cnt' : 0,
                'missing_cnt' : 0,
                'submitted_per' : 0,
                'approved_per': 0,
                'missing_per': 0,
                'working_days' : 0,
                'leave':0,
                'claimed_hrs':0,
                'actual_work_hrs': 0,
                'required_hrs': 0,
                'is_below_required_wrk_hrs': 0
            }

            missed_employees = set(all_employees) - set(users)
            missed_employees = set(missed_employees) - set([1,2,3,4,9,10,20,22,77])

            for user in users:
                try:
                    count_of_approved = len(approved[user])
                except:
                    count_of_approved = 0
                try:
                    count_of_rejected = len(rejected[user])
                except:
                    count_of_rejected = 0
                try:
                    count_of_submittd = len(submitted[user])
                except:
                    count_of_submittd = 0

                count_of_submittd = count_of_submittd + count_of_approved + count_of_rejected
                get_user_leaves = int(self.__get_user_leaves(user, obj_start, obj_end))
                user_working_days = total_working_days - get_user_leaves
                if user_working_days < 0:
                    user_working_days = 0
                count_of_missing = user_working_days - int(count_of_submittd) #- get_user_leaves

                submitted_per = 0
                approved_per = 0
                missing_per = 0

                if user_working_days:
                    submitted_per = round(count_of_submittd / user_working_days * 100)

                if submitted_per > 100:
                    submitted_per = 100

                if count_of_submittd:
                    approved_per = round(count_of_approved / count_of_submittd * 100)

                if approved_per > 100:
                    approved_per = 100

                if user_working_days:
                    missing_per = round(count_of_missing / user_working_days * 100)

                if missing_per > 100:
                    missing_per = 100

                #user_name = UserDA().get_user_by_id(user_id=user)
                user_name = user_dict.get(user, str(user))
                claimed_hrs = total_claimed_hrs.get(user, 0)
                formatted_claimed_hrs = Utility().seconds_to_hour_and_minute(claimed_hrs)
                worked_hrs = work_hours_dict.get(user, 0)
                formatted_worked_hrs = Utility().seconds_to_hour_and_minute(worked_hrs)
                required_wrk_hrs = user_working_days * 28800
                formatted_required_wrk_hrs = Utility().seconds_to_hour_and_minute(required_wrk_hrs)
                if claimed_hrs < required_wrk_hrs:
                    is_below_required_wrk_hrs = 1
                else:
                    is_below_required_wrk_hrs = 0

                if count_of_missing < 0:
                    count_of_missing = 0
                if int(missing_per) < 0:
                    missing_per = 0
                timesheet_report_list = {
                'emp_id' : user,
                'user' : user_name,
                'submitted_cnt': count_of_submittd,
                'approved_cnt': count_of_approved,
                'missing_cnt' : count_of_missing,
                'submitted_per' : submitted_per,
                'approved_per': approved_per,
                'missing_per': missing_per,
                'working_days' : total_working_days,
                'leave':get_user_leaves,
                'claimed_hrs':formatted_claimed_hrs,
                'actual_work_hrs' : formatted_worked_hrs,
                'required_hrs' : formatted_required_wrk_hrs,
                'is_below_required_wrk_hrs': is_below_required_wrk_hrs,
                'submitted_minutes':claimed_hrs,
                'required_minutes': required_wrk_hrs,
                'actual_work_minutes': worked_hrs
                }
                if is_include_not_missing_emp:
                    report_list.append(timesheet_report_list)
                else:
                    if count_of_missing > 0:
                        report_list.append(timesheet_report_list)

            for user in missed_employees:
                get_user_leaves = int(self.__get_user_leaves(user, obj_start, obj_end))
                user_name = user_dict.get(user, '')
                worked_hrs = work_hours_dict.get(user, 0)
                formatted_worked_hrs = Utility().seconds_to_hour_and_minute(worked_hrs)
                missed_emp_hrs = total_working_days - get_user_leaves
                if missed_emp_hrs<0:
                    missed_emp_hrs = 0
                required_wrk_hrs = missed_emp_hrs * 28800
                if required_wrk_hrs > 0:
                    is_below_required_wrk_hrs = 1
                else:
                    is_below_required_wrk_hrs = 0

                formatted_required_wrk_hrs = Utility().seconds_to_hour_and_minute(required_wrk_hrs)

                # if count_of_missing< 0:
                #     count_of_missing = 0
                # if int(missing_per)< 0:
                #     missing_per = 0
                timesheet_report_list = {
                'emp_id' : user,
                'user' : user_name,
                'submitted_cnt': 0,
                'approved_cnt': 0,
                'missing_cnt' : user_working_days,
                'submitted_per' : 0,
                'approved_per': 0,
                'missing_per': 100,
                'working_days' : total_working_days,
                'leave': get_user_leaves,
                'claimed_hrs': "00:00",
                'actual_work_hrs': formatted_worked_hrs,
                'required_hrs' : formatted_required_wrk_hrs,
                'is_below_required_wrk_hrs': is_below_required_wrk_hrs,
                'submitted_minutes': '0',
                'required_minutes': required_wrk_hrs,
                'actual_work_minutes': worked_hrs

                }
                report_list.append(timesheet_report_list)

            report_list = sorted(report_list, key = lambda i: (i['user']))
            return report_list
        except Exception as error:
            result["error"] = str(error)
            return [result]


    def __get_user_dict(self):
        user_dict = {}
        list_emp_ids = []
        users = UserDA().get_all_active_users()
        if users:
            for user in  users:
                user_dict[user.id] = f'{user.first_name} {user.last_name}'
                list_emp_ids.append(user.id)
        return user_dict, list_emp_ids


    def __get_employee_accessibility(self, emp_id, user_id):
        is_accessible = False
        if emp_id == user_id:
            is_accessible = True
        else:
            if UserDA().is_team_member(emp_id, user_id):
                is_accessible = True
        return is_accessible

    def get_time_sheet_detail_by_employee(self,emp_id, start_date, end_date, user_id):
        result = {"error": "", "success": ""}
        try:
            res_list = []
            date_dict = {}

            if not self.__get_employee_accessibility(emp_id, user_id):
                timesheet_list = [{"error": "No permission to view timesheet !!!"}]
                return timesheet_list

            obj_start = Utility().convert_string_to_date_time(start_date, "%Y-%m-%d")
            if not obj_start:
                return [{"error": "Invalid start date !!!"}]

            obj_end = Utility().convert_string_to_date_time(end_date, "%Y-%m-%d")
            if not obj_end:
                return [{"error": "Invalid end date !!!"}]

            if obj_start > obj_end:
                return [{"error": "Start date should be less than end date !!!"}]

            delta = obj_end - obj_start
            if delta.days > 90:
                return [{"error": "The date difference between dates should be less than 90 !!!"}]

            if obj_end > datetime.now():
                end_date = datetime.now().strftime("%Y-%m-%d")
                obj_end = datetime.now()

            employee_data = UserDA().get_user_by_id(emp_id)
            empcode = employee_data.username
            timesheet_list = TimeSheetDA().get_user_timesheet_summary(empcode, employee_data.id, start_date, end_date)
            if timesheet_list:
                for data in timesheet_list:
                    att_date = data['attendance_date'].strftime("%Y-%m-%d")
                    work_hour = data['work_hours'] if data['work_hours'] else 0
                    timesheet_hour = data['timesheet_hours'] if data['timesheet_hours'] else 0
                    timesheet_status = data['status'] if data['status'] else 'MISSING'

                    diffrence = abs(data['diffrence']) if data['diffrence']  else 0
                    res_dict = {
                        "date_status": "working",
                        "date_remark":"",
                        "date": att_date,
                        "work_hour": Utility().seconds_to_hour_and_minute(work_hour),
                        "timesheet_hour":Utility().seconds_to_hour_and_minute(timesheet_hour),
                        "diffrence":Utility().seconds_to_hour_and_minute(diffrence),
                        "timesheet_stauts": timesheet_status
                    }
                    date_dict[att_date] = res_dict
                    del res_dict

            start_date = datetime.strptime(start_date,'%Y-%m-%d')
            end_date = datetime.strptime(end_date,'%Y-%m-%d')

            date_list = self.__get_date_range(start_date, end_date)
            holiday_dict = self.__get_all_holidays(start_date, end_date)
            week_ends_list = self.__get_all_weekends(start_date, end_date)
            leave_list = self.__get_all_leaves(emp_id, start_date, end_date)

            for each_date in date_list:
                curr_date = Utility().convert_string_to_date_time(each_date, "%Y-%m-%d")
                if curr_date > datetime.now():
                    continue

                temp_dict = date_dict.get(each_date, None)
                if not temp_dict:
                    holiday = holiday_dict.get(each_date, None)
                    if holiday:
                        temp_dict = {
                            "date_status": "holiday",
                            "date_remark": holiday,
                            "date": each_date
                        }
                    else:
                        if each_date in week_ends_list:
                            temp_dict = {
                            "date_status": "weekend",
                            "date_remark": 'Weekly Off',
                            "date": each_date
                            }
                        elif each_date in leave_list:
                            temp_dict = {
                            "date_status": "leave",
                            "date_remark": 'Leave',
                            "date": each_date
                            }
                        else:
                            temp_dict = {
                            "date_status": "missing",
                            "date_remark": 'Missing',
                            "timesheet_stauts": "MISSING",
                            "date": each_date
                            }
                res_list.append(temp_dict)
                # res_list = sorted(res_list, \
                #     key = lambda i: (Utility().convert_string_to_date_time(i['date'], "%Y-%m-%d")))
                del temp_dict
            return res_list
        except Exception as error:
            result["error"] = str(error)
            return [result]


    def __get_activity_dict(self):
        activity_dict = {}
        activities = ProjectDA().get_all_project_activity()
        if activities:
            for activity in activities:
                activity_dict[activity.activity_id] = activity.name
        return activity_dict

    def __get_project_dict(self):
        project_dict = {}
        projects = ProjectDA().get_all_projects()
        if projects:
            for project in projects:
                project_dict[project.project_id] = project.name
        return project_dict

    def get_time_sheet_dpu(self,start_date, project_id, user_id, user_name):
        result = {"error": "", "success": ""}
        try:
            res_list = []
            module_dict = {}
            emp_ids = []
            user_dict = {}
            project_ids = []


            obj_start = Utility().convert_string_to_date_time(start_date, "%Y-%m-%d")
            if not obj_start:
                return [{"error": "Invalid date you have entered !!!"}]

            try:
                project_id = int(project_id)
            except:
                return [{"error": "Invalid project you have selected !!!"}]

            activity_dict = self.__get_activity_dict()
            project_dict = self.__get_project_dict()

            role_id, role_name = UserDA().get_user_role_by_id(user_id)

            if project_id:
                if ProjectDA().is_project_accessible(project_id, user_id):
                    project_ids.append(project_id)
                elif role_id in (1, 2, 3):
                    project_ids.append(project_id)
            else:
                if role_id in (1, 2, 3):
                    user_projects = ProjectDA().get_all_projects()
                    for project in user_projects:
                        project_ids.append(project.project_id)
                else:
                    user_projects = ProjectDA().get_project_user_mapping(user_id)
                    for project in user_projects:
                        project_ids.append(project.project_id)

            modules = ProjectDA().get_all_project_modules_by_project_ids(project_ids)
            for each_module in modules:
                module_dict[each_module.module_id] = each_module.name

            if role_id in (1, 2, 3):
                users = UserDA().get_current_team_members_by_lead_id(0)
            else:
                users = UserDA().get_current_team_members_by_lead_id(user_id)

            for user in users:
                emp_ids.append(user.id)
                user_dict[user.id] = user.first_name + " " + user.last_name

            emp_ids.append(user_id)
            user_dict[user_id] = user_name

            #role_id, role_name = UserDA().get_user_role_by_id(user_id)
            if role_id in (1, 2, 3):
                time_sheets = TimeSheetDA().get_all_daily_time_sheet(start_date)
            else:
                time_sheets = TimeSheetDA().get_daily_time_sheet_by_users(start_date, emp_ids)
            if time_sheets:
                for time_sheet in time_sheets:
                    user_name = user_dict.get(time_sheet.user_id)
                    str_timesheet_date = time_sheet.timesheet_date.strftime("%d-%m-%Y")
                    items = TimeSheetDA().get_time_sheet_items_by_timesheet_id(time_sheet.timesheet_id)
                    for each_item in items:
                        if each_item.project_id not in project_ids :
                            continue
                        comment = str(each_item.comment).replace(","," ").replace("\t"," ")
                        module = str(module_dict.get(each_item.module_id, '')).replace(","," ").replace("\t"," ")

                        res_dict = {
                            "project": project_dict.get(each_item.project_id, ''),
                            "module": module,
                            "activity": activity_dict.get(each_item.activity_id, ''),
                            "duration": Utility().seconds_to_hour_and_minute(each_item.duration),
                            "comment": comment,
                            "developer":user_name,
                            "billable": each_item.is_billable,
                            "timesheet_date":str_timesheet_date,
                            "percentage_completed": each_item.percentage_completed if each_item.percentage_completed else '-',
                            "status": each_item.status if each_item.status else '-' ,
                            "ticket_title": each_item.ticket_title if each_item.ticket_title else '-',
                            "ticket_eta": each_item.ticket_eta if each_item.ticket_eta else '-'
                        }
                        res_list.append(res_dict)
                        res_list = sorted(res_list, key = lambda i: (i['developer']))
                        del res_dict
                if not res_list:
                    res_list = [{"error": "No records to list !!!"}]

                return res_list
            else:
                return [{"error": "No time sheet found !!!"}]

        except Exception as error:
            return [{"error": str(error)}]


    def get_actual_wrk_hr_employee_dict(self, start_date_obj, end_date_obj):
        att_list = AttendanceDA().get_attendance_by_range(start_date_obj, end_date_obj)
        work_hr = {}
        emp_code_dict = self.emp_code_dict()
        for attendance in att_list:
            emp_id = emp_code_dict.get(attendance.emp_code, None)
            if emp_id:
                if emp_id in work_hr.keys():
                    work_hr[emp_id] = work_hr[emp_id] + attendance.work_hours
                else:
                    work_hr[emp_id] = attendance.work_hours
        return work_hr

    def emp_code_dict(self):
        emp_dict = {}
        employees = UserDA().get_all_users()
        for employee in employees:
            emp_dict[employee.username] = employee.id
        return emp_dict


    def holiday_count_excluding_week_days(self, start_date_obj, end_date_obj):
        holidays = HolidayDA().get_all_holidays(start_date_obj, end_date_obj)
        holiday_count_weekend_excluded =0
        for holiday in holidays:
            holiday_date = holiday.holiday_date
            if holiday_date.weekday() in (5, 6):
                continue
            else:
                holiday_count_weekend_excluded = holiday_count_weekend_excluded+1
        return holiday_count_weekend_excluded


    def get_team_timesheet_summary(self, user_id, start_date, end_date):

        all_employees = []
        missed_employees = []
        response = {
            'team_time_sheet_submit': "",
            'emp_time_sheet_submit': "0%",
            'error': None}

        exclude_emp_ids = [1,2,3,4,9,10,77]

        try:
            if user_id in exclude_emp_ids:
                response['emp_time_sheet_submit'] = 'N.A'

            user_dict, all_employees = self.__get_user_dict()
            total_dates = self.__get_date_range(start_date, end_date)
            number_of_days = len(total_dates)

            role_id, role_name = UserDA().get_user_role_by_id(user_id)
            if role_id in (1, 2, 3):
                emp_ids = all_employees
            elif role_id == 4:
                emp_ids = [user_id]
                all_employees = [user_id]
                team_member_list = UserDA().get_current_team_members_by_lead_id(user_id)
                for each_user in team_member_list:
                    emp_ids.append(each_user.id)
                    all_employees.append(each_user.id)
            else:
                emp_ids = [user_id]
                all_employees = [user_id]

            weekends_in_month = Utility().get_all_weekends(start_date, end_date)
            weekends = len(weekends_in_month)

            holiday_count_excluded_weekends = self.holiday_count_excluding_week_days(start_date, end_date)
            total_working_days = number_of_days - (weekends + holiday_count_excluded_weekends)
            timesheets = TimeSheetDA().get_all_time_sheets(start_date, end_date)

            submitted = {}
            users = []

            for sheet in timesheets:
                if sheet.user_id not in all_employees:
                    continue

                if emp_ids:
                    if sheet.user_id not in emp_ids:
                        continue

                if sheet.user_id in users:
                    if sheet.status == 'SUBMITTED' or sheet.status == 'APPROVED':
                        if sheet.user_id in submitted:
                            submitted[sheet.user_id].append(sheet)
                        else:
                            submitted[sheet.user_id] = [sheet]
                else:
                    if sheet.status == 'SUBMITTED' or sheet.status == 'APPROVED':
                        submitted[sheet.user_id] = [sheet]
                    users.append(sheet.user_id)

            missed_employees = set(all_employees) - set(users)
            missed_employees = set(missed_employees) - set(exclude_emp_ids)

            total_user_working_days = 0
            total_user_time_sheet_count = 0
            for user in users:
                get_user_leaves = int(self.__get_user_leaves(user, start_date, end_date))
                try:
                    count_of_submittd = len(submitted[user])
                except:
                    count_of_submittd = 0
                total_user_time_sheet_count+=count_of_submittd

                user_working_days = total_working_days - get_user_leaves
                if user_working_days < 0:
                    user_working_days = 0

                total_user_working_days+=user_working_days

                if user_id == user:
                    submitted_per = round(count_of_submittd / user_working_days * 100)
                    if submitted_per > 100:
                        submitted_per = 100
                    response['emp_time_sheet_submit'] = str(submitted_per) + "%"

            for user in missed_employees:
                get_user_leaves = int(self.__get_user_leaves(user, start_date, end_date))
                user_working_days = total_working_days - get_user_leaves
                if user_working_days < 0:
                    user_working_days = 0
                total_user_working_days+=user_working_days

            submitted_per = round(total_user_time_sheet_count / total_user_working_days * 100)
            if submitted_per > 100:
                submitted_per = 100
            response['team_time_sheet_submit'] = str(submitted_per) + "%"
            return response
        except Exception as err:
            # response["error"] = settings.ERROR_MSG['application_error']\
            #     .format(err, self.__log.error(self.__exception.get_exception()))
            #self.__log.error(self.__exception.get_exception())
            response["error"] = str(err)
            return response