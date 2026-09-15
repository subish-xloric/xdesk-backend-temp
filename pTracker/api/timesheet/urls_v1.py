# this url file is created for mobile version v1
from django.urls import re_path as url
from django.contrib import admin
from django.urls import path

from pTracker.api.timesheet.views import MyTimeSheetList_V1
from pTracker.api.timesheet.views import TimeSheetApprove_V1
from pTracker.api.timesheet.views import TimeSheetDateValid_V1
from pTracker.api.timesheet.views import TimeSheetList_V1
from pTracker.api.timesheet.views import TeamTimeSheetList_V1
from pTracker.api.timesheet.views import TimeSheetDetail_V1
from pTracker.api.timesheet.views import VersionExpiredView
from pTracker.api.timesheet.views import CreateTimesheetArchive


urlpatterns = [
    path('my_time_sheets/<str:year>/<str:month>/', MyTimeSheetList_V1.as_view(), name="my_time_sheet_list_v1"),
    path('get-timesheets-of-month/<int:emp_id>/<str:year>/<str:month>/', TeamTimeSheetList_V1.as_view(), name="my_time_sheet_list_v1"),
    path('get-timesheet-details/<int:timesheet_id>/', TimeSheetDetail_V1.as_view(), name='time_sheet_detail_v1'),
    path('my_timesheet_list/', TimeSheetList_V1.as_view(), name="time_sheet_list"),
    path('validate-date/<str:date>/', TimeSheetDateValid_V1.as_view(), name='timesheet_date_valid_v1'),
    path('verify-timesheet/', TimeSheetApprove_V1.as_view(), name="time_sheet_approve_v1"),
    path('add-timesheet/', TimeSheetDetail_V1.as_view(), name="time_sheet_add"),
    

    

#     path('my_time_sheets/<str:year>/<str:month>/', VersionExpiredView.as_view(), name="my_time_sheet_list_v1"),
#     path('get-timesheets-of-month/<int:emp_id>/<str:year>/<str:month>/', VersionExpiredView.as_view(), name="my_time_sheet_list_v1"),
#     path('get-timesheet-details/<int:timesheet_id>/', VersionExpiredView.as_view(), name='time_sheet_detail_v1'),
#     path('my_timesheet_list/', VersionExpiredView.as_view(), name="time_sheet_list"),
#     path('validate-date/<str:date>/', VersionExpiredView.as_view(), name='timesheet_date_valid_v1'),
#     path('verify-timesheet/', VersionExpiredView.as_view(), name="time_sheet_approve_v1"),
#     path('add-timesheet/', VersionExpiredView.as_view(), name="time_sheet_add"),
]