
from django.urls import re_path as url
from django.contrib import admin
from django.urls import path


from pTracker.api.resource.views import  GetProjectAccountMappings
from pTracker.api.resource.views import  GetAllProjectAccounts



urlpatterns = [
    path('get-project-account-mappings/<str:year_and_month>/<int:map_status>/<int:billable>/<int:account>', GetProjectAccountMappings.as_view(), name="get_project_account_mappings"),
    path('get-all-project-accounts/', GetAllProjectAccounts.as_view(), name="get_all_project_accounts"),


]