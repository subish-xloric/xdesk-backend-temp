from datetime import datetime

from django.conf import settings
from types import SimpleNamespace


from pTracker.common.logs import Logs
from pTracker.common.utility import Utility
from pTracker.common.exception_handler import ExceptionHandler

from pTracker.dataaccess.ptracker_access.timesheet_da import  TimeSheetDA
from pTracker.dataaccess.ptracker_access.project_da import  ProjectDA
from pTracker.dataaccess.ptracker_access.user_da import UserDA
from pTracker.dataaccess.ptracker_access.attendance import AttendanceDA
from pTracker.cronjobs.archive_timesheets import archive_timesheets
from pTracker.cronjobs.archive_timesheets import restore_timesheets


def new_dto():
    dto = SimpleNamespace()
    return dto


class ArchiveTimeSheetBL():

    def __init__(self):
        self.__log = Logs()
        self.__exception = ExceptionHandler()
        self.__utility = Utility()

    def create_timesheet_archive(self, user_id, data):
        objUser = UserDA()
        response = {'error' : '', 'success' : '', 'status' : 200}
        try:
            from_date = data.get("from_date", None)
            to_date = data.get("to_date", None)
            if from_date and to_date:
                from_date_obj = datetime.strptime(from_date, "%Y-%m-%d")
                to_date_obj = datetime.strptime(to_date, "%Y-%m-%d")
                archive_timesheets(user_id, from_date, to_date)
                response["success"] = "Job queed successfully"
            else:
                response["error"] = "Invalid Dates."
                response["error"] = 499
        except Exception as error:
            print(error)
            response["error"] = settings.ERROR_MSG['application_error']\
                .format(error, self.__log.error(self.__exception.get_exception()))
            response['status'] = 499
        return response
    
    def get_all_timesheet_archives(self):
        response = {'error' : '', 'success' : '', 'status' : 200}
        archive_list = []
        try:
            archives = TimeSheetDA().get_all_timesheet_archives()
            for each_archive in archives:
                temp = {}
                temp['archive_log_id'] = each_archive.archive_id
                temp['archive_from'] = datetime.strftime(each_archive.archive_from,'%d-%m-%Y')
                temp['archive_to'] = datetime.strftime(each_archive.archive_to,'%d-%m-%Y')
                temp['archive_date'] = datetime.strftime(each_archive.archive_date,'%d-%m-%Y') 
                archive_list.append(temp)
            response['data'] = archive_list
        except Exception as error:
            response["error"] = settings.ERROR_MSG['application_error']\
                .format(error, self.__log.error(self.__exception.get_exception()))
            response['status'] = 499
        return response
    
    def restore_timesheet_from_archive(self, user_id, data):
        response = {'error' : '', 'success' : '', 'status' : 200}
        try:
            archive_id = data.get("archive_log_id", None)
           
            if archive_id:
                archive_obj = TimeSheetDA().get_timesheet_archive_log_by_id(archive_id)
                if archive_obj:
                    form_date = archive_obj.archive_from
                    to_date = archive_obj.archive_to
                    restore_timesheets(form_date, to_date, archive_id)

                    response["success"] = "Job queed successfully"
                else:
                    response["error"] = "Invalid Archive ID."
                    response["error"] = 499
            else:
                response["error"] = "Invalid Archive ID."
                response["status"] = 499
        except Exception as error:
            response["error"] = settings.ERROR_MSG['application_error']\
                .format(error, self.__log.error(self.__exception.get_exception()))
            response['status'] = 499
        return response

