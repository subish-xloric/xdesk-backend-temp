# this url file is created for mobile version v1
from django.urls import re_path as url
from django.contrib import admin
from django.urls import path

from pTracker.api.projects.views import  ProjectActivityView_V1
from pTracker.api.projects.views import  ProjectModuleView_V1
from pTracker.api.projects.views import  ProjectView_V1
from pTracker.api.projects.views import VersionExpiredView
from pTracker.api.projects.views import ProjectActivityAdminListView, ProjectActivityAdminDetailView

urlpatterns = [
   path('activities/', ProjectActivityAdminListView.as_view(), name='activities_v1'),
   path('activities/<int:row_id>/', ProjectActivityAdminDetailView.as_view(), name='activity_v1'),

   path('get-activities/', ProjectActivityView_V1.as_view(), name='get_activities_v1'),
   path('get-modules/<int:project_id>/', ProjectModuleView_V1.as_view(), name='get_modules_v1'),
   path('get-projects/', ProjectView_V1.as_view(), name='get_projects_v1')

   #  path('get-activities/', VersionExpiredView.as_view(), name='get_activities_v1'),
   # path('get-modules/<int:project_id>/', VersionExpiredView.as_view(), name='get_modules_v1'),
   # path('get-projects/', VersionExpiredView.as_view(), name='get_projects_v1')
]