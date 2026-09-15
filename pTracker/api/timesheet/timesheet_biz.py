from datetime import datetime

from django.conf import settings
from types import SimpleNamespace

from pTracker.common.utility import Utility
from pTracker.dataaccess.ptracker_access.timesheet_da import  TimeSheetDA
from pTracker.dataaccess.ptracker_access.project_da import  ProjectDA
from pTracker.dataaccess.ptracker_access.user_da import UserDA
from pTracker.dataaccess.ptracker_access.attendance import AttendanceDA


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
        actual_work_hours = None
        if user_timesheets:
            rejected_sheets = self.__get_rejected_sheets()

            for timesheet in user_timesheets:
                actual_work_hours = None
                hours = Utility().convert_seconds_to_hour_and_minute(timesheet.total_duration)
                comment = ''
                if timesheet.status == "REJECTED":
                    comment = rejected_sheets.get(timesheet.timesheet_id, '')
                emp_code = UserDA().get_user_by_id(timesheet.user_id).username
                actual_hours = AttendanceDA().get_attendance_by_emp_id_and_date(emp_code, timesheet.timesheet_date)
                if actual_hours:
                    actual_work_hours = actual_hours.work_hours
                timesheet_list.append({
                    "timesheet_id": timesheet.timesheet_id,
                    "status": timesheet.status,
                    "timesheet_date": timesheet.timesheet_date,
                    "user_id": timesheet.user_id,
                    "total_duration": timesheet.total_duration,
                    "total_hour": hours.split(":")[0],
                    "total_minute": hours.split(":")[1],
                    "comment": comment,
                    'actual_work_hours':actual_work_hours
                })
        return timesheet_list

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
            if not UserDA().is_team_member(user_id, lead_id):
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

    def create_or_update_time_sheet(self, data, user_id):
        result = {"error": "", "success": "", "status": 200}
        try:
            item_list = []
            is_update = False
            timesheet_id = data.get('timesheet_id', 0)
            

            dto = new_dto()
            dto.timesheet_date = data.get('timesheet_date', None)
            dto.user_id = user_id
            dto.status = data.get('status', None)
            line_items = data.get('items', [])
            dto.total_duration = 0

            front_end_user_id = data.get('user_id', 0)
            if front_end_user_id:
                if front_end_user_id != user_id:
                    result["error"] = "Indicators of potential malpractice have been detected. Please initiate a detailed review."
                    result['status'] = 499
                    return [result]

            if timesheet_id:
                is_update = True
                timesheet_obj = TimeSheetDA().get_time_sheet_by_id(timesheet_id, dto.user_id)
                if not timesheet_obj:
                    result["error"] = "Indicators of potential malpractice have been detected. Please initiate a detailed review."
                    result['status'] = 499
                    return [result]

            is_timesheet_exist = TimeSheetDA().is_timesheet_exist(dto.user_id, dto.timesheet_date, timesheet_id)
            if is_timesheet_exist:
                result["error"] = "Time sheet is already recorded for this date."
                result['status'] = 499
                return [result]

            action_dto = new_dto()
            action_dto.timesheet_id = timesheet_id
            action_dto.comment = ''
            if timesheet_id:
                action_dto.action = "EDITED"
            else:
                action_dto.action = "SUBMITTED"
            action_dto.performed_by = dto.user_id

            for item in line_items:
                item_dto = new_dto()
                item_dto.timesheet_id = timesheet_id
                item_dto.timesheet_date = dto.timesheet_date
                item_dto.user_id = dto.user_id
                item_dto.module_id = item.get("module_id", 0)
                item_dto.project_id = item.get("project_id", 0)
                item_dto.activity_id = item.get("activity_id", 0)
                item_dto.duration = item.get("duration", 0)
                item_dto.comment = item.get("comment", None)
                item_dto.is_billable = item.get("is_billable", 1)
                item_dto.percentage_completed = item.get("percentage_completed", '-')
                item_dto.status = item.get("status", '-')
                item_dto.ticket_title = item.get("ticket_title") if item.get("ticket_title") else '-'
                item_dto.ticket_eta = item.get("ticket_eta") if item.get("ticket_eta",'') else None
                try:
                    item_dto.percentage_completed = str(int(item_dto.percentage_completed))
                except:
                    item_dto.percentage_completed = '-'

                dto.total_duration += item_dto.duration
                item_list.append(item_dto)
                del item_dto

            if dto.total_duration > 86399:
                result["error"] = "Total time duration should be less than 24 hours."
                result['status'] = 499
                return [result]


            try:
                if timesheet_id:
                    dto.timesheet_id = timesheet_id
                    TimeSheetDA().update_time_sheet(dto)
                else:
                    timesheet_id = TimeSheetDA().create_time_sheet(dto)

                if is_update:
                    TimeSheetDA().delete_time_sheet_items(timesheet_id)
                for each_item in item_list:
                    each_item.timesheet_id = timesheet_id
                    timesheet_item_id = TimeSheetDA().create_time_sheet_items(each_item)
                action_dto.timesheet_id = timesheet_id
                action_id = TimeSheetDA().create_time_sheet_action_log(action_dto)

                msg = "Time sheet created sucessfully."
                if is_update:
                    msg = "Time sheet updated sucessfully."
                result["success"] = msg
                return [result]
            except Exception as err:
                TimeSheetDA().roll_back_time_sheet_entry(timesheet_id)
                result["error"] = str(err)
                result['status'] = 499
                return [result]
        except Exception as err:
            result["error"] = str(err)
            result['status'] = 499
            return [result]


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
        is_exist = TimeSheetDA().is_timesheet_exist(user_id, str_date, time_sheet_id)
        obj_date = Utility().convert_string_to_date_time(str_date, "%Y-%m-%d")
        min_date = Utility().convert_string_to_date_time("2019-12-31", "%Y-%m-%d")
        work_hour = '00:00'
        if obj_date > datetime.today():
            return {"is_valid": False, "msg": "Sorry ! Future date not permitted.", "status": 499}
        elif obj_date <= min_date:
            return {"is_valid": False, "msg": "Sorry ! Select a date after 31/12/2019", "status": 499}
        elif is_exist:
            return {"is_valid": False, "msg": "Time sheet is already recorded for this date.",  "status": 200}
        else:
            user = UserDA().get_user_by_id(user_id)
            attendance = AttendanceDA().get_attendance_by_emp_id_and_date(start_date=obj_date.date(),\
                 emp_id=user.username)
            if attendance:
                work_hour = attendance.work_hours
            return {"is_valid": True, "msg": "", 'work_hour':work_hour,  "status": 200}



    def approve_time_sheet(self, data, user_id):
        result = {"error": "", "success": "", "status": 200}
        try:
            timesheet_id = data.get('timesheet_id', 0)
            dto = new_dto()
            dto.timesheet_id = timesheet_id
            dto.status = data.get('status', None)
            action_dto = new_dto()
            action_dto.timesheet_id = dto.timesheet_id
            action_dto.comment = data.get('comment', '')
            action_dto.action = dto.status
            action_dto.performed_by = user_id
            if timesheet_id:
                obj_sheet = TimeSheetDA().get_time_sheet_by_timesheet_id(timesheet_id)
                if not obj_sheet:
                    result["error"] = "Invalid time sheet id."
                    result['status'] = 499
                    return [result]
                emp_id = obj_sheet.user_id
                if not UserDA().is_team_member(emp_id, user_id):
                    result["error"] = "You have no permission to review this time sheet"
                    result['status'] = 403
                    return [result]

                TimeSheetDA().approve_time_sheet(dto)
                TimeSheetDA().create_time_sheet_action_log(action_dto)

            msg = "Time sheet approved sucessfully."
            if dto.status == "REJECTED":
                msg = "Time sheet rejected sucessfully."
            result["success"] = msg
            return [result]

        except Exception as err:
            result['status'] = 499
            result["error"] = str(err)
            return [result]


    def get_employee_time_sheet_detail_by_id(self, time_sheet_id, emp_id, user_id):
        if not UserDA().is_team_member(emp_id, user_id):
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
        work_hours = "0:00"
        emp = UserDA().get_user_by_id(emp_id)
        res = AttendanceDA().get_attendance_by_emp_id_and_date(emp.username, work_date)
        if res:
            work_hours = Utility().convert_seconds_to_hour_and_minute(res.work_hours)
        return work_hours
    
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
    




