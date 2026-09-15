from datetime import datetime, timedelta
from celery import shared_task as task
import math
from pTracker.celery import app

from django.conf import settings

from pTracker.attendance.daily_work_hours_report import DailyWorkHoursReportBL
from pTracker.attendance.daily_att_report import DailyAttendanceReportBL
from pTracker.common.utility import Utility
from pTracker.user_management.holiday_da import HolidayDA


@app.task(bind=True)
def create_daily_work_hours_report(self):

    try:
        if datetime.now().weekday() == 0:
            last_day = datetime.now() - timedelta(3)
        else:
            last_day = datetime.now() - timedelta(1)

        is_holiday = HolidayDA().is_holiday(last_day.strftime("%Y-%m-%d"))
        if is_holiday:
            pass
        else:
            DailyWorkHoursReportBL().generate_daily_work_hours_report(last_day.strftime("%Y-%m-%d"))


    except Exception as e:
        msg = "Error in the job create_daily_work_hours_report, Error is : {0} ".format(str(e))
        print('msg', msg)
        Utility().log(msg)
    finally:
        pass


