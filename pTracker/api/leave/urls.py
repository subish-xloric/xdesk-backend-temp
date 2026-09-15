from django.urls import re_path as url
from django.contrib import admin
from django.urls import path


from pTracker.api.leave.views import TeamLeaveCalendarView
from pTracker.api.leave.views import CreateFormDropdowns
from pTracker.api.leave.views import UserLeaveSummaryView
from pTracker.api.leave.views import LeaveStatusUpdateView
from pTracker.api.leave.views import LeaveDateValidation
from pTracker.api.leave.views import CreateLeaveRequest
from pTracker.api.leave.views import GetLeaveRequest
from pTracker.api.leave.views import TeamLeaveSummaryView
from pTracker.api.leave.views import TeamLeaveDropdownView
from pTracker.api.leave.views import UpdateLeaveRequest
from pTracker.api.leave.views import CompensatoryLeaveFormDropdowns
from pTracker.api.leave.views import LeaveReportDropDowns
from pTracker.api.leave.views import LeaveReportList
from pTracker.api.leave.views import CompensatoryLeaveDateValidation
from pTracker.api.leave.views import CreateCompensatoryLeave
from pTracker.api.leave.views import CompensataoryLeaveView
from pTracker.api.leave.views import TeamMembersByLeadId
from pTracker.api.leave.views import UpdateCompensatoryLeave
from pTracker.api.leave.views import CompensatoryLeaveFilter
from pTracker.api.leave.views import LeaveRequestDateValidate
from pTracker.api.leave.views import PendingLeavesView
from pTracker.api.leave.views import SendNotPunchNotification
from pTracker.api.leave.views import DebitleavesView

from pTracker.api.leave.views import LeaveSummaryReport
from pTracker.api.leave.views import AnnualLeaveSummaryReport
from pTracker.api.leave.views import  GetAllActiveUsers
from pTracker.api.leave.views import  CreditLeaveQuotaView
from pTracker.api.leave.views import  AnuualLeaveDetailView


from pTracker.api.leave.views import LeaveQuotaView
from pTracker.api.leave.views import UpdateLeaveQuota
from pTracker.api.leave.views import PendingRequestListView

urlpatterns = [
    path('team-leave-calendar/', TeamLeaveCalendarView.as_view(), name="team_leave_calendar"),
    path('fill-leave-apply-form-dropdowns/', CreateFormDropdowns.as_view(), name="fill_leave_apply_form_dropdowns"),
    path('leave-date-validation/', LeaveDateValidation.as_view(), name="leave_date_validation"),

    path('my-leave-summary/', UserLeaveSummaryView.as_view(), name="my_leave_summary"),
    path('team-leave-summary/', TeamLeaveSummaryView.as_view(), name="team_leave_summary"),
    path('team-leave-dropdown/', TeamLeaveDropdownView.as_view(), name='team_leave_dropdown'),
    #Leave Requset
    path('leave-request-create/', CreateLeaveRequest.as_view(), name="leave_request_create"),
    path('leave-request-update/', UpdateLeaveRequest.as_view(), name="leave_request_edit"),
    path('get-leave-request/', GetLeaveRequest.as_view(), name="get_leave_request"),



    path('leave-status-updater/', LeaveStatusUpdateView.as_view(), name="leave_status_updater"),


    path('compensatory-leave/manage/', CompensataoryLeaveView.as_view(), name="compensatory_leave_manage"),
    path('compensatory-leave/form-dropdowns/', CompensatoryLeaveFormDropdowns.as_view(), name="compensatory_form_dropdowns"),
    path('compensatory-leave/create/', CreateCompensatoryLeave.as_view(), name="create_compensatory_leave"),

    path('compensatory-leave-date-validation/', CompensatoryLeaveDateValidation.as_view(), name="compensatory_leave_date_validation"),

    #path('compensatory-leaves/', CompensataoryLeaveView.as_view(), name="compensatory_leaves"),
    path('team-members/', TeamMembersByLeadId.as_view(), name="team-members"),
    path('update-compensatory-leave/', UpdateCompensatoryLeave.as_view(), name="update-compensatory-leave"),
    path('compensatory-leave-filter/', CompensatoryLeaveFilter.as_view(), name="compensatory-leave-filter"),

    path('leave-report-dropdowns/', LeaveReportDropDowns.as_view(), name="leave_report_dropdowns"),
    path('leave-report-list/', LeaveReportList.as_view(), name="leave_report_list"),
    path('send-not-punch-notification/', SendNotPunchNotification.as_view(), name="send_not_punch_notification"),



    path('reports/leave-summary/', LeaveSummaryReport.as_view(), name="leave_summary_report"),
    path('reports/annual-leave-summary/', AnnualLeaveSummaryReport.as_view(), name="annual_leave_summary_report"),

    path('reports/annual-leave-summary-dropdown/', GetAllActiveUsers.as_view(), name="annual-leave-summary-dropdown"),

    path('credit-leave-quota/<int:year>/', CreditLeaveQuotaView.as_view(), name="credit_leave_quota"),
    path('annual-leave-details/<int:emp_id>/<int:year>', AnuualLeaveDetailView.as_view(), name="annual_leave_details"),

    path('leave-quota/<int:year>', LeaveQuotaView.as_view(), name="leave_quota"),
    path('update-leave-quota/', UpdateLeaveQuota.as_view(), name="update_leave_quota"),
    path('pending-request-list/', PendingRequestListView.as_view(), name="pending_request_list"),
    path('leave-request-date-validate/<str:start_date>/<str:end_date>/<int:edit_id>', LeaveRequestDateValidate.as_view(), name="leave_request_date_validate"),
    path('pending-leaves-list/', PendingLeavesView.as_view(), name="pending_leaves_list"),
    path('debit-leaves/', DebitleavesView.as_view(), name="deabit_leaves"),
]





