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


class ProjectBL():

    def __init__(self):
        self.__logs = Logs()
        self.__exception = ExceptionHandler()
        self.__utility = Utility()

    def get_all_project_activity(self):
        activity_list = []

        activities = ProjectDA().get_all_project_activity()
        if activities:
            for activity in activities:
                activity_list.append({"id": activity.activity_id, "name": activity.name})
        return activity_list

    def get_all_projects_by_user(self, user_id):
        project_list = []
        obj_project = ProjectDA()
        project_dict = {}

        projects = obj_project.get_all_projects()
        if projects:
            for project in projects:
                project_dict[project.project_id] = project

        user_projects = obj_project.get_project_user_mapping(user_id)
        if user_projects:
            for user_project in user_projects:
                project = project_dict.get(user_project.project_id, None)
                if project:
                    project_list.append({
                        "id": project.project_id,
                        "name": project.name,
                        "is_billable": project.is_billable
                    })
        if not project_list:
            project_list = [{"error": "No active project found !!!", "status": 499}]
        return project_list


    def get_all_active_modules_by_project(self, project_id, user_id):
        module_list = []
        obj_project = ProjectDA()
        role_id, role_name = UserDA().get_user_role_by_id(user_id)
        if role_id in (1, 2, 3):
            is_access = True
        else:
            is_access = obj_project.is_project_accessible(project_id, user_id)
        if not is_access:
            module_list = [{"error": "Not accessible !!!", "status": 403}]
            return module_list

        modules = obj_project.get_all_active_modules_by_project(project_id)
        if modules:
            for module in modules:
                module_list.append({
                    "id": module.module_id,
                    "name": module.name,
                    "project_id": module.project_id
                })
        if not module_list:
            module_list = [{"error": "No active modules found !!!", "status": 200}]
        return module_list

    def create_or_update_project_module(self, request):
        result = {"error": "", "success": ""}
        obj_project = ProjectDA()
        try:
            data = request.data
            #role_id = request.role_id
            role_id, role_name = UserDA().get_user_role_by_id(request.user.id)
            is_update = False
            module_id = data.get('module_id', 0)
            if module_id:
                is_update = True

            project_id = data.get('project_id', 0)
            created_by = request.user.id
            if not obj_project.is_project_lead(project_id, created_by):
                if role_id > 3:
                    result["error"] = "You have no permission to add project module."
                    return [result]

            dto = new_dto()
            dto.project_id = project_id
            dto.name = data.get('name', 0)
            dto.description = data.get('description', None)
            dto.created_by = created_by
            dto.start_date = datetime.now()
            if obj_project.is_project_module_exist(project_id, dto.name, module_id):
                result["error"] = "Module is already exists under the project."
                return [result]

            if module_id:
                dto.module_id = module_id
                obj_project.update_project_module(dto)
            else:
                obj_project.create_project_module(dto)

            msg = "Module created sucessfully."
            if is_update:
                msg = "Module updated sucessfully."
            result["success"] = msg
            return [result]

        except Exception as err:
            result["error"] = str(err)
            return [result]

    def delete_project_module(self, request, module_id):
        result = {"error": "", "success": ""}
        obj_project = ProjectDA()
        try:
            role_id, role_name = UserDA().get_user_role_by_id(request.user.id)
            obj_module = obj_project.get_project_module(module_id)
            if not obj_module:
                result["error"] = "Invalid project module."
                return [result]
            project_id = obj_module.project_id
            deleted_by = request.user.id
            if not obj_project.is_project_lead(project_id, deleted_by):
                if role_id > 3:
                    result["error"] = "You have no permission to delete this project module."
                    return [result]
            obj_project.delete_project_module(module_id, deleted_by)
            msg = "Module deleted sucessfully."
            result["success"] = msg
            return [result]
        except Exception as err:
            result["error"] = str(err)
            return [result]

    def get_all_projects(self):
        project_list = []
        obj_project = ProjectDA()

        projects = obj_project.get_all_projects()
        if projects:
            for project in projects:
                project_list.append({
                    "id": project.project_id,
                    "name": project.name,
                    "is_billable": project.is_billable
                })
        if not project_list:
            project_list = [{"error": "No active project found !!!", "status": 499}]
        return project_list


    def get_members_by_project_id(self,request):
        result = {'error': '',
                'members': [],
                'employees_pool':[]
                }
        members_list = []
        employee_pool_list = []
        try:
            project_id = request['project_id']
            team_members = ProjectDA().get_all_members_by_project(project_id)
            all_active_users = UserDA().get_all_active_users()
            for user in all_active_users:
                temp = {}
                try: #if removed from user table before removing from project
                    member = team_members.get(user_id = user.id)
                    temp['name'] = user.first_name + ' ' + user.last_name
                    temp['id'] = user.id
                    temp['is_lead'] = member.is_lead
                    temp['project_id'] = project_id
                    members_list.append(temp)
                except:
                    temp['name'] = user.first_name + ' ' + user.last_name
                    temp['id'] = user.id
                    temp['is_lead'] = 0 # in case of new  employee
                    temp['project_id'] = project_id
                    employee_pool_list.append(temp)
            result['members'] = members_list
            result['employees_pool'] = employee_pool_list
        except Exception as error:
            result["error"] = settings.ERROR_MSG['application_error']\
                .format(error, self.__logs.error(self.__exception.get_exception()))
        return result

    def create_emp_project_mapping(self, user_id, request):
        result = {
            "error": '',
            "success": '',
            "status" : 200
        }
        try:
            permission = self.__is_employee_project_mapping_access(user_id)
            if not permission:
                result['error'] = settings.ERROR_MSG['no_permission']
                result['status'] = 403
                return result

            map_data = request.data
            temp = []
            for n, i in enumerate(map_data):
                next_dicts = map_data[n + 1:]
                for each in next_dicts:
                    if i['project_id'] == each['project_id'] and i['employee_id'] == each['employee_id']:
                        if i['emp_pool_dir'] != each['emp_pool_dir'] :
                            temp.append(i)
                            temp.append(each)
            for each in temp:
                if each in map_data:
                    map_data.remove(each)
            if map_data:
                for each in map_data:
                    #TODO project is not using anywhere need a approve to remove this
                    project = ProjectDA().get_project_by_id(each['project_id'])
                    if each['is_lead']:
                        filter_criteria = {
                            'project_id':each['project_id'],
                            'is_lead':1    
                        }
                        ProjectDA().update_project_emp_mapping_by_filter( filter_criteria, project_emp_dict={'is_lead': 0})
                        
                    if (each['emp_pool_dir'] == 'OUT'):
                        is_already_exist = self.is_exist_active_project_mapping(
                            each['employee_id'], each['project_id'])
                        if is_already_exist and not each['is_lead']:
                            result['error'] = 'mapping alredy done'
                            return result
                        elif each['is_lead'] and is_already_exist:
                            project_emp_dict={
                                'is_lead': each['is_lead']
                            }
                            filter_criteria = {
                            'user_id':each['employee_id'],
                            'project_id':each['project_id'],
                            }
                            ProjectDA().update_project_emp_mapping_by_filter(filter_criteria, project_emp_dict)
                            result['message'] = "Employee Project Mapping Updated"
                            if each['is_lead']:
                                continue
                        ProjectDA().create_project_employee_mapping(
                            each['project_id'], each['employee_id'], each['is_lead'])
                        log_data = {
                            'project_id': each['project_id'],
                            'user_id': each['employee_id'],
                            'join_date': date.today()
                        }
                        ProjectDA().create_emp_project_mapping_log(log_data)
                        result['message'] = "Employee Project Mapping Created"

                    mapping_obj = ProjectDA().\
                        get_project_mapping_by_employee_id_and_project_id\
                            (each['employee_id'], each['project_id'])

                    if (each['emp_pool_dir'] == 'IN'):
                       log_data = {'release_date': date.today()}
                       ProjectDA().update_emp_project_mapping_log(
                           log_data, each['employee_id'], each['project_id'])
                       ProjectDA().delete_emp_project_mapping(
                           mapping_obj[0].mapping_id)
                       result['message'] = "Employee Project Mapping Updated"
            else:
                result['error'] = "Nothing To Change"
        except Exception as error:
            result["error"] = settings.ERROR_MSG['application_error']\
                .format(error, self.__logs.error(self.__exception.get_exception()))
            result['status'] = 450
        return result

    def __is_employee_project_mapping_access(self, user_id):
        is_access = False
        permitted = self.__utility.is_permitted(user_id, 'can_create_emp_project_mapping')
        if permitted:
            is_access = True
        return is_access

    def is_exist_active_project_mapping(self, employee_id, project_id):
        mapping = ProjectDA().get_project_mapping_by_employee_id_and_project_id(
            employee_id, project_id)
        if mapping:
            return True
        return False
