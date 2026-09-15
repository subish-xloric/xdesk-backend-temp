# this url file is created for mobile version v1
from django.urls import re_path as url
from django.contrib import admin
from django.urls import path


from pTracker.api.attendance.views import CancelWFHRequestView_V1, GetWorkHours_V1
from pTracker.api.attendance.views import CreateWFHRequestView_V1
from pTracker.api.attendance.views import UpdateWFHRequestView_V1
from pTracker.api.attendance.views import MyWFHRequestListView_V1
from pTracker.api.attendance.views import TeamWFHRequestListView_V1
from pTracker.api.attendance.views import WebPunch_V1
from pTracker.api.attendance.views import MyRecordList_V1
from pTracker.api.attendance.views import GetTeamStatsView_V1
from pTracker.api.attendance.views import GetTeamStatsViewbyKeyword_V1
from pTracker.api.attendance.views import WebPunchCheck_V1
from pTracker.api.attendance.views import WFHRequestListViewByEmpId_V1
from pTracker.api.attendance.views import  VersionExpiredView

urlpatterns = [
    path('get-all-my-wfh-requests/<int:page>/<int:emp_id>/', WFHRequestListViewByEmpId_V1.as_view(), name='get_all_my_wfh_requests_v1'),
    path('get-all-my-wfh-requests/<int:page>/', MyWFHRequestListView_V1.as_view(), name='get_all_my_wfh_requests_v1'),
    # path('get-all-team-wfh-requests/<int:page>/', TeamWFHRequestListView_V1.as_view(), name='get_all_team_wfh_requests_v1'),
    path('get-all-team-wfh-requests/<int:page>/<str:status>/<str:includeOnlyDirectReporting>/', TeamWFHRequestListView_V1.as_view(), name='get_all_team_wfh_requests_v1'),
    url(r'remote-punch/', WebPunch_V1.as_view(), name='webPunch_v1'),
    path('remote-punch-check/', WebPunchCheck_V1.as_view(), name='webPunchCheck_v1'),
    url(r'request-wfh/', CreateWFHRequestView_V1.as_view(), name='create_wfh_request_v1'),
    url(r'respond-to-wfh-request/', UpdateWFHRequestView_V1.as_view(), name='update_wfh_request_v1'),
    url(r'cancel-wfh-request/', CancelWFHRequestView_V1.as_view(), name='cancel_wfh_request_v1'),

    path('get-attendance-of-month/<int:year>/<int:month>/<int:emp_id>/', MyRecordList_V1.as_view(), name='my_record_list_v1'),
    path('get-work-hours/<str:date>/<int:emp_id>/', GetWorkHours_V1.as_view(), name='work_hours_v1'),
    path('get-team-stats/<str:date>/<int:page>/<str:filterByType>/<str:searchKeyword>/', GetTeamStatsViewbyKeyword_V1.as_view(), name='team_stats_v1'),
    path('get-team-stats/<str:date>/<int:page>/<str:filterByType>/', GetTeamStatsView_V1.as_view(), name='team_stats_v1'),





    # path('get-all-my-wfh-requests/<int:page>/<int:emp_id>/', VersionExpiredView.as_view(), name='get_all_my_wfh_requests_v1'),
    # path('get-all-my-wfh-requests/<int:page>/', VersionExpiredView.as_view(), name='get_all_my_wfh_requests_v1'),
    # # path('get-all-team-wfh-requests/<int:page>/', TeamWFHRequestListView_V1.as_view(), name='get_all_team_wfh_requests_v1'),
    # path('get-all-team-wfh-requests/<int:page>/<str:status>/<str:includeOnlyDirectReporting>/', VersionExpiredView.as_view(), name='get_all_team_wfh_requests_v1'),
    # url(r'remote-punch/', VersionExpiredView.as_view(), name='webPunch_v1'),
    # path('remote-punch-check/', VersionExpiredView.as_view(), name='webPunchCheck_v1'),
    # url(r'request-wfh/', VersionExpiredView.as_view(), name='create_wfh_request_v1'),
    # url(r'respond-to-wfh-request/', VersionExpiredView.as_view(), name='update_wfh_request_v1'),
    # url(r'cancel-wfh-request/', VersionExpiredView.as_view(), name='cancel_wfh_request_v1'),

    # path('get-attendance-of-month/<int:year>/<int:month>/<int:emp_id>/', VersionExpiredView.as_view(), name='my_record_list_v1'),
    # path('get-work-hours/<str:date>/<int:emp_id>/', VersionExpiredView.as_view(), name='work_hours_v1'),
    # path('get-team-stats/<str:date>/<int:page>/<str:filterByType>/<str:searchKeyword>/', VersionExpiredView.as_view(), name='team_stats_v1'),
    # path('get-team-stats/<str:date>/<int:page>/<str:filterByType>/', VersionExpiredView.as_view(), name='team_stats_v1'),

]