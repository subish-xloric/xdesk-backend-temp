
from django.urls import re_path as url
from django.contrib import admin
from django.urls import path


from pTracker.api.rewards.views import  CreateRewardNomination
from pTracker.api.rewards.views import  ApproveRewardNomination
from pTracker.api.rewards.views import  GetParamsViews
from pTracker.api.rewards.views import  GetAllRewards
from pTracker.api.rewards.views import  RejectRewardNomination
from pTracker.api.rewards.views import  CancelRewardNomination
from pTracker.api.rewards.views import  RewardCommets
from pTracker.api.rewards.views import  GetRewardCriteria
from pTracker.api.rewards.views import  ViewRewardDetails
from pTracker.api.rewards.views import  GetAllMyRewards
from pTracker.api.rewards.views import  GetRewardReports
from pTracker.api.rewards.views import  GetRewardReportDetails
from pTracker.api.rewards.views import  GetTvNotification
from pTracker.api.rewards.views import  GetNoticeList
from pTracker.api.rewards.views import  CreateNotices
from pTracker.api.rewards.views import  CancelNotices
from pTracker.api.rewards.views import  UpdateNotices
from pTracker.api.rewards.views import GetEventList
from pTracker.api.rewards.views import CreateEvents
from pTracker.api.rewards.views import DeleteEvents
from pTracker.api.rewards.views import UpdateRewardContent

urlpatterns = [

    path('get-reward-params/', GetParamsViews.as_view(), name="get_reward_params"),
    path('get-all-rewards/', GetAllRewards.as_view(), name="get_all_rewards"),

    path('create-reward-nomination/', CreateRewardNomination.as_view(), name="create_reward_nomination"),
    path('approve-reward-nomination/', ApproveRewardNomination.as_view(), name="approve_reward_nomination"),
    path('reject-reward-nomination/', RejectRewardNomination.as_view(), name="reject_reward_nomination"),
    path('cancel-reward-nomination/', CancelRewardNomination.as_view(), name="cancel_reward_nomination"),


    path('get-all-reward-comments/<str:reward_id>/', RewardCommets.as_view(), name="get_all_reward_comments"),
    path('create-reward-comments/', RewardCommets.as_view(), name="create_reward_comments"),
    path('get-reward-criterias/<str:type_id>/', GetRewardCriteria.as_view(), name="get_reward_criterias"),
    path('view-reward-details/<str:reward_id>/', ViewRewardDetails.as_view(), name="view_reward_details"),

    path('get-all-my-rewards/', GetAllMyRewards.as_view(), name="get_all_my_rewards"),
    path('get-reward-reports/', GetRewardReports.as_view(), name="get_reward_reports"),
    path('get-reward-report-details/', GetRewardReportDetails.as_view(), name="get_reward_report_details"),

    path('manage-notices/', GetNoticeList.as_view(), name="manage_notices"),
    path('create-notices/', CreateNotices.as_view(), name="create_notices"),
    path('cancel-notices/', CancelNotices.as_view(), name="cancel_notices"),
    path('update-notices/', UpdateNotices.as_view(), name="update_notices"),

    path('create-events/', CreateEvents.as_view(), name="create_events"),
    path('list-events/', GetEventList.as_view(), name="list_events"),
    path('delete-events/', DeleteEvents.as_view(), name="delete_events"),
    path('update-reward-content/', UpdateRewardContent.as_view(), name="update_reward"),
    path('get-all-tv-notifications/', GetTvNotification.as_view(), name="get_all_tv_notifications"),
]