from django.urls import re_path as url
from django.contrib import admin
from django.urls import path


from pTracker.api.projects.views import  ProjectActivityView
from pTracker.api.projects.views import  ProjectView
from pTracker.api.projects.views import  ProjectModuleView
from pTracker.api.projects.views import  ProjectModuleDeleteView
from pTracker.api.projects.views import  EmployeesByProjectId
from pTracker.api.projects.views import  EmployeesProjectMapping

#project create biz 
from pTracker.api.projects.views import  GetAllProjectList
from pTracker.api.projects.views import  CreateProject
from pTracker.api.projects.views import  UpdateProject
from pTracker.api.projects.views import  DeleteProject
from pTracker.api.projects.views import  GetProjectDropDownParams


urlpatterns = [
    path('activities/', ProjectActivityView.as_view(), name="activities"),
    path('list/', ProjectView.as_view(), name="list"),
    #path('list/', ProjectView.as_view(), name="list"),
    path('module/<int:project_id>/', ProjectModuleView.as_view(), name='module'),
    path('create-module/', ProjectModuleView.as_view(), name='create_module'),
    path('delete-module/<int:module_id>/', ProjectModuleDeleteView.as_view(), name='delete_module'),
    path('employees-by-project-id', EmployeesByProjectId.as_view(), name='employees_by_project_id'),
    path('emp-project-mapping/', EmployeesProjectMapping.as_view(), name='emp_project_mapping'),
    
    
    #project create biz urls
    path('get-all-project-list/', GetAllProjectList.as_view(), name='get_all_project_list'),
    path('create-project/', CreateProject.as_view(), name='create_project'),
    path('update-project/<int:project_id>/', UpdateProject.as_view(), name='update_project'),
    path('delete-project/<int:project_id>/', DeleteProject.as_view(), name='delete_project'),
    path('get-project-drop-down-params/', GetProjectDropDownParams.as_view(), name='get_project_drop_down_params'),

]