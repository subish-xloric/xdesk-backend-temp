from datetime import datetime, date, timedelta
from trace import Trace
from django.conf import Settings, settings
from django.contrib.auth.models import User

from pTracker.common.utility import Utility
from pTracker.common.exception_handler import ExceptionHandler
from pTracker.common.logs import Logs

from pTracker.dataaccess.ptracker_access.user_da import UserDA


from types import SimpleNamespace


def new_dto():
    dto = SimpleNamespace()
    return dto


class LeadEmpMapping():
    def __init__(self):
        self.__log = Logs()
        self.__exception = ExceptionHandler()
        self.__utility = Utility()

    def get_leads(self):
        result = {
            "leads": [],
            "unmapped_emps": [],
            "error": ''
        }
        leads = []
        try:
            supervisors, err = UserDA().get_all_supervisors()
            if supervisors:
                    for each in supervisors:
                        temp = {}
                        temp['name'] = each[1] + ' ' + each[2]
                        temp['id'] = each[0]
                        leads.append(temp)
                    result['leads'] = leads
            unmapped_employees = self.get_all_un_mapped_employees()
            result['unmapped_emps'] = unmapped_employees['unmapped_emps']

        except Exception as err:
            result["error"] = settings.ERROR_MSG['application_error']\
                .format(str(err), self.__log.error(self.__exception.get_exception()))
        return result

    def get_all_un_mapped_employees(self):
        result = {
            "error": '',
            "unmapped_emps": []
        }
        try:
            unmapped_list = []
            mapping_excluded = ['2', '3',2,3]
            all_users = UserDA().get_all_active_users()
            mapped_emps = UserDA().get_all_mapped_employess()
            for each_emp in mapped_emps:
                all_users = all_users.exclude(id= each_emp.emp_id)
            for each in  mapping_excluded:
                all_users = all_users.exclude(id= each)

            for each in all_users:
                temp = {}
                temp['name'] = each.first_name + ' ' + each.last_name
                temp['id'] = each.id
                unmapped_list.append(temp)
            result['unmapped_emps'] = unmapped_list

        except Exception as err:
            result["error"] = settings.ERROR_MSG['application_error']\
                .format(str(err), self.__log.error(self.__exception.get_exception()))
        return result

    def get_employees_by_lead(self, request):
        result = {
            'emps': [],
            'error' : ''

        }
        team_member_list = []
        try:
            lead_id = request.get('lead_id', None)
            team_members = UserDA().get_current_team_members_by_lead_id(lead_id)
            for each in team_members:
                temp = {}
                temp['name'] = each.first_name + ' ' + each.last_name
                temp['id'] = each.id
                team_member_list.append(temp)
            result['emps'] = team_member_list
        except Exception as err:
            result["error"] = settings.ERROR_MSG['application_error']\
                .format(str(err), self.__log.error(self.__exception.get_exception()))
        return result

    def employee_lead_mapping(self, request,user_id):
        result = {
            'message': '',
            'error': '',
            "status" : 200
        }
        try:
            is_access = self.__is_employee_lead_mapping_access(user_id)            
            if not is_access:
                result['error'] = settings.ERROR_MSG['no_permission']
                result['status'] = 403
                return result
            map_data = request.data
            temp = []
            for n, i in enumerate(map_data):
                next_dicts = map_data[n + 1:]
                for each in next_dicts:
                    if i['lead_id'] == each['lead_id'] and i['employee_id'] == each['employee_id']:
                        if i['emp_pool_dir'] != each['emp_pool_dir']:
                            temp.append(i)
                            temp.append(each)
            for each in temp:
                if each in map_data:
                    map_data.remove(each)
            if map_data:
                for each in map_data:
                    mapping_data = {}
                    lead = UserDA().get_user_by_id(each['lead_id'])
                    lead_name = lead.first_name + '' + lead.last_name
                    if (each['emp_pool_dir'] == 'OUT'):
                        is_already_exist = self.is_exist_active_mapping(each['employee_id'], each['lead_id'])
                        if is_already_exist:
                            result['error'] = 'Mapping already done !!'
                            result['status'] = 450
                            return result

                        emp_lead_maping_obj = UserDA().create_employee_lead_mapping(each['employee_id'], each['lead_id'], date.today())
                        action = settings.EMP_LEAD_MAPPING_LOG[1].format(lead_name,
                                                                         datetime.now().strftime("%d/%m/%Y %I:%M %p"))
                    mapping_obj = UserDA().get_emp_lead_mapping_by_emp_id_and_lead_id(each['employee_id'], each['lead_id'])
                    if (each['emp_pool_dir'] == 'IN'):
                        mapping_data['is_deleted'] = 1
                        mapping_data['to_date'] = date.today()
                        emp_lead_maping_obj = UserDA().update_employee_lead_mapping_v2(each['employee_id'], each['lead_id'], mapping_data)
                        action = settings.EMP_LEAD_MAPPING_LOG[2].format(lead_name,
                                                                         datetime.now().strftime("%d/%m/%Y %I:%M %p"))

                    log_data = {
                        'mapping_id': mapping_obj.id,
                        'lead_id': each['lead_id'],
                        'action': action,
                        'emp_id': each['employee_id']
                    }
                    UserDA().create_emp_lead_mapping_log(log_data)
                    result['message'] = "Mapping Succesfull"
            else:
                result['message'] = "Nothing to change"


        except Exception as err:
            result["error"] = settings.ERROR_MSG['application_error']\
                .format(str(err), self.__log.error(self.__exception.get_exception()))
            result['status'] = 450
        return result

    def __is_employee_lead_mapping_access(self, user_id):
        is_access = False
        permitted = self.__utility.is_permitted(user_id, 'can_create_emp_project_mapping')
        if permitted:
            is_access = True
        return is_access

    def is_exist_active_mapping(self, emp_id,lead_id):
        mapping = UserDA().get_emp_lead_mapping_by_emp_id_and_lead_id(emp_id, lead_id)
        if mapping:
            return True
        return False
