from django.urls import re_path as url
from django.contrib import admin
from django.urls import path


from pTracker.api.timesheet.views import CreateTimesheetArchive, TimeSheetDetail, TimesheetArchiveList
from pTracker.api.timesheet.views import EmployeeTimeSheetDetail
from pTracker.api.timesheet.views import TimeSheetList
from pTracker.api.timesheet.views import TimeSheetDateValid
from pTracker.api.timesheet.views import MyTimeSheetList
from pTracker.api.timesheet.views import TeamTimeSheetList
from pTracker.api.timesheet.views import TimeSheetApprove
from pTracker.api.timesheet.views import TimesheetSummary
from pTracker.api.timesheet.views import TimesheetDetailByEmployee
from pTracker.api.timesheet.views import TimesheetDPU
from pTracker.api.timesheet.views import TimesheetMissingAlert
from pTracker.api.timesheet.views import RestoreTimesheetFromArchives
from pTracker.api.timesheet.views import ExcludeTsEmployees


urlpatterns = [
    path('add/', TimeSheetDetail.as_view(), name="time_sheet_add"),
    path('update/', TimeSheetDetail.as_view(), name="time_sheet_add"),
    path('list/', TimeSheetList.as_view(), name="time_sheet_list"),
    path('my_time_sheets/<str:start_date>/<str:end_date>/<str:status>/', MyTimeSheetList.as_view(), name="my_time_sheet_list"),
    path('team_time_sheets/<int:emp_id>/<str:start_date>/<str:end_date>/<str:status>/', TeamTimeSheetList.as_view(), name="my_time_sheet_list"),

    path('detail/<int:time_sheet_id>/', TimeSheetDetail.as_view(), name='time_sheet_detail'),
    path('emp_detail/<int:time_sheet_id>/<int:emp_id>/', EmployeeTimeSheetDetail.as_view(), name='emp_time_sheet_detail'),
    path('date-valid/<str:time_sheet_date>/<int:time_sheet_id>/', TimeSheetDateValid.as_view(), name='timesheet_date_valid-update'),
    path('date-valid/<str:time_sheet_date>/', TimeSheetDateValid.as_view(), name='timesheet_date_valid'),
    path('approve/', TimeSheetApprove.as_view(), name="time_sheet_approve"),

    #timesheet report
    path('timesheet-summary/<str:start_date>/<str:end_date>/', TimesheetSummary.as_view(), name="timesheet_summary"),
    path('timesheet-detail-by-employee/<int:emp_id>/<str:start_date>/<str:end_date>/', TimesheetDetailByEmployee.as_view(), name="timesheet_detail_by_employee"),
    path('timesheet-dpu/<str:start_date>/<str:project_id>/', TimesheetDPU.as_view(), name="timesheet_dpu"),
    path('get-timesheet-missing-alert/', TimesheetMissingAlert.as_view(), name="timesheet_missing_alert"),

    path('create-timesheet-archive/', CreateTimesheetArchive.as_view(), name="create_timesheet_archive"),
    path('get-all-timesheet-archives/', TimesheetArchiveList.as_view(), name="get_all_timesheet_archives"),
    path('restore-timesheet-from-archives/', RestoreTimesheetFromArchives.as_view(), name="restore_timesheet_from_archives"),
    path('exclude-timesheet-employee/', ExcludeTsEmployees.as_view(), name="'exclude_timesheet_employee"),
]