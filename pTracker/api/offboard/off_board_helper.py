from types import SimpleNamespace
from datetime import datetime, timedelta

from django.conf import settings
from django.contrib.auth.models import User

from pTracker.common.utility import Utility
from pTracker.common.exception_handler import ExceptionHandler
from pTracker.common.logs import Logs

from pTracker.dataaccess.ptracker_access.user_da import UserDA
from pTracker.dataaccess.ptracker_access.off_board_da import OffBoardDA

from pTracker.api.offboard.off_board_notification_biz import OffBoardNotificationBL


def new_dto():
    dto = SimpleNamespace()
    return dto


class OffBoardHelperBL():
    def __init__(self):
        self.__log = Logs()
        self.__exception = ExceptionHandler()
        self.__utility = Utility()

    def off_boarding_exit_form(self):
        template = {
            'off_boarding_id': 0,
            'emp_id': 0,
            'exit_form_data': '',
            'off_boarding_code': '',
            'status': 1,
            'organization_id': 0,
            'request_date': '',
            'releiving_date': ''
        }
        return template

    def get_exit_employee_template(self):
        template = {
            "name": "",
            "employee_code": 0,
            "employee_id": 0,
            "off_board_request_date": '',
            "relieving_date": '',
            "off_boarding_id": 0,
            "organization_id": 0
        }
        return template

    def get_exit_form_template(self):
        template = {
            "employee": '',
            "department": []
        }
        return template
