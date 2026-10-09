from datetime import date, datetime

from django.conf import settings
from django.db import transaction
from types import SimpleNamespace

from pTracker.common.utility import Utility
from pTracker.common.company_authorization import oversees_employee, has_capability
from pTracker.common.company_context import get_active_company_id
from pTracker.common.exception_handler import ExceptionHandler
from pTracker.common.logs import Logs
from pTracker.dataaccess.attendance_v2_access.org_da import OrgDA
from pTracker.dataaccess.attendance_v2_access.daily_da import DailyDA
from pTracker.dataaccess.ptracker_access.timesheet_da import  TimeSheetDA
from pTracker.dataaccess.ptracker_access.project_da import  ProjectDA
from pTracker.dataaccess.ptracker_access.user_da import UserDA


def new_dto():
    dto = SimpleNamespace()
    return dto


class TimeSheetBL():


    def __get_total_duration(self, line_items):
        duration = 0
        for item in line_items:
            temp = item.get("duration", 0)
            duration += temp
        return duration

    def __get_rejected_sheets(self):
        actions = TimeSheetDA().get_all_rejected_time_sheets()
        action_dict = {}
        if actions:
            for action in actions:
                action_dict[action.timesheet_id] = action.comment
        return action_dict


    def __generate_time_sheet_dict(self, user_timesheets):
        timesheet_list = []
        user_timesheets = list(user_timesheets or [])
        if user_timesheets:
            rejected_sheets = self.__get_rejected_sheets()
            worked_seconds = self.__get_worked_seconds(
                {t.user_id for t in user_timesheets},
                min(t.timesheet_date for t in user_timesheets),
                max(t.timesheet_date for t in user_timesheets))

            for timesheet in user_timesheets:
                hours = Utility().convert_seconds_to_hour_and_minute(timesheet.total_duration)
                comment = ''
                if timesheet.status == "REJECTED":
                    comment = rejected_sheets.get(timesheet.timesheet_id, '')
                timesheet_list.append({
                    "timesheet_id": timesheet.timesheet_id,
                    "status": timesheet.status,
                    "timesheet_date": timesheet.timesheet_date,
                    "user_id": timesheet.user_id,
                    "total_duration": timesheet.total_duration,
                    "total_hour": hours.split(":")[0],
                    "total_minute": hours.split(":")[1],
                    "comment": comment,
                    'actual_work_hours': worked_seconds.get((timesheet.user_id, timesheet.timesheet_date))
                })
        return timesheet_list

    def __get_worked_seconds(self, user_ids, start_date, end_date):
        """ {(user_id, date): seconds worked} from Attendance V2 in the active
        company; days without an attendance record are missing. """
        company_id = get_active_company_id()
        if company_id is None:
            return {}
        minutes = DailyDA().get_worked_minutes(company_id, user_ids, start_date, end_date)
        return {key: value * 60 for key, value in minutes.items()}

    def get_all_time_sheet_by_user(self, user_id):
        user_timesheets = TimeSheetDA().get_all_time_sheet_by_user(user_id)
        timesheet_list = self.__generate_time_sheet_dict(user_timesheets)
        if not timesheet_list:
            timesheet_list = [{"error": "No time sheet entry found !!!", "status": 499}]
        return timesheet_list

    def get_time_sheets_by_date_range(self, user_id, start_date, end_date, status=0, lead_id=0):
        timesheet_list = []
        try:
            status = int(status)
        except:
            status = 0
        if status == 1:
            status = "SUBMITTED"
        elif status == 2:
            status = "APPROVED"
        elif status == 3:
            status = "REJECTED"
        else:
            status = 0

        if lead_id:
            if not oversees_employee(lead_id, user_id, module='timesheet'):
                timesheet_list = [{"error": "No permission to view timesheets !!!", "status": 403}]
                return timesheet_list

        obj_start = Utility().convert_string_to_date_time(start_date, "%Y-%m-%d")
        if not obj_start:
            timesheet_list = [{"error": "Invalid start date !!!", "status": 499}]

        obj_end = Utility().convert_string_to_date_time(start_date, "%Y-%m-%d")
        if not obj_end:
            timesheet_list = [{"error": "Invalid end date !!!", "status": 499}]

        if obj_start > obj_end:
            timesheet_list = [{"error": "Start date should be less than end date !!!","status": 499}]

        if timesheet_list:
            return timesheet_list

        user_timesheets = TimeSheetDA().get_all_time_sheet_by_user(user_id)
        if user_timesheets:
            user_timesheets = user_timesheets.filter(timesheet_date__gte=start_date, timesheet_date__lte=end_date)
            if status:
                user_timesheets = user_timesheets.filter(status=status)
            timesheet_list = self.__generate_time_sheet_dict(user_timesheets)
        if not timesheet_list:
            timesheet_list = [{"error": "No time sheet entry found !!!", "status": 499}]
        return timesheet_list

    TIMESHEET_MIN_DATE = date(2020, 1, 1)
    MAX_TIMESHEET_DURATION = 86399  # seconds, just under 24 hours
    MALPRACTICE_MSG = "Indicators of potential malpractice have been detected. Please initiate a detailed review."

    def create_or_update_time_sheet(self, data, user_id):
        """ Saves the caller's own timesheet. A saved timesheet is always
        SUBMITTED (approval only happens through verify-timesheet/), an
        APPROVED one can no longer be edited, and every item must use a
        project/module/activity the caller can pick in the active company. """
        result = {"error": "", "success": "", "status": 200}
        try:
            front_end_user_id = data.get('user_id', 0)
            if front_end_user_id and front_end_user_id != user_id:
                result["error"] = self.MALPRACTICE_MSG
                result['status'] = 499
                return [result]

            try:
                timesheet_id = int(data.get('timesheet_id') or 0)
            except (TypeError, ValueError):
                timesheet_id = -1
            if timesheet_id < 0:
                result["error"] = "Invalid time sheet id."
                result['status'] = 400
                return [result]

            error, timesheet_date, item_list = self.__validate_time_sheet(data, user_id)
            if error:
                result["error"] = error
                result['status'] = 400
                return [result]

            if timesheet_id:
                timesheet_obj = TimeSheetDA().get_time_sheet_by_id(timesheet_id, user_id)
                if not timesheet_obj:
                    result["error"] = self.MALPRACTICE_MSG
                    result['status'] = 499
                    return [result]
                if timesheet_obj.status == "APPROVED":
                    result["error"] = "An approved time sheet can't be edited."
                    result['status'] = 400
                    return [result]

            if TimeSheetDA().is_timesheet_exist(user_id, timesheet_date, timesheet_id):
                result["error"] = "Time sheet is already recorded for this date."
                result['status'] = 499
                return [result]

            dto = new_dto()
            dto.timesheet_date = timesheet_date
            dto.user_id = user_id
            dto.status = "SUBMITTED"
            dto.total_duration = sum(item.duration for item in item_list)

            action_dto = new_dto()
            action_dto.comment = ''
            action_dto.action = "EDITED" if timesheet_id else "SUBMITTED"
            action_dto.performed_by = user_id

            with transaction.atomic():
                if timesheet_id:
                    dto.timesheet_id = timesheet_id
                    TimeSheetDA().update_time_sheet(dto)
                    TimeSheetDA().delete_time_sheet_items(timesheet_id)
                else:
                    timesheet_id = TimeSheetDA().create_time_sheet(dto)
                for each_item in item_list:
                    each_item.timesheet_id = timesheet_id
                    TimeSheetDA().create_time_sheet_items(each_item)
                action_dto.timesheet_id = timesheet_id
                TimeSheetDA().create_time_sheet_action_log(action_dto)

            result["success"] = "Time sheet updated sucessfully." if action_dto.action == "EDITED" \
                else "Time sheet created sucessfully."
            return [result]
        except Exception:
            log_id = Logs().error(ExceptionHandler().get_exception())
            result["error"] = f"Time sheet could not be saved. LogID: {log_id}"
            result['status'] = 499
            return [result]

    def __validate_time_sheet(self, data, user_id):
        """ Returns (error, timesheet_date, item dtos); error is None when valid. """
        try:
            timesheet_date = datetime.strptime(str(data.get('timesheet_date') or ''), "%Y-%m-%d").date()
        except ValueError:
            return "timesheet_date must be a date (YYYY-MM-DD).", None, None
        if timesheet_date > date.today():
            return "Sorry ! Future date not permitted.", None, None
        if timesheet_date < self.TIMESHEET_MIN_DATE:
            return "Sorry ! Select a date after 31/12/2019", None, None

        line_items = data.get('items')
        if not isinstance(line_items, list) or not line_items:
            return "Add at least one time sheet entry.", None, None

        item_list = []
        for item in line_items:
            if not isinstance(item, dict):
                return "Invalid time sheet entry.", None, None
            item_dto = new_dto()
            item_dto.timesheet_date = timesheet_date
            item_dto.user_id = user_id
            try:
                item_dto.project_id = int(item.get("project_id") or 0)
                item_dto.module_id = int(item.get("module_id") or 0)
                item_dto.activity_id = int(item.get("activity_id") or 0)
                item_dto.duration = int(item.get("duration"))
                item_dto.is_billable = int(item.get("is_billable", 1))
            except (TypeError, ValueError):
                return "project_id, module_id, activity_id, duration and is_billable must be numbers.", None, None
            if item_dto.duration <= 0:
                return "Each entry's duration must be more than zero.", None, None

            item_dto.comment = str(item.get("comment") or '')
            item_dto.status = str(item.get("status") or '-')
            item_dto.ticket_title = str(item.get("ticket_title") or '-')
            if len(item_dto.comment) > 5000 or len(item_dto.status) > 20 or len(item_dto.ticket_title) > 255:
                return "comment, status or ticket_title is too long.", None, None
            try:
                percentage = int(item.get("percentage_completed"))
                item_dto.percentage_completed = str(percentage) if 0 <= percentage <= 100 else '-'
            except (TypeError, ValueError):
                item_dto.percentage_completed = '-'
            ticket_eta = item.get("ticket_eta")
            try:
                item_dto.ticket_eta = datetime.strptime(str(ticket_eta), "%Y-%m-%d").date() if ticket_eta else None
            except ValueError:
                return "ticket_eta must be a date (YYYY-MM-DD).", None, None
            item_list.append(item_dto)

        if sum(item.duration for item in item_list) > self.MAX_TIMESHEET_DURATION:
            return "Total time duration should be less than 24 hours.", None, None

        error = self.__validate_time_sheet_projects(item_list, user_id)
        return error, timesheet_date, item_list

    def __validate_time_sheet_projects(self, item_list, user_id):
        """ The same choices the project/module/activity drop-downs offer:
        active projects of the active company (only assigned ones without
        project.view_all), active modules of that project, active activities
        of the company. A module is optional. """
        company_id = get_active_company_id()
        project_da = ProjectDA()
        projects = project_da.get_active_project_ids_in_company(company_id, {item.project_id for item in item_list})
        if not has_capability(user_id, 'project.view_all'):
            projects &= set(project_da.get_all_project_ids_of_user(user_id))
        module_projects = project_da.get_active_module_projects({item.module_id for item in item_list if item.module_id})
        activities = project_da.get_active_activity_ids_in_company(company_id, {item.activity_id for item in item_list})

        for item in item_list:
            if item.project_id not in projects:
                return "You can't log time to this project."
            if item.module_id and module_projects.get(item.module_id) != item.project_id:
                return "The selected module doesn't belong to the project."
            if item.activity_id not in activities:
                return "Select a valid activity."
        return None

    def get_all_project_dict(self):
        project_dict = {}
        projects = ProjectDA().get_all_projects()
        if projects:
            for project in projects:
                project_dict[project.project_id] = project.name
        return project_dict

    def get_all_project_activity_dict(self):
        res_dict = {}
        activities = ProjectDA().get_all_project_activity()
        if activities:
            for activity in activities:
                res_dict[activity.activity_id] = activity.name
        return res_dict

    def get_all_project_module_dict(self):
        res_dict = {}
        modules = ProjectDA().get_all_project_modules()
        if modules:
            for module in modules:
                res_dict[module.module_id] = module.name
        return res_dict


    def get_time_sheet_detail_by_id(self, time_sheet_id, user_id):
        timesheet_dict = {"status_code": 200}
        item_list = []

        project_dict = self.get_all_project_dict()
        activity_dict = self.get_all_project_activity_dict()
        module_dict = self.get_all_project_module_dict()

        time_sheet = TimeSheetDA().get_time_sheet_by_id(time_sheet_id, user_id)
        if time_sheet:
            items = TimeSheetDA().get_time_sheet_items_by_timesheet_id(time_sheet_id)
            working_hours = self.get_work_hours_by_date(time_sheet.timesheet_date, time_sheet.user_id)
            if items:
                for item in items:
                    hours = Utility().convert_seconds_to_hour_and_minute(item.duration)
                    item_list.append({
                        "module_id": item.module_id,
                        "module_name": module_dict.get(item.module_id, ""),
                        "project_id": item.project_id,
                        "project_name": project_dict.get(item.project_id, "") ,
                        "activity_id": item.activity_id,
                        "activity_name": activity_dict.get(item.activity_id, "") ,
                        "duration": item.duration,
                        "hour": hours.split(":")[0],
                        "minute": hours.split(":")[1],
                        "comment": item.comment,
                        "is_billable": item.is_billable,
                        "percentage_completed": item.percentage_completed if item.percentage_completed else '-',
                        "status": item.status if item.status else '-',
                        "ticket_title": item.ticket_title if item.ticket_title else '-',
                        "ticket_eta": item.ticket_eta if item.ticket_eta else '-'
                        })
            timesheet_dict['timesheet_id'] = time_sheet.timesheet_id
            timesheet_dict['status'] = time_sheet.status
            timesheet_dict['timesheet_date'] = time_sheet.timesheet_date
            timesheet_dict['user_id'] = time_sheet.user_id
            timesheet_dict['total_duration'] = Utility().convert_seconds_to_hour_and_minute(time_sheet.total_duration)
            timesheet_dict['work_hours'] = working_hours
            timesheet_dict['items'] = item_list

        if not timesheet_dict:
            timesheet_dict['error']  = "No record found !!"
            timesheet_dict['status_code'] = 499
        return timesheet_dict

    def is_timesheet_date_valid(self, user_id, str_date, time_sheet_id=0):
        """ Can the caller log a timesheet on str_date? When editing, pass the
        timesheet's id so it doesn't count as the existing one (only the
        caller's own timesheet is excluded). work_hour is the day's worked time
        from Attendance V2 in seconds, or "00:00" when there is no record. """
        obj_date = Utility().convert_string_to_date_time(str_date, "%Y-%m-%d")
        if obj_date is None:
            return {"is_valid": False, "msg": "Invalid date, use YYYY-MM-DD.", "status": 400}
        if obj_date.date() > date.today():
            return {"is_valid": False, "msg": "Sorry ! Future date not permitted.", "status": 499}
        if obj_date.date() < self.TIMESHEET_MIN_DATE:
            return {"is_valid": False, "msg": "Sorry ! Select a date after 31/12/2019", "status": 499}

        if time_sheet_id and not TimeSheetDA().get_time_sheet_by_id(time_sheet_id, user_id):
            time_sheet_id = 0
        if TimeSheetDA().is_timesheet_exist(user_id, obj_date.date(), time_sheet_id):
            return {"is_valid": False, "msg": "Time sheet is already recorded for this date.",  "status": 200}

        work_hour = self.__get_worked_seconds({user_id}, obj_date.date(), obj_date.date()).get(
            (user_id, obj_date.date()), '00:00')
        return {"is_valid": True, "msg": "", 'work_hour': work_hour,  "status": 200}

    REVIEW_ACTIONS = ('APPROVED', 'REJECTED')

    def approve_time_sheet(self, data, user_id):
        """ Approve or reject a SUBMITTED timesheet. A decision is final: an
        APPROVED timesheet never changes again, a REJECTED one only goes back
        to SUBMITTED when its owner edits it. Rejecting needs a comment. """
        result = {"error": "", "success": "", "status": 200}
        try:
            try:
                timesheet_id = int(data.get('timesheet_id') or 0)
            except (TypeError, ValueError):
                timesheet_id = 0
            if timesheet_id <= 0:
                result["error"] = "timesheet_id is required."
                result['status'] = 400
                return [result]
            action = str(data.get('status') or '').strip().upper()
            if action not in self.REVIEW_ACTIONS:
                result["error"] = "action must be APPROVED or REJECTED."
                result['status'] = 400
                return [result]
            comment = str(data.get('comment') or '').strip()
            if action == "REJECTED" and not comment:
                result["error"] = "A comment is required to reject a time sheet."
                result['status'] = 400
                return [result]

            obj_sheet = TimeSheetDA().get_time_sheet_by_timesheet_id(timesheet_id)
            if not obj_sheet:
                result["error"] = "Invalid time sheet id."
                result['status'] = 499
                return [result]
            if not self.__can_review_time_sheet(user_id, obj_sheet.user_id, action):
                result["error"] = "You have no permission to review this time sheet"
                result['status'] = 403
                return [result]
            if obj_sheet.status != "SUBMITTED":
                result["error"] = f"This time sheet is already {str(obj_sheet.status).lower()} and can't be reviewed again."
                result['status'] = 400
                return [result]

            dto = new_dto()
            dto.timesheet_id = timesheet_id
            dto.status = action
            action_dto = new_dto()
            action_dto.timesheet_id = timesheet_id
            action_dto.comment = comment
            action_dto.action = action
            action_dto.performed_by = user_id
            with transaction.atomic():
                TimeSheetDA().approve_time_sheet(dto)
                TimeSheetDA().create_time_sheet_action_log(action_dto)

            result["success"] = "Time sheet rejected sucessfully." if action == "REJECTED" \
                else "Time sheet approved sucessfully."
            return [result]

        except Exception:
            log_id = Logs().error(ExceptionHandler().get_exception())
            result["error"] = f"Time sheet could not be reviewed. LogID: {log_id}"
            result['status'] = 499
            return [result]

    def __can_review_time_sheet(self, user_id, emp_id, action):
        """ Reviewers act only on active members of the active company: the
        employee's mapped lead or a timesheet.approve holder. Your own
        timesheet only when you hold timesheet.approve, have no reporting lead
        to send it to, and are approving it. """
        company_id = get_active_company_id()
        if company_id is None or not OrgDA().is_company_member(company_id, emp_id):
            return False
        if emp_id == user_id:
            return (action == "APPROVED"
                    and has_capability(user_id, 'timesheet.approve')
                    and not UserDA().get_lead_id_by_user(user_id))
        return oversees_employee(user_id, emp_id, capability='timesheet.approve')

    def get_employee_time_sheet_detail_by_id(self, time_sheet_id, emp_id, user_id):
        if not oversees_employee(user_id, emp_id, module='timesheet'):
            result = {}
            result["error"] = "You have no permission to review this time sheet."
            return result
        return self.get_time_sheet_detail_by_id(time_sheet_id, emp_id)












    def insert_user(self):
        import csv, sys, os, django


        #project_dir = "/parcare/src/"
        #sys.path.append(project_dir)
        #os.environ['DJANGO_SETTINGS_MODULE'] = 'adp_parking.settings'
        # os.environ.setdefault("DJANGO_SETTINGS_MODULE", __file__)
        #import django
        #django.setup()


        from django.contrib.auth import authenticate
        from django.contrib import admin
        from django.contrib.auth.models import User

        from django.contrib.auth import get_user_model
        from django.conf import settings
        User = get_user_model()

        file = '/home/subish/Desktop/To_Megalrag/toDajngo.csv'

        data = csv.reader(open(file), delimiter=",")
        i =0
        for row in data:
            if i==0:
                i=i+1
                continue
            # Post.id = row[0]

            user = User.objects.create_user(row[3], row[6], row[0])

            # Post=User()
            # Post.password = row[0]
            user.last_login = None
            user.is_superuser = 0
            # Post.username = row[3]
            user.first_name = row[4]
            user.last_name=row[5]
            # Post.email = row[6]
            user.is_staff = 0
            user.is_active = 1
            # print ('str(row[9])', str(row[9]))
            user.date_joined = str(row[9])
            #User.objects.create_user
            user.save()

    def get_work_hours_by_date(self, work_date, emp_id):
        """ "HH:MM" worked on work_date per Attendance V2, "0:00" without a record. """
        seconds = self.__get_worked_seconds({emp_id}, work_date, work_date).get((emp_id, work_date))
        if seconds is None:
            return "0:00"
        return Utility().convert_seconds_to_hour_and_minute(seconds)

    def get_timesheets_by_date_range(self, from_date, to_date):
        return TimeSheetDA().get_timesheets_by_date_range(from_date, to_date)
    
    def get_all_timesheet_log(self):
        return TimeSheetDA().get_all_timesheet_log()
    
    def get_timesheet_items_by_date_range(self, from_date, to_date):
        return TimeSheetDA().get_timesheet_item_by_date_range(from_date, to_date)

    def bulk_create_timesheet_archive_and_log_archive(self, timesheets, log_dict):
        timesheet_ids = TimeSheetDA().bulk_create_timesheet_archive_and_log_archive(timesheets,log_dict)
        return timesheet_ids
    
    def bulk_create_timesheet_items_archive(self, timesheet_items):
        TimeSheetDA().bulk_create_timesheet_items_archive(timesheet_items)
    
    def delete_timesheets_by_date_range(self, from_date, to_date):
        TimeSheetDA().delete_timesheets_by_date_range(from_date, to_date)
    
    def delete_timesheet_items_by_date_range(self, from_date, to_date):
        TimeSheetDA().delete_timesheets_items_by_date_range(from_date, to_date)
    
    def delete_timesheet_log_by_timesheet_ids(self, timesheet_ids):
        TimeSheetDA().delete_timesheet_log_by_timesheet_ids(timesheet_ids)
    
    def create_timesheet_archive_log(self,start_date ,end_date,user_id ):
        data = {}
        data['archive_from'] = datetime.strptime(start_date,"%Y-%m-%d")
        data['archive_to'] = datetime.strptime(end_date,"%Y-%m-%d")
        data['archive_date'] = datetime.now()
        data['user_id'] = user_id
        obj = TimeSheetDA().create_timesheet_archive_log(data)
        return obj
    
    def get_archived_timesheets_by_date_range(self, start_date, end_date):
        return TimeSheetDA().get_archived_timesheets_by_date_range(start_date, end_date)

    def get_all_archived_timesheet_log(self):
        return TimeSheetDA().get_all_archived_timesheet_log()
    
    def get_archived_timesheet_items_by_date_range(self, start_date,end_date):
        return TimeSheetDA().get_archived_timesheet_items_by_date_range(start_date, end_date)
    
    def bulk_create_timesheet_from_archive_and_log_archive(self,timesheets,log_dict):
        timesheet_ids = TimeSheetDA().bulk_create_timesheet_from_archive_and_log_archive(timesheets,log_dict)
        return timesheet_ids
    
    def bulk_create_timesheet_items_from_archive(self,timesheet_items):
        TimeSheetDA().bulk_create_timesheet_items_from_archive(timesheet_items)
    
    def delete_timesheets_archive_by_date_range(self, start_date, end_date):
        TimeSheetDA().delete_timesheets_archive_by_date_range(start_date, end_date)
    
    def delete_timesheet_items_archives_by_date_range(self,start_date,end_date ):
        TimeSheetDA().delete_timesheets_items_archives_by_date_range(start_date, end_date)
    
    def delete_timesheet_log_archive_by_timesheet_ids(self, timesheet_ids):
        TimeSheetDA().delete_timesheet_log_archive_by_timesheet_ids(timesheet_ids)
    
    def delete_timesheet_archive_log(self, archive_id):
        TimeSheetDA().delete_timesheet_archive_log(archive_id)
    




