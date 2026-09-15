from django.urls import re_path as url
from django.contrib import admin
from django.urls import path


from pTracker.api.attendance.views import MyRecordList
from pTracker.api.attendance.views import AttendanceDetailView
from pTracker.api.attendance.views import LeadMappingList
from pTracker.api.attendance.views import EmployeeAttendanceLogList
from pTracker.api.attendance.views import EmployeeAttendanceAverage
from pTracker.api.attendance.views import WebPunchCheck
from pTracker.api.attendance.views import WebPunch
from pTracker.api.attendance.views import UpcomingHolidays
from pTracker.api.attendance.views import WFHEmp
from pTracker.api.attendance.views import DashboardAverageHours
from pTracker.api.attendance.views import NotPunchListView

from pTracker.api.attendance.views import EmployeeWFHRequestListView
from pTracker.api.attendance.views import CreateWFHRequestView
from pTracker.api.attendance.views import UpdateWFHRequestView
from pTracker.api.attendance.views import WFHDateValidation
from pTracker.api.attendance.views import WFHRequestFilterByStatus
from pTracker.api.attendance.views import WFHMyRequestFilterByStatusAndMonth

from pTracker.api.attendance.views import GetAttendanceReport
from pTracker.api.attendance.views import GetMonthlyAttendanceReport
from pTracker.api.attendance.views import  GenerateExcelReport
from pTracker.api.attendance.views import  GetWorkFromHomeReport

from pTracker.api.attendance.views import AnuualWFHDetailView
from pTracker.api.attendance.views import AnnualWFHSummaryReport
from pTracker.api.attendance.views import WFHReportDropDowns

from pTracker.api.attendance.views import GetWorkFromHomeEmployee


urlpatterns = [
    path('my-records/<str:month_year>/', MyRecordList.as_view(), name='my_record_list'),
    path('get-lead-mapping/', LeadMappingList.as_view(), name='lead_mapping'),
    path('emp-att-logs/<str:month_year_empid>/', EmployeeAttendanceLogList.as_view(), name='emp_record_list'),
    path('emp-att-average/<str:month_year_empid>/', EmployeeAttendanceAverage.as_view(), name='avg'),
    path('web-punch-check/', WebPunchCheck.as_view(), name='webPunchCheck'),
    path('web-punch/', WebPunch.as_view(), name='webPunch'),
    path('upcoming-holidays/', UpcomingHolidays.as_view(), name='upcoming_holidays'),
    path('get-wfh-employees/<str:work_date>', WFHEmp.as_view(), name='get_wfh_employees'),
    path('dashboard-avg-hours/', DashboardAverageHours.as_view(), name='dashboard_avg_hours'),

    url(r'^get-all-wfh-requests/', EmployeeWFHRequestListView.as_view(), name='get_all_my_wfh_requests'),
    url(r'^create-wfh-request/', CreateWFHRequestView.as_view(), name='create_wfh_request'),
    url(r'^update-wfh-request/', UpdateWFHRequestView.as_view(), name='update_wfh_request'),
    url(r'get-attendance-details-by-date/', AttendanceDetailView.as_view(), name='get_attendance_details_by_date'),
    path('not-punch-list/<str:start_date>/<str:end_date>', NotPunchListView.as_view(), name='not_punch_list'),
    url(r'get-wfh-date-validation/', WFHDateValidation.as_view(), name='get-wfh-date-validation'),
    url(r'wfh-request-filter-by-status/', WFHRequestFilterByStatus.as_view(), name='wfh_request_filter_by_status'),
    url(r'wfh-my-request-filter-by-status-and-month/', WFHMyRequestFilterByStatusAndMonth.as_view(), name='wfh_my_request_filter_by_status_and_month'),

    path('get-attendance-report/<str:str_date>/<str:organization>/', GetAttendanceReport.as_view(), name='attendance_report'),
    path('get-monthly-attendance-report/<str:year>/<str:month>/<str:organization>/', GetMonthlyAttendanceReport.as_view(), name='attendance_monthly_report'),
    path('generate-excel-report/<str:year>/<str:month>/<str:organization>/', GenerateExcelReport.as_view(), name='generate_excel_report'),

    path('wfh-report-dropdowns/', WFHReportDropDowns.as_view(), name="wfh_report_dropdowns"),
    path('get-wfh-reports/', GetWorkFromHomeReport.as_view(), name='team_stats_v1'),
    path('annual-wfh-details/<int:emp_id>/<int:year>', AnuualWFHDetailView.as_view(), name="annual_wfh_details"),

    path('employee-wfh-list/', GetWorkFromHomeEmployee.as_view(), name='employee_wfh_list'),

    path('annual-wfh-summary/', AnnualWFHSummaryReport.as_view(), name="annual_wfh_summary_report"),

]