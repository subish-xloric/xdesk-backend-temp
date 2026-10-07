from datetime import datetime, timedelta

from pTracker.celery import app
from pTracker.common.utility import Utility
from pTracker.api.attendance_v2.daily_job_biz import AttendanceDailyJobBL


@app.task(bind=True)
def finalize_attendance_v2(self):
    """ Runs late in the evening for the previous date, after even an overnight
    shift's punch window for that date has closed. """
    try:
        AttendanceDailyJobBL().run((datetime.now() - timedelta(days=1)).date())
    except Exception as e:
        Utility().log("Error in the job finalize_attendance_v2, Error is : {0} ".format(str(e)))
