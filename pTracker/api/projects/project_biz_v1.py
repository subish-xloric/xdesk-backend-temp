from  datetime import datetime

from django.conf import settings
from types import SimpleNamespace

from django.db.models import base

from pTracker.common.utility import Utility
from pTracker.dataaccess.ptracker_access.project_da import  ProjectDA
from pTracker.dataaccess.ptracker_access.user_da import UserDA

from pTracker.common.logs import Logs
from pTracker.common.exception_handler import ExceptionHandler


def new_dto():
    dto = SimpleNamespace()
    return dto


class ProjectBL_V1():

    def __init__(self):
        self.__logs = Logs()
        self.__exception = ExceptionHandler()
    
    def format_activiteis(self, result):
        if not result:
            result = {"activities": []}
        else:
            result = {"activities": result}
        return result
    
    def format_get_modules(self, result):
        if result[0].get('error'):
            result = {"error": result[0].get('error'), "status": result[0].get('status', 200)}
        else:
            result = {"modules": result,  "status": 200}
        return result
    
    def format_get_projects(self, result):
        if result[0].get('error'):
            result = {"error": result[0].get('error'), "status": result[0].get('status', 200)}
        else:
            result = {"projects": result, "status": 200}
        return result