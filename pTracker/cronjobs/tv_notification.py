
from  datetime import datetime, date, timedelta

from django.conf import settings

from pTracker.celery import app
from pTracker.common.logs import Logs
from pTracker.dataaccess.ptracker_access.user_da import UserDA
from pTracker.common.exception_handler import ExceptionHandler
from pTracker.dataaccess.ptracker_access.holiday_da import HolidayDA
from pTracker.api.rewards.rewards_biz import RewardsBL
from pTracker.cronjobs.email_sender import send_email_notification

@app.task(bind=True)
def create_birthday_events(self):
    try:
        current_date = date.today()
        birthdays, err = UserDA().get_current_date_birthdays(current_date)
        if birthdays:
            is_holiday = HolidayDA().get_holiday_by_date(current_date)
            for row in birthdays:
                employe_name = str(row[1]) + ' ' + str(row[2])
                # Iterate until a valid date_and_time is found
                short_desc = ''
                title = 'Happy Birthday'
                while check_is_weekend(current_date) or is_holiday:
                    current_date += timedelta(days=1)
                    is_holiday = HolidayDA().get_holiday_by_date(current_date)
                    title = 'Belated Happy Birthday'
                    short_desc = 'belated' #current_date.strftime("%B %d")
                RewardsBL().create_tv_notification('Birthday', title=title, short_desc=short_desc, date=current_date, emp_id=row[5])
    except Exception as error:
        sub = "Job create_birthday_events failed"
        err = ExceptionHandler().get_exception()
        content = str(error) + " ." + str(err)
        send_job_failed_notification(sub, content, 'subish@digitalmesh.com')
        Logs().error(err)
    return True

def check_is_weekend(date):
        return date.weekday() in [5, 6]  # Saturday is 5, Sunday is 6

def send_job_failed_notification(subject, content, to_email):
        mail_dto = {}
        mail_dto["subject"] = subject
        mail_dto["from_address"] = settings.EMAIL_ADDRESS['do_not_reply']['name']
        mail_dto["body"] = content
        mail_dto["to_addresses"] = [to_email]
        mail_dto["smtp_username"] = settings.EMAIL_ADDRESS['do_not_reply']['mailID']
        mail_dto["smtp_password"] = settings.EMAIL_ADDRESS['do_not_reply']['password']
        send_email_notification.apply_async([mail_dto, 1], queue=settings.CELERY_QUEUE['mail_sender'])