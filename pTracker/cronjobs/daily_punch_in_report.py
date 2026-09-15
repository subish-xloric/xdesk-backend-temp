from datetime import datetime, timedelta
from celery import shared_task as task
import math
from pTracker.celery import app

from django.conf import settings

from pTracker.attendance.punch_in_report import PunchInBL
from pTracker.user_management.holiday_da import HolidayDA
from pTracker.common.utility import Utility



@app.task(bind=True)
def create_daily_punch_in_report(self):

    try:
        current_day = datetime.now()
        is_holiday = HolidayDA().is_holiday(current_day.strftime("%Y-%m-%d"))

        if current_day.weekday() in (5, 6):
            pass
        elif is_holiday:
            pass
        else:
            PunchInBL().generate_daily_punch_in_report(current_day.strftime("%Y-%m-%d"))
    except Exception as e:
        msg = "Error in the job create_daily_punch_in_report, Error is : {0} ".format(str(e))
        print( 'msg', msg)
        Utility().log(msg)
    finally:
        pass