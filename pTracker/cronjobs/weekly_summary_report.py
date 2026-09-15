from datetime import datetime, timedelta
from celery import shared_task as task
import math
from pTracker.celery import app

from django.conf import settings

# from pTracker.attendance.punch_in_report import PunchInBL
# from pTracker.user_management.holiday_da import HolidayDA
from pTracker.attendance.weekly_att_report import WeeklyAttendanceReportBL
from pTracker.common.utility import Utility



@app.task(bind=True)
def create_weekly_summary_report(self):

    try:

        last_friday = datetime.now() - timedelta(3)
        last_monday = datetime.now() - timedelta(7)
        WeeklyAttendanceReportBL().generate_weekly_att_report(last_monday.strftime("%Y-%m-%d"), last_friday.strftime("%Y-%m-%d"))
    except Exception as e:
        msg = "Error in the job create_daily_punch_in_report, Error is : {0} ".format(str(e))
        print( 'msg', msg)
        Utility().log(msg)
    finally:
        pass