from datetime import datetime, timedelta
from celery import shared_task as task
import math
from pTracker.celery import app

from django.conf import settings

from pTracker.attendance.monthly_att_report import MonthlyAttendanceReportBL
from pTracker.attendance.daily_att_report import DailyAttendanceReportBL
from pTracker.common.utility import Utility
from pTracker.user_management.holiday_da import HolidayDA


@app.task(bind=True)
def create_monthly_att_report(self):
    try:
        today = datetime.now()
        first = today.replace(day=1)
        lastMonth = first - timedelta(days=3)
        month = int(lastMonth.strftime("%m"))
        year = int(lastMonth.strftime("%Y"))
        MonthlyAttendanceReportBL().generate_monthly_att_report(month, year)
    except Exception as e:
        msg = "Error in the job create_monthly_att_report, Error is : {0} ".format(str(e))
        Utility().log(msg)
    finally:
        pass


@app.task(bind=True)
def create_daily_att_report(self):

    try:
        if datetime.now().weekday() == 0:
            last_day = datetime.now() - timedelta(3)
        else:
            last_day = datetime.now() - timedelta(1)

        is_holiday = HolidayDA().is_holiday(last_day.strftime("%Y-%m-%d"))

        if not is_holiday:
            DailyAttendanceReportBL().generate_daily_att_report(last_day.strftime("%Y-%m-%d"))

    except Exception as e:
        msg = "Error in the job create_daily_att_report, Error is : {0} ".format(str(e))
        Utility().log(msg)
    finally:
        pass