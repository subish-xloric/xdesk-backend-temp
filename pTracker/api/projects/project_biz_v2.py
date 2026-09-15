from  datetime import datetime, date, timedelta
from django.utils.safestring import mark_safe
import re
from bs4 import BeautifulSoup

from django.conf import settings
from types import SimpleNamespace

from django.db.models import base
from django.db import  transaction

from pTracker.common.utility import Utility
from pTracker.dataaccess.ptracker_access.project_da import  ProjectDA
from pTracker.dataaccess.ptracker_access.user_da import UserDA

from pTracker.common.logs import Logs
from pTracker.common.exception_handler import ExceptionHandler

def new_dto():
    dto = SimpleNamespace()
    return dto


class ProjectCreateBL():
    
    def __init__(self):
        self.__logs = Logs()
        self.__exception = ExceptionHandler()
        self.__utility = Utility()


    def get_all_projects(self, request):
        response = {"status": 200, "projects": [], "project_accounts": [], "success": False, "error": ""}
        
        try:
            project_account_dict = {}
            project_dict = {}
            user_id = request.user.id
            is_permitted = True

            companies = settings.ORGANIZATION
            
            # role_id, role_name = UserDA().get_user_role_by_id(user_id)
            # is_manager = self.is_manager(role_id)

            # if not is_manager:
            #     response["error"] = settings.ERROR_MSG.get("access_denied")
            #     response["status"] = 403
            #     return response
            
            # if is_manager:
            #     projects = ProjectDA().get_all_projects()
            # else:
            #     projects = ProjectDA().get_all_user_projects(user_id)
            
            project_accounts = ProjectDA().get_all_project_accounts()
            project_account_list = []
            if project_accounts:
                for each_account in project_accounts:
                    project_account_dict[each_account.account_id] = {
                    'account_name': each_account.name
                    }
                    project_account_list.append({
                        'account_id': each_account.account_id,
                        'account_name': each_account.name,
                    })
            
            response['company_list'] = [ {'org_id': org_id, 'org_name': org_name} for org_id, org_name in settings.ORGANIZATION.items()]
            response['project_account_list'] = project_account_list
            projects = ProjectDA().get_all_projects()
            if projects:
                for project in projects:
                    project_dict = {
                        "project_id":project.project_id,
                        "project_type_id":project.project_type_id,
                        "project_name":project.name,
                        "project_account_name":project_account_dict.get(project.account_id,"-")['account_name'],
                        "project_account_id":project.account_id,
                        "project_desc":project.description,
                        "company_name":companies.get(project.company_id, ''),
                        "company_id":project.company_id,
                        "billable":project.is_billable,
                        # "start_date":project.start_date if project.start_date else "",
                        # "end_date":project.end_date if project.end_date else "",
                        "start_date":datetime.strftime(project.start_date, '%d/%m/%Y') if project.start_date else "",
                        "end_date":datetime.strftime(project.end_date, '%d/%m/%Y') if project.end_date else "",
                    }
                    response["projects"].append(project_dict)
                
            response["success"] = True
            
        except Exception as err:
            response['success'] = False
            response["error"] = settings.ERROR_MSG['application_error'].format(
                str(err), self.__logs.error(self.__exception.get_exception())
            )
            response["status"] = 499
        return response
    
    
    def create_project(self, request):
        response = {"status": 200, "projects": [], "success": False, "error": ""}
        
        try:
            project_data = {}
            request_data = request.data
            user_id = request.user.id
            is_permitted = True
            
            #TODO is_manager need to be added
            
            role_id, role_name = UserDA().get_user_role_by_id(user_id)
            is_manager = self.is_manager(role_id)

            # if not is_manager:
            #     response["error"] = settings.ERROR_MSG.get("access_denied")
            #     response["status"] = 403
            #     return response
            
            # if is_manager:
            #     projects = ProjectDA().get_all_projects()
            # else:
            #     projects = ProjectDA().get_all_user_projects(user_id)

            if role_id > 4 or not is_manager:
                response["error"] = settings.ERROR_MSG.get("access_denied")
                response["status"] = 403
                return response
            
            try:
                company_id = int(request_data.get('company'))

                if company_id not in settings.ORGANIZATION.keys():
                    response['error'] = 'Invalid company selected'
                    response["status"] = 499
                    return response
            except:
                response['error'] = 'Invalid company selected'
                response["status"] = 499
                return response

            try:
                project_account = int(request_data.get('project_account'))

                existing_project_accounts = ProjectDA().get_all_project_account_ids()
                if project_account not in existing_project_accounts:
                    response['error'] = 'Invalid project account selected'
                    response["status"] = 499
                    return response
            except:
                response['error'] = 'Invalid project account selected'
                response["status"] = 499
                return response


            name = request_data.get('name')
            name_error, name = self.string_validator(name, 'Project Name')
            if name_error:
                response['error'] = name_error
                response["status"] = 499
                return response
            
            description = request_data.get('description')
            if description and len(description.strip()) > 0:
                description_error, description = self.string_validator(description, 'Project Description')
                if description_error:
                    response['error'] = description_error
                    response["status"] = 499
                    return response

            try:
                is_billable = int(request_data.get('is_billable')) if request_data.get('is_billable') not in ['null', None] else 0
                if is_billable not in [0,1]:
                    response['error'] = 'Invalid input found (Billable)'
                    response["status"] = 499
                    return response

            except:
                response['error'] = 'Invalid input found (Billable)'
                response["status"] = 499
                return response
            
            start_date = request_data.get('start_date', None) if request_data.get('start_date', None) not in ['null', None, ''] else None
            # if start_date:
            #     try:
            #         start_date = self.convert_to_date(start_date)
            #     except:
            #         response['error'] = 'Invalid date passed'
            #         response["status"] = 499
            #         return response

            end_date = request_data.get('end_date', None) if request_data.get('end_date', None) not in ['null', None, ''] else None
            # if end_date:
            #     try:
            #         end_date = self.convert_to_date(end_date)
            #     except:
            #         response['error'] = 'Invalid date passed'
            #         response["status"] = 499
            #         return response

            date_response = self.validate_progress_dates(start_date=start_date,end_date=end_date)
            if date_response["error"]:
                return date_response
            start_date = date_response['start_date']
            end_date = date_response['end_date']
            
            project_data = {
                'company_id': company_id,
                'account_id': project_account,
                'start_date': start_date,
                'end_date': end_date,
                'name': name,
                'description': description,
                'is_billable': is_billable,
                'created_by': user_id,
            }
            
            with transaction.atomic():
                project = ProjectDA().create_project_data(project_data)
                if not project:
                    response['error'] = 'Project create unsuccessful'
                    response["status"] = 499
                    return response
                project_name = project.name
                
            response["success"] = True
            response['message'] = f'{project_name} project has been created successfully.'
            
        except Exception as err:
            response['success'] = False
            response["error"] = settings.ERROR_MSG['application_error'].format(
                str(err), self.__logs.error(self.__exception.get_exception())
            )
            response["status"] = 499
        return response
    
    
    def update_project(self, request, project_id):
        response = {"status": 200, "projects": [], "success": False, "error": ""}
        
        try:
            project_data = {}
            request_data = request.data
            user_id = request.user.id
            is_permitted = True
            
            role_id, role_name = UserDA().get_user_role_by_id(user_id)
            is_manager = self.is_manager(role_id)
            
            #TODO is_manager need to be added

            # if not is_manager:
            #     response["error"] = settings.ERROR_MSG.get("access_denied")
            #     response["status"] = 403
            #     return response
            
            # if is_manager:
            #     projects = ProjectDA().get_all_projects()
            # else:
            #     projects = ProjectDA().get_all_user_projects(user_id)

            is_part_of_project = ProjectDA().is_project_accessible(user_id, project_id)
            if not is_part_of_project and not is_manager:
                response["error"] = settings.ERROR_MSG.get("access_denied")
                response["status"] = 403
                return response
            
            try:
                project_obj = ProjectDA().get_project_by_id(project_id)
                old_project_data = {
                'company_id': project_obj.company_id,
                'account_id': project_obj.account_id,
                'start_date': project_obj.start_date,
                'end_date': project_obj.end_date,
                'name': project_obj.name,
                'project_type_id': project_obj.project_type_id,
                'description': project_obj.description,
                'is_billable': project_obj.is_billable,
                'created_by': project_obj.created_by,
                }
            except:
                response["error"] = 'Invalid project id is passed'
                response["status"] = 403
                return response
            
            is_part_of_project = ProjectDA().is_project_accessible(user_id, project_id)
            if not is_part_of_project and not is_manager:
                response["error"] = settings.ERROR_MSG.get("access_denied")
                response["status"] = 403
                return response
            
            try:
                company_id = int(request_data.get('company'))

                if company_id not in settings.ORGANIZATION.keys():
                    response['error'] = 'Invalid company selected'
                    response["status"] = 499
                    return response
            except:
                response['error'] = 'Invalid company selected'
                response["status"] = 499
                return response
            
            name = request_data.get('name')
            name_error, name = self.string_validator(name, 'Project Name')
            if name_error:
                response['error'] = name_error
                response["status"] = 499
                return response
            
            description = request_data.get('description')
            if description and len(description.strip()) > 0:
                description_error, description = self.string_validator(description, 'Project Description')
                if description_error:
                    response['error'] = description_error
                    response["status"] = 499
                    return response
            
            try:
                project_account = int(request_data.get('project_account'))

                existing_project_accounts = ProjectDA().get_all_project_account_ids()
                if project_account not in existing_project_accounts:
                    response['error'] = 'Invalid project account selected'
                    response["status"] = 499
                    return response
            except:
                response['error'] = 'Invalid project account selected'
                response["status"] = 499
                return response

            try:
                is_billable = int(request_data.get('is_billable'))
                if is_billable not in [0,1]:
                    response['error'] = 'Invalid input found (Billable)'
                    response["status"] = 499
                    return response

            except:
                response['error'] = 'Invalid input found (Billable)'
                response["status"] = 499
                return response
            
            start_date = request_data.get('start_date', None) if request_data.get('start_date', None) not in ['null', None, ''] else None
            # if start_date:
            #     try:
            #         start_date = self.convert_to_date(start_date)
            #     except:
            #         response['error'] = 'Invalid date passed'
            #         response["status"] = 499
            #         return response

            end_date = request_data.get('end_date', None) if request_data.get('end_date', None) not in ['null', None, ''] else None
            # if end_date:
            #     try:
            #         end_date = self.convert_to_date(end_date)
            #     except:
            #         response['error'] = 'Invalid date passed'
            #         response["status"] = 499
            #         return response
            
            date_response = self.validate_progress_dates(start_date=start_date,end_date=end_date)
            if date_response["error"]:
                return date_response
            start_date = date_response['start_date']
            end_date = date_response['end_date']
            
            project_data = {
                'company_id': company_id,
                'account_id': project_account,
                'start_date': start_date,
                'end_date': end_date,
                'name': name,
                'project_type_id': '1',
                'description': description,
                'is_billable': is_billable,
                'created_by': user_id,
            }
            
            no_changes = project_data == old_project_data
            if no_changes:
                response['error'] = 'Why did you update ? I can\'t see any changes'
                response['status'] = 499
                return response
            
            with transaction.atomic():
                project = ProjectDA().update_project_data(project_id, project_data)
                if not project:
                    response['error'] = f'Project {project_obj.name} update unsuccessful'
                    response["status"] = 499
                    return response
                project_name = name
                
            response["success"] = True
            response['message'] = f'Project {project_obj.name} has been updated successfully.'
            
        except Exception as err:
            response['success'] = False
            response["error"] = settings.ERROR_MSG['application_error'].format(
                str(err), self.__logs.error(self.__exception.get_exception())
            )
            response["status"] = 499
        return response

    
    def delete_project(self, request, project_id):
        response = {"status": False, "projects": [], "success": False, "error": ""}
        
        try:
            project_data = {}
            request_data = request.data
            user_id = request.user.id
            is_permitted = True
            
            role_id, role_name = UserDA().get_user_role_by_id(user_id)
            is_manager = self.is_manager(role_id)

            try:
                project_obj = ProjectDA().get_project_by_id(project_id)
                project_name = project_obj.name
            except:
                response["error"] = 'Invalid project id is passed'
                response["status"] = 403
                return response
            
            #TODO is_manager need to be added

            # if not is_manager:
            #     response["error"] = settings.ERROR_MSG.get("access_denied")
            #     response["status"] = 403
            #     return response
            
            # if is_manager:
            #     projects = ProjectDA().get_all_projects()
            # else:
            #     projects = ProjectDA().get_all_user_projects(user_id)
            
            is_part_of_project = ProjectDA().is_project_accessible(user_id, project_id)
            if not is_part_of_project and not is_manager:
                response["error"] = settings.ERROR_MSG.get("access_denied")
                response["status"] = 403
                return response
            
            project_data = {
                'is_deleted': 1,
                'deleted_by': user_id,
            }

            module_ids = ProjectDA().get_all_active_module_ids_by_project(project_id)
            
            with transaction.atomic():
                project = ProjectDA().update_project_data(project_id, project_data)
                if not project:
                    response['error'] = 'Project deletion unsuccessful'
                    response["status"] = 499
                    return response
                
                if module_ids:
                    is_modules_deleted = ProjectDA().delete_project_modules(module_ids, user_id)
                    if not is_modules_deleted:
                        response['error'] = f'Project Module deletion unsuccessful'
                        response["status"] = 499
                        return response
                
            response["success"] = True
            response['message'] = f'Project {project_name} has been deleted successfully.'
            
        except Exception as err:
            response['success'] = False
            response["error"] = settings.ERROR_MSG['application_error'].format(
                str(err), self.__logs.error(self.__exception.get_exception())
            )
            response["status"] = 499
        return response
    
    
    def get_project_drop_down_params(self, request):
        response = {"status": 200, "project_accounts": [], "success": False, "error": ""}
        
        try:
            user_id = request.user.id
            is_permitted = True
            role_id, role_name = UserDA().get_user_role_by_id(user_id)
            is_manager = self.is_manager(role_id)
            #TODO is_manager need to be added

            # if not is_manager:
            #     response["error"] = settings.ERROR_MSG.get("access_denied")
            #     response["status"] = 403
            #     return response
            
            # if is_manager:
            #     projects = ProjectDA().get_all_projects()
            # else:
            #     projects = ProjectDA().get_all_user_projects(user_id)
            
            project_account_dict = {}
            project_accounts = ProjectDA().get_all_project_accounts()
            if project_accounts:
                for each_account in project_accounts:
                    project_account_dict[each_account.account_id] = {
                    'account_id': each_account.account_id,
                    'account_name': each_account.name
                    }
                response["project_accounts"] = list(project_account_dict.values())
                response['success'] = True
        
        except Exception as err:
            response['success'] = False
            response["error"] = settings.ERROR_MSG['application_error'].format(
                str(err), self.__logs.error(self.__exception.get_exception())
            )
            response["status"] = 499
        return response
    
    
    def is_manager(self, role_id):
        is_manager = False
        if role_id in (1, '1', 2, '2', 3, '3'):
            is_manager = True
        return is_manager
    
    
    def validate_progress_dates(self,created_date=None, start_date=None, end_date=None):
        response = {"error": None, "status": 200, "success": True}
        try:
            current_date = datetime.now().date()
            try:
                start_date = self.convert_to_date(start_date)
                end_date = self.convert_to_date(end_date)
            except Exception as e:
                response['error'] = 'Invalid dates'
                response["status"] = 499
                response["success"] = False
                return response

            if start_date:
                if start_date > current_date:
                    response['error'] = 'The start date should be the same as or less than the current date.'
                    response["status"] = 499
                    response["success"] = False
                    return response
            if end_date:
                if (end_date < current_date):
                    response['error'] = 'The end date should be the same as or greater than the current date.'
                    response["status"] = 499
                    response["success"] = False
                    return response

            if start_date and end_date:
                if end_date < start_date:
                    response['error'] = 'The end date should be the same as or later than the start date.'
                    response["status"] = 499
                    response["success"] = False
                    return response
            response['start_date'] = start_date
            response['end_date'] = end_date
        except Exception as err:
            response["error"] = err
        return response
    
    def convert_to_date(self,date_str):
        return datetime.strptime(date_str, "%d/%m/%Y").date() if date_str else None
    


    def string_validator(self, message, field_name):
        message = mark_safe(message)
        full_message = message
        message = BeautifulSoup(message, 'html.parser')
        message = message.text
        message = message.lstrip().rstrip()


        #The following validator will validate the following scenarios
        # 1) it should not accept numbers only text data
        # 2) it should not accept space only text data
        # 3) it should accept text data having numbers and letters
        # 4) it should accept letters only text data
        # 5) it should have minimum length of 4
        # 6) it should not accept special characters only text data
        # 7) it should accept text data having special character and letters, if there is special characters then there must be a letter
        # 8) It should accept letters only text data with spaces in beggining and end, or beggining or end
        # 9) It should also accept spaces in between words and letters
        # 10) It should accept letters only text data with spaces in beggining and end, or beggining or end while spaces in between.

        message_validator = r'^(?=.*[a-zA-Z])[a-zA-Z0-9!@#$%^&*()-_+=|\\[\]{};:\'",.<>/?\s]*[a-zA-Z]+[a-zA-Z0-9!@#$%^&*()-_+=|\\[\]{};:\'",.<>/?\s]*$'
        non_ascii_validator = r'[^\x00-\x7F]'
        error = f'Invalid "{field_name}" field. Your may have triggered one or more of the following issues: it contains only numbers, only special characters, is empty, is shorter than 3 characters, or includes non-ASCII or non-UTF characters'

        if re.match(non_ascii_validator, message):
            return error, full_message
        elif not re.match(message_validator, message) or len(message) < 3:
            return error, full_message
        else:
            return None, full_message
