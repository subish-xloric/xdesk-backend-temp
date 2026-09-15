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




def new_dto():
    dto = SimpleNamespace()
    return dto


@app.task(bind=True)
def offboard_final_process(self, user_id, off_boarding_id):
    try:
        update_data = {}
        user_update_data = {}
        with transaction.atomic():
            lead_mappings = UserDA().get_emp_lead_mapping_by_emp_id(user_id)
            UserDA().create_emp_lead_mapping_relieving_log(lead_mappings)
            UserDA().delete_lead_mapping_by_employee_id(user_id)
            ProjectDA().delete_employee_project_mappings_by_user_id(user_id)
            ProjectDA().update_employee_project_mapping_log(user_id)
            update_data['job_status'] = 4 #TODO remove hard code values  settings.EMPLOYMENT_STATUS[]
            UserDA().update_user_profile(user_id, update_data)
            user_update_data['is_active'] = 0
            UserDA().update_auth_user(user_update_data, user_id)
            TimeSheetDA().create_timesheet_archive(user_id)
            TimeSheetDA().create_timesheet_item_archive(user_id)

            update_data = {"status": settings.OFF_BOARD_REQUEST_STATUS['Completed']}
            OffBoardDA().update_offboard_request(off_boarding_id, update_data)


    except Exception as e:
        msg = "Error in the job offboard_final_process, Error is : {0} ".format(
            str(e))
        Logs().error(msg)

@app.task(bind=True)
def terminate_employee_check(self):
    try:
        offboard_requests = OffBoardDA().get_initiated_termination_requests()
        if offboard_requests:
            filter_date = datetime.today() - timedelta(days=1)
            for each in offboard_requests:
                if each.relieving_date <= filter_date.date():
                    offboard_final_process.apply_async([each.user_id, each.id], queue=settings.CELERY_QUEUE['offboarding'])

                    # update_data = {"status": settings.OFF_BOARD_REQUEST_STATUS['Completed']}
                    # OffBoardDA().update_offboard_request(off_boarding_request.id, update_data)
    except Exception as e:
        msg = "Error in the job terminate_employee_check, Error is : {0} ".format(
            str(e))
        Logs().error(msg)
