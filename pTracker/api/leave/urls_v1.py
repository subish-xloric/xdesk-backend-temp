# this url file is created for mobile version v1
from django.urls import re_path as url
from django.contrib import admin
from django.urls import path

from pTracker.api.leave.views import TeamLeaveSummaryView_V1
from pTracker.api.leave.views import CreateLeaveRequest_V1
from pTracker.api.leave.views import LeaveDateValidation_V1
from pTracker.api.leave.views import LeaveStatusUpdateView_V1
from pTracker.api.leave.views import UserLeaveSummaryView_V1
from pTracker.api.leave.views import LeaveCancelView_V1
from pTracker.api.leave.views import UserLeaveSummaryViewByEmpID_V1
from pTracker.api.leave.views import GetUserLeaveSummaryByEmpID_V1
from pTracker.api.leave.views import VersionExpiredView

urlpatterns = [
    path('request-leave/', CreateLeaveRequest_V1.as_view(), name="leave_request_create_v1"),
    path('get-all-my-leave-requests/<int:page>/<int:emp_id>/', UserLeaveSummaryViewByEmpID_V1.as_view(), name="my_leave_summary_v1"),
    path('get-all-my-leave-requests/<int:page>/', UserLeaveSummaryView_V1.as_view(), name="my_leave_summary_v1"),
    path('cancel-leave-request/', LeaveCancelView_V1.as_view(), name="leave_status_updater_v1"),
    path('get-team-leave-requests/<int:page>/<str:status>/<str:includeOnlyDirectReporting>/', TeamLeaveSummaryView_V1.as_view(), name="team_leave_summary"),
    path('validate-date/<str:start_date>/<str:end_date>/', LeaveDateValidation_V1.as_view(), name="leave_date_validation"),
    path('respond-to-leave-request/', LeaveStatusUpdateView_V1.as_view(), name="leave_request_respond_v1"),
    path('get-leave-summary/<int:emp_id>/', GetUserLeaveSummaryByEmpID_V1.as_view(), name="get_leave_summary"),



#      path('request-leave/', VersionExpiredView.as_view(), name="leave_request_create_v1"),
#     path('get-all-my-leave-requests/<int:page>/<int:emp_id>/', VersionExpiredView.as_view(), name="my_leave_summary_v1"),
#     path('get-all-my-leave-requests/<int:page>/', VersionExpiredView.as_view(), name="my_leave_summary_v1"),
#     path('cancel-leave-request/', VersionExpiredView.as_view(), name="leave_status_updater_v1"),
#     path('get-team-leave-requests/<int:page>/<str:status>/<str:includeOnlyDirectReporting>/', VersionExpiredView.as_view(), name="team_leave_summary"),
#     path('validate-date/<str:start_date>/<str:end_date>/', VersionExpiredView.as_view(), name="leave_date_validation"),
#     path('respond-to-leave-request/', VersionExpiredView.as_view(), name="leave_request_respond_v1"),
#     path('get-leave-summary/<int:emp_id>/', VersionExpiredView.as_view(), name="get_leave_summary"),
]