from  datetime import datetime, date, timedelta

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


class ResourceBL():

    def __init__(self):
        self.__log = Logs()
        self.__exception = ExceptionHandler()
        self.__utility = Utility()
    
    def get_all_map_logs(self):
        log_dict = {}
        log_objs = ProjectDA().get_all_map_logs()
        if log_objs:
            for each_log in log_objs:
                msg = each_log.comment
                if each_log.emp_id not in log_dict:
                    log_dict[each_log.emp_id] = [msg]
                else:
                    log_dict[each_log.emp_id].append(msg)
        return log_dict

    
    def get_all_mapped_users_dict(self,billable_or_not, account_id = 0):
        mapped_dict = {}
        mapped_objs = ProjectDA().get_all_mapped_users_by_billable_or_not(billable_or_not, account_id)
        if mapped_objs:
            for mapped_obj in mapped_objs:
                mapped_dict[mapped_obj.emp_id] = mapped_obj
        return mapped_dict


    def __is_billable_status_valid(self,status):
        return True


    def __is_valid_map_status(self,map_status):
        try:
            status = settings.PROJECT_ACC_MAP_STATUS[int(map_status),None]
            if status:
                return True
            else:
                return False
        except:
            return False
    
    def is_account_valid(self,account_id):
        try:
            account_id = int(account_id)
            account_dict = self.get_all_project_account_dict()
            account_obj = account_dict.get(account_id,None)
            if account_obj:
                return True
            else:
                return False

        except:
            return False
    
    def get_all_project_account_dict(self):
        account_dict = {}
        accounts = ProjectDA().get_all_project_accounts()
        if accounts:
            for account in accounts:
                account_dict[account.account_id] = account
        return account_dict


    def get_all_project_accounts(self):
        result = {"error": None, "accounts": []}
        account_list = []
        try:

            accounts = ProjectDA().get_all_project_accounts()
            if accounts:
                for account in accounts:
                    account_list.append({"id": account.account_id, "name": account.name})
            result['accounts'] = account_list
        except Exception as err:
            result["error"] = settings.ERROR_MSG["application_error"].format(
                str(err), self.__log.error(self.__exception.get_exception())
            )

        return result

    def get_all_project_accnt_emp_mapping(self,user_id,year_and_month,map_status,billable,account):
        result = {"error": None, "accounts": []}
        account_list = []
        try:
            role_id, role_name = UserDA().get_user_role_by_id(user_id)
            if role_id not in (1, '1',2, '2',3, '3'):
                result['error'] = settings.ERROR_MSG['access_denied']
                return result

            # is_map_status_valid = self.__is_valid_map_status(map_status)
            # if not is_map_status_valid:
            #     result['error'] = "Not a Valid Map Status ."
            #     return result

            # is_account_valid = self.is_account_valid(account)
            # if not is_account_valid:
            #     result['error'] = "Not a Valid Account ID ."
            #     return result

            is_billable_valid = self.__is_billable_status_valid(billable)

            map_status = settings.PROJECT_ACC_MAP_STATUS.get(int(map_status),None)

            result_list = []

            if map_status == 'Un Mapped':
                mapped_users_dict = self.get_all_mapped_users_dict(billable,account)
                map_log_dict = self.get_all_map_logs()
                activeUsers = UserDA().get_all_active_users()
                if activeUsers:
                    for user in activeUsers:
                        map_obj = mapped_users_dict.get(user.id)
                        if map_obj:
                            continue
                        else:
                            temp = {}
                            temp['user_id'] = user.id
                            temp['name'] = user.first_name + ' '+ user.last_name
                            temp['account'] = '-'
                            temp['start_date'] = '-'
                            temp['end_date'] = '-'
                            temp['alias'] = '-'
                            temp['billable'] = 2
                            temp['log'] = map_log_dict.get(user.id,[])

                            result_list.append(temp)
            result['accounts'] = result_list
        except Exception as err:
            result["error"] = settings.ERROR_MSG["application_error"].format(
                str(err), self.__log.error(self.__exception.get_exception())
            )

        return result