
import math
from  datetime import datetime, timedelta
from django.conf import settings
from types import SimpleNamespace


from pTracker.common.utility import Utility
from pTracker.dataaccess.ptracker_access.user_da import UserDA


def new_dto():
    dto = SimpleNamespace()
    return dto


class UserMappingBL():

    def get_employee_code(self, user_id):
        emp_code = None
        user = UserDA().get_user_by_id(user_id)
        if user_id:
            emp_code = user.username
        return emp_code

    def is_employee_accessible(self, user_id, lead_id):
        is_accessible = False
        role_id, role_name = UserDA().get_user_role_by_id(lead_id)
        if user_id == lead_id:
            return True
        if role_name:
            if str(role_name).lower() in ('cto', 'ceo', 'director', 'hr'):
                is_accessible = True
            elif str(role_name).lower() == 'manager':
                if user_id not in (2, 3):
                    is_accessible = True
            elif str(role_name).lower() == 'lead':
                is_accessible = UserDA().is_team_member(user_id, lead_id)
        return is_accessible

    def get_mapping_list(self, user_id):
        users = None
        team_list = []
        role_id, role_name = UserDA().get_user_role_by_id(user_id)
        if role_name:
            if str(role_name).lower() in ('cto', 'ceo', 'manager', 'director', 'hr'):
                users = UserDA().get_all_active_users()
            elif str(role_name).lower() == 'lead':
                users = UserDA().get_current_team_members_by_lead_id(user_id)

            if users:
                for user in users:
                    temp_dict = {
                        "emp_id": user.id ,
                        "emp_name": str(user.first_name) + " " + str(user.last_name)
                    }


                    if str(role_name).lower() not in ('cto', 'ceo', 'director'):
                        if user.username in ('200', '201'):
                            continue
                    team_list.append(temp_dict)
        return team_list

