from datetime import datetime
from django.conf import settings

from types import SimpleNamespace

from pTracker.dataaccess.ptracker_access.project_models import ProjectActivity
from pTracker.dataaccess.ptracker_access.project_models import Project
from pTracker.dataaccess.ptracker_access.project_models import ProjectEmployee
from pTracker.dataaccess.ptracker_access.project_models import ProjectModule
from pTracker.dataaccess.ptracker_access.project_models import ProjectEmployeeLog
# from pTracker.dataaccess.ptracker_access.project_models import ProjectModule
from pTracker.dataaccess.ptracker_access.project_models import ProjectAccount
from pTracker.dataaccess.ptracker_access.project_models import ProjectAccountEmpMapping
from pTracker.dataaccess.ptracker_access.project_models import ProjectAccountEmpMappingLog
from pTracker.dataaccess.ptracker_access.project_models import ProjectRepo
from pTracker.dataaccess.ptracker_access.project_models import ProjectRepoMapping
from pTracker.dataaccess.ptracker_access.project_models import ProjectRepoUserMapping



def new_dto():
    dto = SimpleNamespace()
    return dto


class ProjectDA():

    def __init__(self):
        pass

    def get_all_project_activity(self):
        objs = ProjectActivity.objects.filter(is_deleted=0).order_by('name')
        return objs

    def get_all_project_modules(self):
        objs = ProjectModule.objects.filter(is_deleted=0)
        return objs

    def get_project_module(self, module_id):
        try:
            objs = ProjectModule.objects.get(is_deleted=0, module_id=module_id)
        except:
            objs = None
        return objs

    def get_all_projects(self):
        objs = Project.objects.filter(is_deleted=0).order_by('name')
        return objs

    def get_project_user_mapping(self, user_id):
        objs = ProjectEmployee.objects.filter(user_id=user_id)
        return objs

    def get_project_leads_by_project_id(self, project_id):
        objs = ProjectEmployee.objects.filter(project_id=project_id, is_lead=1)
        return objs

    def is_project_accessible(self, project_id, user_id):
        objs = ProjectEmployee.objects.filter(user_id=user_id, project_id=project_id)
        if objs:
            return True
        else:
            return False

    def get_all_active_modules_by_project(self, project_id):
        objs = ProjectModule.objects.filter(project_id=project_id, is_deleted=0).order_by("name")
        return objs
    
    def get_all_active_module_ids_by_project(self, project_id):
        objs = ProjectModule.objects.filter(project_id=project_id, is_deleted=0).values_list('module_id', flat=True).order_by("name")
        return objs


    def get_all_project_ids_of_user(self, user_id):
        project_ids = ProjectEmployee.objects.filter(user_id=user_id).values_list('project_id', flat=True)
        return project_ids


    def get_project_employees_from_project_id(self, project_id):
        user_ids = ProjectEmployee.objects.filter(project_id=project_id).values_list('user_id', flat=True)
        return user_ids


    def create_project_module(self, dto):
        obj = ProjectModule(
            project_id=dto.project_id,
            name=dto.name,
            description=dto.description,
            created_by=dto.created_by,
            start_date=dto.start_date)
        obj.save()
        module_id = obj.module_id
        return module_id

    def update_project_module(self, dto):
        ProjectModule.objects.filter(module_id=dto.module_id)\
            .update(project_id=dto.project_id,
                    name=dto.name,
                    description=dto.description)
        return dto.module_id

    def delete_project_module(self, module_id, deleted_by):
        ProjectModule.objects.filter(module_id=module_id)\
            .update(is_deleted=1,
                    deleted_by=deleted_by,
                    end_date=None)
        return module_id
    
    def delete_project_module(self, module_id, deleted_by):
        ProjectModule.objects.filter(module_id=module_id)\
            .update(is_deleted=1,
                    deleted_by=deleted_by,
                    end_date=None)
        return module_id
    

    def delete_project_modules(self, module_ids, deleted_by):
        for module_id in module_ids:
            ProjectModule.objects.filter(module_id=module_id)\
                .update(is_deleted=1,
                        deleted_by=deleted_by,
                        end_date=None)
        
        return module_ids


    def is_project_lead(self, project_id, user_id):
        objs = ProjectEmployee.objects.filter(user_id=user_id, project_id=project_id)
        if objs:
            try:
                is_lead = int(objs[0].is_lead)
            except:
                is_lead = 0
        else:
            is_lead = 0
        return is_lead

    def is_project_module_exist(self, project_id, module_name, module_id=0):
        objs = ProjectModule.objects.filter(project_id=project_id, is_deleted=0, name=module_name)
        if module_id:
            objs = objs.exclude(module_id=module_id)

        return objs


    def get_all_project_ids(self):
        project_ids = Project.objects.filter(is_deleted=0).values_list('project_id', flat=True)
        return project_ids


    def get_all_project_modules_by_project_ids(self, project_ids):
        objs = ProjectModule.objects.filter(is_deleted=0, project_id__in=project_ids)
        return objs

    def create_project_employee_mapping(self, project_id, user_id, is_lead=0):
        obj = ProjectEmployee(
            project_id=project_id,
            user_id=user_id,
            is_lead=is_lead)
        obj.save()

    def get_all_members_by_project(self,project_id):
        return ProjectEmployee.objects.filter(project_id = project_id)

    def get_project_mapping_by_employee_id_and_project_id(self, employee_id, project_id):
        print(employee_id,project_id,"**********")
        return ProjectEmployee.objects.filter(project_id = project_id, user_id = employee_id)

    def get_project_by_id(self, project_id):
        try:
            return Project.objects.get(project_id=project_id,is_deleted=0)
        except:
            return None

    def delete_emp_project_mapping(self,mapping_id):
        return ProjectEmployee.objects.filter(mapping_id = mapping_id).delete()

    def create_emp_project_mapping_log(self, log_data):
        return ProjectEmployeeLog.objects.create(**log_data)

    def update_emp_project_mapping_log(self,log_data, employee_id, project_id):
        return ProjectEmployeeLog.objects.filter(user_id = employee_id, project_id = project_id).update(**log_data)

    def delete_employee_project_mappings_by_user_id(self, user_id):
        return ProjectEmployee.objects.filter(user_id = user_id).delete()

    def update_employee_project_mapping_log(self, user_id):
        return ProjectEmployeeLog.objects.filter(user_id =user_id, release_date= None).update(release_date = datetime.now().date())


    def get_all_project_accounts(self):
        return ProjectAccount.objects.filter(is_deleted = 0)
    
    def get_all_project_account_ids(self):
        return ProjectAccount.objects.values_list('account_id', flat=True).filter(is_deleted = 0)

    def get_all_mapped_users_by_billable_or_not(self,billable_or_not, account_id = 0):
        if account_id and billable_or_not:
            return ProjectAccountEmpMapping.objects.filter(is_billable = billable_or_not,end_date__isnull=True,account_id =account_id )
        elif account_id:
            return ProjectAccountEmpMapping.objects.filter(is_billable = billable_or_not,end_date__isnull=True,account_id =account_id )

        elif billable_or_not:
            return ProjectAccountEmpMapping.objects.filter(is_billable = billable_or_not,end_date__isnull=True )
        else:
            return ProjectAccountEmpMapping.objects.filter(end_date__isnull=True )

    def get_all_map_logs(self):
        return ProjectAccountEmpMappingLog.objects.all()


    def get_all_user_projects(self, user_id):
        projects = None
        employee_projects = ProjectEmployee.objects.filter(user_id=user_id).values_list('project_id')
        projects = Project.objects.filter(project_id__in=employee_projects, is_deleted=0)
        return projects


    def update_project_emp_mapping(self, employee_id, project_id, project_emp_dict):
        ProjectEmployee.objects.filter(user_id=employee_id, project_id=project_id).update(**project_emp_dict)

    def update_project_emp_mapping_by_emp_id(self, employee_id, project_emp_dict):
        ProjectEmployee.objects.filter(user_id=employee_id).update(**project_emp_dict)
    
    def update_project_emp_mapping_by_filter(self, filter_criteria, project_emp_dict):
        ProjectEmployee.objects.filter(**filter_criteria).update(**project_emp_dict)
    
    def create_project_data(self,data_dict):
        data = Project.objects.create(**data_dict)
        return data
    
    def update_project_data(self, project_id, project_data):
        return Project.objects.filter(project_id=project_id).update(**project_data)

    #The dict data filtering example filter_criteria['repo_project_id'] = project_id
    def get_all_project_repo_by_filter_criteria(self, filter_criteria):
        project_repo = None
        project_repo = ProjectRepo.objects.filter(**filter_criteria, is_deleted=0)#.order_by('repo_name')
        return project_repo
    
    def get_all_repo_mapping_by_filter_criteria(self, filter_criteria):
        repo_mapping = None
        repo_mapping = ProjectRepoMapping.objects.filter(**filter_criteria, is_deleted=0)
        return repo_mapping
    
    def get_project_repo_by_id(self, repo_id):        
        try:
            return ProjectRepo.objects.filter(repo_id=repo_id, is_deleted=0).first()
        except:
            return None
        
    def get_project_repo_mapping_by_repoid(self, repo_id):        
        try:
            return ProjectRepoMapping.objects.filter(repo_id=repo_id, is_deleted=0)
        except:
            return None
        

    def get_project_repo_user_mapping_by_repoid(self, user_id, repo_id):
        try:
            return ProjectRepoUserMapping.objects.filter(user_id=user_id, repo_id=repo_id, is_deleted=0).first()
        except:
            return None

        