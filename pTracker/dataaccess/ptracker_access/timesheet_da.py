
from datetime import datetime
from types import SimpleNamespace

from django.conf import settings
from django.db import connection

from pTracker.dataaccess.ptracker_access.time_sheet_models import TimeSheet, TimeSheetArchive, TimeSheetItemArchive
from pTracker.dataaccess.ptracker_access.time_sheet_models import TimeSheetActionLog
from pTracker.dataaccess.ptracker_access.time_sheet_models import TimeSheetItem

from pTracker.dataaccess.ptracker_access.time_sheet_models import TimeSheetActionLogArchive
from pTracker.dataaccess.ptracker_access.time_sheet_models import TimeSheetArchiveLog
from pTracker.dataaccess.ptracker_access.user_models import TimesheetExcludedEmployees
from pTracker.dataaccess.db import Connection
from pTracker.common.utility import Utility

def new_dto():
    dto = SimpleNamespace()
    return dto


class TimeSheetDA():

    def __init__(self):
        pass

    def roll_back_time_sheet_entry(self, timesheet_id):
        self.delete_time_sheet_items(timesheet_id)
        self.clear_time_sheet_action_log(timesheet_id)
        time_sheet = TimeSheet.objects.filter(timesheet_id=timesheet_id)
        if time_sheet:
            time_sheet.delete()

    def get_all_time_sheet_by_user(self, user_id):
        objs = TimeSheet.objects.filter(user_id=user_id).order_by("timesheet_date")
        return objs

    def get_time_sheet_by_id(self, timesheet_id, user_id =0):
        if user_id:
            objs = TimeSheet.objects.filter(timesheet_id=timesheet_id, user_id=user_id)
            if objs:
                objs = objs[0]
        else:
            objs = TimeSheet.objects.filter(timesheet_id=timesheet_id)
            if objs:
                objs = objs[0]
        return objs

    def get_time_sheet_by_timesheet_id(self, timesheet_id):
        objs = TimeSheet.objects.filter(timesheet_id=timesheet_id)
        if objs:
            objs = objs[0]
        return objs

    def is_timesheet_exist(self, user_id, str_date, timesheet_id=0):
        if not timesheet_id:
            objs = TimeSheet.objects.filter(timesheet_date=str_date, user_id=user_id)
        else:
            objs = TimeSheet.objects.filter(timesheet_date=str_date, user_id=user_id).exclude(timesheet_id=timesheet_id)

        if objs:
            return True
        else:
            return False

    def get_time_sheet_items_by_timesheet_id(self, timesheet_id):
        items = TimeSheetItem.objects.filter(timesheet_id=timesheet_id)
        return items

    def create_time_sheet(self, dto):
        obj = TimeSheet(
            status=dto.status,
            timesheet_date=dto.timesheet_date,
            user_id=dto.user_id,
            total_duration=dto.total_duration)
        obj.save()
        timesheet_id = obj.timesheet_id
        return timesheet_id

    def update_time_sheet(self, dto):
        obj = TimeSheet.objects.filter(timesheet_id=dto.timesheet_id)\
            .update(status=dto.status,
                    timesheet_date=dto.timesheet_date,
                    user_id=dto.user_id,
                    total_duration=dto.total_duration)
        return dto.timesheet_id

    def approve_time_sheet(self, dto):
        TimeSheet.objects.filter(timesheet_id=dto.timesheet_id)\
            .update(status=dto.status)
        return dto.timesheet_id

    def delete_time_sheet_items(self, timesheet_id):
        items = TimeSheetItem.objects.filter(timesheet_id=timesheet_id)
        if items:
            items.delete()

    def create_time_sheet_items(self, dto):
        obj = TimeSheetItem(
            timesheet_id=dto.timesheet_id,
            timesheet_date=dto.timesheet_date,
            user_id=dto.user_id,
            module_id=dto.module_id,
            project_id=dto.project_id,
            activity_id=dto.activity_id,
            duration=dto.duration,
            comment=dto.comment,
            is_billable=dto.is_billable,
            percentage_completed=dto.percentage_completed,
            status=dto.status,
            ticket_title=dto.ticket_title,
            ticket_eta=dto.ticket_eta)

        obj.save()
        timesheet_item_id = obj.timesheet_item_id
        return timesheet_item_id

    def create_time_sheet_action_log(self, dto):
        obj = TimeSheetActionLog(
            timesheet_id=dto.timesheet_id,
            comment=dto.comment,
            action=dto.action,
            performed_by=dto.performed_by,
            action_date=datetime.now())
        obj.save()
        action_id = obj.action_id
        return action_id

    def clear_time_sheet_action_log(self, timesheet_id):
        actions = TimeSheetActionLog.objects.filter(timesheet_id=timesheet_id)
        if actions:
            actions.delete()

    def get_all_rejected_time_sheets(self):
        actions = TimeSheetActionLog.objects.filter(action="REJECTED").order_by('action_id')
        return actions

    def get_all_time_sheets(self,start_date,end_date):
        objs = TimeSheet.objects.filter(timesheet_date__gte=start_date,timesheet_date__lte=end_date)
        return objs

    def get_user_timesheet_summary(self, emp_code, user_id, str_date, end_date):
        str_sql = """SELECT da.emp_code,da.attendance_date,da.work_hours,
                    t2.total_duration timesheet_hours,
                    (da.work_hours-t2.total_duration)diffrence,
                    t2.status,t2.timesheet_date,t2.timesheet_id
                    FROM daily_attendance da
                    LEFT JOIN timesheet t2
                    ON da.attendance_date=t2.timesheet_date AND t2.user_id = {1}
                    WHERE da.attendance_date >='{2}'
                    AND da.attendance_date <= '{3}'
                    AND da.emp_code ={0} ORDER BY da.attendance_date""".format(emp_code, user_id, str_date, end_date)
        with connection.cursor() as cursor:
               cursor.execute(str_sql)
               columns = [column[0] for column in cursor.description]
               result_list = []
               for row in cursor.fetchall():
                  result_list.append(dict(zip(columns, row)))
        if not result_list:
            result_list = None
        return result_list

    def get_daily_time_sheet_by_users(self,start_date, user_ids=[]):
        return TimeSheet.objects.filter(timesheet_date=start_date,user_id__in=user_ids)

    def get_all_daily_time_sheet(self,start_date):
        return TimeSheet.objects.filter(timesheet_date=start_date)

    def create_timesheet_archive(self,user_id):
        data_list = []
        log_data_list = []
        log_ids = []
        timesheet_objects = TimeSheet.objects.filter(user_id=user_id)
        timesheet_log = TimeSheetActionLog.objects.all()
        for each in timesheet_objects:
            data_list.append(TimeSheetArchive(timesheet_id = each.timesheet_id,
            status = each.status,
            timesheet_date = each.timesheet_date,
            user_id = each.user_id,
            total_duration = each.total_duration,
            created_date = each.created_date
            ))

            log= timesheet_log.filter(timesheet_id = each.timesheet_id)
            for each_log in log:
                log_ids.append(each_log.action_id)
                log_data_list.append(TimeSheetActionLogArchive(action_id = each_log.action_id,
                timesheet_id = each_log.timesheet_id,
                comment = each_log.comment,
                action = each_log.action,
                action_date = each_log.action_date,
                performed_by = each_log.performed_by
                ))
        TimeSheetActionLogArchive.objects.bulk_create(log_data_list)
        TimeSheetArchive.objects.bulk_create(data_list)
        TimeSheet.objects.filter(user_id=user_id).delete()
        TimeSheetActionLog.objects.filter(action_id__in =log_ids).delete()

    def create_timesheet_item_archive(self,user_id):
        data_list = []
        timesheet_item_objects = TimeSheetItem.objects.filter(user_id=user_id)
        for each in timesheet_item_objects:
            data_list.append(TimeSheetItemArchive(timesheet_item_id = each.timesheet_item_id,
            timesheet_id = each.timesheet_id,
            module_id = each.module_id,
            project_id = each.project_id,
            activity_id = each.activity_id,
            duration = each.duration,
            comment = each.comment,
            user_id = each.user_id,
            timesheet_date = each.timesheet_date,
            is_billable = each.is_billable,
            percentage_completed = each.percentage_completed,
            status = each.status,
            ticket_title = each.ticket_title,
            ticket_eta = each.ticket_eta
            ))
        TimeSheetItemArchive.objects.bulk_create(data_list)
        TimeSheetItem.objects.filter(user_id=user_id).delete()

    def get_timesheet_date_range(sel,emp_id,start_date,end_date):
        try :
            obj_timeSheet = TimeSheet.objects.filter(user_id = emp_id , timesheet_date__gte = start_date,timesheet_date__lte = end_date)
        except :
            print("Error")
        return obj_timeSheet

    def get_timesheets_by_date_range(self,start_date,end_date):
        return TimeSheet.objects.filter(timesheet_date__gte = start_date,timesheet_date__lte = end_date)

    def get_all_timesheet_log(self):
        return TimeSheetActionLog.objects.all()

    def get_timesheet_item_by_date_range(self,start_date,end_date):
        return TimeSheetItem.objects.filter(timesheet_date__gte = start_date,timesheet_date__lte = end_date)

    def bulk_create_timesheet_archive_and_log_archive(self, timesheets, log_dict):
        data_list = []
        timesheet_ids =[]
        log_list = []
        for each_timesheet in timesheets:
            data_list.append(TimeSheetArchive(timesheet_id = each_timesheet.timesheet_id,
                status = each_timesheet.status,
                timesheet_date = each_timesheet.timesheet_date,
                user_id = each_timesheet.user_id,
                total_duration = each_timesheet.total_duration,
                created_date = each_timesheet.created_date
                ))
            logs = log_dict.get(each_timesheet.timesheet_id,None)
            timesheet_ids.append(each_timesheet.timesheet_id)
            for each_log in logs:
                log_list.append(TimeSheetActionLogArchive(action_id = each_log.action_id,
                timesheet_id = each_log.timesheet_id,
                comment = each_log.comment,
                action = each_log.action,
                action_date = each_log.action_date,
                performed_by = each_log.performed_by
                ))
        TimeSheetActionLogArchive.objects.bulk_create(log_list)
        TimeSheetArchive.objects.bulk_create(data_list)
        

        return timesheet_ids

    def bulk_create_timesheet_items_archive(self, timesheet_items):
        data_list = []
        for each_item in timesheet_items:
            data_list.append(TimeSheetItemArchive(timesheet_item_id = each_item.timesheet_item_id,
            timesheet_id = each_item.timesheet_id,
            module_id = each_item.module_id,
            project_id = each_item.project_id,
            activity_id = each_item.activity_id,
            duration = each_item.duration,
            comment = each_item.comment,
            user_id = each_item.user_id,
            timesheet_date = each_item.timesheet_date,
            is_billable = each_item.is_billable,
            percentage_completed = each_item.percentage_completed,
            status = each_item.status,
            ticket_title = each_item.ticket_title,
            ticket_eta = each_item.ticket_eta
            ))
            
        return TimeSheetItemArchive.objects.bulk_create(data_list)

    def delete_timesheets_by_date_range(self, from_date, to_date):
        return TimeSheet.objects.filter(timesheet_date__gte = from_date,timesheet_date__lte = to_date).delete()
    
    def delete_timesheets_items_by_date_range(self, from_date, to_date):
        return TimeSheetItem.objects.filter(timesheet_date__gte = from_date,timesheet_date__lte = to_date).delete()
    
    def delete_timesheet_log_by_timesheet_ids(self, timesheet_ids):
        return TimeSheetActionLog.objects.filter(timesheet_id__in =timesheet_ids) .delete()
    
    def create_timesheet_archive_log(self, data):
        return TimeSheetArchiveLog.objects.create(**data)
    
    def get_all_timesheet_archives(self):
        return TimeSheetArchiveLog.objects.all()
    
    def get_timesheet_archive_log_by_id(self,archive_id):
        return TimeSheetArchiveLog.objects.filter(archive_id=archive_id ).first()
    
    def get_archived_timesheets_by_date_range(self,from_date, to_date):
        return TimeSheetArchive.objects.filter(timesheet_date__gte = from_date,timesheet_date__lte = to_date)
    
    def get_all_archived_timesheet_log(self):
        return TimeSheetActionLogArchive.objects.all()
    
    def get_archived_timesheet_items_by_date_range(self,start_date, end_date):
        return TimeSheetItemArchive.objects.filter(timesheet_date__gte = start_date,timesheet_date__lte = end_date)

    def bulk_create_timesheet_from_archive_and_log_archive(self,timesheets,log_dict):
        data_list = []
        timesheet_ids =[]
        log_list = []
        for each_timesheet in timesheets:
            data_list.append(TimeSheet(timesheet_id = each_timesheet.timesheet_id,
                status = each_timesheet.status,
                timesheet_date = each_timesheet.timesheet_date,
                user_id = each_timesheet.user_id,
                total_duration = each_timesheet.total_duration,
                created_date = each_timesheet.created_date
                ))
            logs = log_dict.get(each_timesheet.timesheet_id,None)
            timesheet_ids.append(each_timesheet.timesheet_id)
            for each_log in logs:
                log_list.append(TimeSheetActionLog(action_id = each_log.action_id,
                timesheet_id = each_log.timesheet_id,
                comment = each_log.comment,
                action = each_log.action,
                action_date = each_log.action_date,
                performed_by = each_log.performed_by
                ))
        TimeSheetActionLog.objects.bulk_create(log_list)
        TimeSheet.objects.bulk_create(data_list)
        

        return timesheet_ids
    
    def bulk_create_timesheet_items_from_archive(self, timesheet_items):
        data_list = []
        for each_item in timesheet_items:
            data_list.append(TimeSheetItem(timesheet_item_id = each_item.timesheet_item_id,
            timesheet_id = each_item.timesheet_id,
            module_id = each_item.module_id,
            project_id = each_item.project_id,
            activity_id = each_item.activity_id,
            duration = each_item.duration,
            comment = each_item.comment,
            user_id = each_item.user_id,
            timesheet_date = each_item.timesheet_date,
            is_billable = each_item.is_billable,
            percentage_completed = each_item.percentage_completed,
            status = each_item.status,
            ticket_title = each_item.ticket_title,
            ticket_eta = each_item.ticket_eta
            ))
            
        return TimeSheetItem.objects.bulk_create(data_list)
    
    def delete_timesheets_archive_by_date_range(self, start_date, end_date):
        return TimeSheetArchive.objects.filter(timesheet_date__gte = start_date,timesheet_date__lte = end_date).delete()
    
    def delete_timesheets_items_archives_by_date_range(self, start_date, end_date):
        return TimeSheetItemArchive.objects.filter(timesheet_date__gte = start_date,timesheet_date__lte = end_date).delete()
    
    def delete_timesheet_log_archive_by_timesheet_ids(self, timesheet_ids):
        return TimeSheetActionLogArchive.objects.filter(timesheet_id__in =timesheet_ids) .delete()
    
    def delete_timesheet_archive_log(self, archive_id):
        return TimeSheetArchiveLog.objects.filter(archive_id =archive_id) .delete()
    
    def create_exclude_timesheet_employee(self, data_dict):
        return TimesheetExcludedEmployees.objects.create(**data_dict)











