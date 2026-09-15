from datetime import date, datetime, timedelta
from types import SimpleNamespace

from celery import shared_task as task
from django.conf import settings

from django.db import  transaction

from pTracker.celery import app
from pTracker.common.utility import Utility
from pTracker.common.logs import Logs

from pTracker.dataaccess.ptracker_access.user_da import UserDA
from pTracker.dataaccess.ptracker_access.project_da import ProjectDA
from pTracker.dataaccess.ptracker_access.timesheet_da import TimeSheetDA
from pTracker.dataaccess.ptracker_access.off_board_da import OffBoardDA
from pTracker.cronjobs.email_sender import send_email_notification

from pTracker.api.timesheet.timesheet_biz import TimeSheetBL




def new_dto():
    dto = SimpleNamespace()
    return dto


@app.task(bind=True)
def archive_timesheets(self, user_id, start_date, end_date):
    try:
        update_data = {}
        user_update_data = {}
        log_dict = {}
        with transaction.atomic():
            timesheets = TimeSheetBL().get_timesheets_by_date_range(start_date,end_date)
            timesheet_logs = TimeSheetBL().get_all_timesheet_log()
            timesheet_items = TimeSheetBL().get_timesheet_items_by_date_range(start_date,end_date)
            for each_log in timesheet_logs:
                timesheet_id = each_log.timesheet_id
                if timesheet_id in  log_dict:
                    log_dict[timesheet_id].append(each_log)
                else:
                    log_dict[timesheet_id] = [each_log]
            timesheet_ids = TimeSheetBL().bulk_create_timesheet_archive_and_log_archive(timesheets,log_dict)
            TimeSheetBL().bulk_create_timesheet_items_archive(timesheet_items)
            TimeSheetBL().delete_timesheets_by_date_range(start_date,end_date)
            TimeSheetBL().delete_timesheet_items_by_date_range(start_date,end_date)
            TimeSheetBL().delete_timesheet_log_by_timesheet_ids(timesheet_ids)
            TimeSheetBL().create_timesheet_archive_log(start_date,end_date,user_id)
            send_job_summary(user_id,0,start_date,end_date)



    except Exception as e:
        msg = "Error in the job archive_timesheets, Error is : {0} ".format(
            str(e))
        Logs().error(msg)
    
def send_job_summary(emp_id, is_archive, from_date, to_date):
    mail_dto = {}
    emp = UserDA().get_user_by_id(emp_id)
    if is_archive:
        subject = "Timesheet Archive Job Summary"
        msg = "Timesheets from {0} to {2} archived".format(from_date, to_date)
    else:
        subject = "Restore Timesheet from Archive Job Summary"
        msg = "Timesheets from {0} to {2} Restored from  Archives".format(from_date, to_date)
    mail_dto["subject"] = "DM DESK: {0} .".format(subject)
    mail_dto["from_address"] = settings.EMAIL_ADDRESS['do_not_reply']['name']
    mail_dto["body"] = msg
    mail_dto["to_addresses"] = [emp.email]
    mail_dto["smtp_username"] = settings.EMAIL_ADDRESS['do_not_reply']['mailID']
    mail_dto["smtp_password"] = settings.EMAIL_ADDRESS['do_not_reply']['password']
    # uncomment to send mail TODO
    send_email_notification.apply_async([mail_dto, 1], queue=settings.CELERY_QUEUE['mail_sender'])

@app.task(bind=True)
def restore_timesheets(self, start_date, end_date, archive_id, user_id):
    log_dict = {}
    try:
        start_date = start_date.strftime("%Y-%m-%d")
        end_date = end_date.strftime("%Y-%m-%d")
        timesheets = TimeSheetBL().get_archived_timesheets_by_date_range(start_date,end_date)
        print(len(timesheets), "-timesheets")
        timesheet_logs = TimeSheetBL().get_all_archived_timesheet_log()
        print(len(timesheet_logs), "-timesheet_logs")
        timesheet_items = TimeSheetBL().get_archived_timesheet_items_by_date_range(start_date,end_date)
        print(len(timesheet_items), "-timesheet_items")
        for each_log in timesheet_logs:
            timesheet_id = each_log.timesheet_id
            if timesheet_id in  log_dict:
                log_dict[timesheet_id].append(each_log)
            else:
                log_dict[timesheet_id] = [each_log]
        with transaction.atomic():
            timesheet_ids = TimeSheetBL().bulk_create_timesheet_from_archive_and_log_archive(timesheets,log_dict)
            TimeSheetBL().bulk_create_timesheet_items_from_archive(timesheet_items)
            TimeSheetBL().delete_timesheets_archive_by_date_range(start_date,end_date)
            TimeSheetBL().delete_timesheet_items_archives_by_date_range(start_date,end_date)
            TimeSheetBL().delete_timesheet_log_archive_by_timesheet_ids(timesheet_ids)
            TimeSheetBL().delete_timesheet_archive_log(archive_id)
            send_job_summary(user_id,1,start_date,end_date)
    except Exception as e:
        msg = "Error in the job restore_timesheets, Error is : {0} ".format(
            str(e))
        Logs().error(msg)
