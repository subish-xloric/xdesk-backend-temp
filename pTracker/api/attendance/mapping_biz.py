import math
from  datetime import datetime, timedelta
from django.conf import settings
from types import SimpleNamespace


from pTracker.common.company_authorization import data_scope, SCOPE_ALL, SCOPE_TEAM
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
        """ Whether lead_id - always the authenticated caller (request.user.id in
        views.py), never an id the client supplies - may access user_id's attendance
        data. Own data is always accessible; beyond that this follows the caller's
        attendance scope for their active company (attendance.view_all /
        attendance.view_team, see data_scope): company-wide, own team only, or
        nobody else's. """
        if user_id == lead_id:
            return True
        scope = data_scope(lead_id, 'attendance')
        if scope == SCOPE_ALL:
            return True
        if scope == SCOPE_TEAM:
            return UserDA().is_team_member(user_id, lead_id)
        return False

    def get_mapping_list(self, user_id):
        """ The employees user_id (the authenticated caller) may see: everyone with
        attendance.view_all, their own team with attendance.view_team, nobody
        otherwise. user_id is always request.user.id, never a team id the client
        supplies. """
        scope = data_scope(user_id, 'attendance')
        if scope == SCOPE_ALL:
            users = UserDA().get_all_active_users()
        elif scope == SCOPE_TEAM:
            users = UserDA().get_current_team_members_by_lead_id(user_id)
        else:
            users = None

        team_list = []
        if users:
            for user in users:
                team_list.append({
                    "emp_id": user.id,
                    "emp_name": str(user.first_name) + " " + str(user.last_name)
                })
        return team_list
