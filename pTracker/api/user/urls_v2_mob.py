# this url file is created for mobile version v1
from django.urls import re_path as url
from django.contrib import admin
from django.urls import path

from pTracker.api.user.views import AuthyTokenVerifyView_V1
from pTracker.api.user.views import CustomLoginView_v1
from pTracker.api.user.views import DashboardAnniversaries_V1
from pTracker.api.user.views import EmployeeDetailsView_V1
from pTracker.api.user.views import GetRequestCount_V1
# from pTracker.api.user.views import GetTeamStatsView_V1
from pTracker.api.user.views import GetTeameMemebers_V1
from pTracker.api.user.views import GetApplicationData_V1

from pTracker.api.user.views import CheckResetAPIView_v1
from pTracker.api.user.views import PasswordResetView_v1
from pTracker.api.user.views import SetNewPasswordAPIView_v1
# from pTracker.api.user.views import GetTeamStatsViewbyKeyword_V1
from pTracker.api.user.views import CustomLogoutView_v1
# from pTracker.api.user.views import GetVersionStatus
from pTracker.api.user.views import SaveEmployeeProileDetails_v1
from pTracker.api.user.views import GetAllEmployeeProfilesWaitingAction_v1
from pTracker.api.user.views import GetEmployeeProfileInfoAwaitsAction_v1
from pTracker.api.user.views import ApplyActionOnProfileChange_v1
from pTracker.api.user.views import BiometricRegistrationView
from pTracker.api.user.views import BiometricLoginView
from pTracker.api.user.views import SaveEmployeeProfileImage_v1


urlpatterns = [

   url(r'login/', CustomLoginView_v1.as_view(), name='custom_login_v1'),
   url(r'2fa/token-verify/', AuthyTokenVerifyView_V1.as_view(), name='2fa_token_verify_v1'),
   url(r'logout/', CustomLogoutView_v1.as_view(), name='custom_logout_v1'),

   path('get-employee-profile/<int:emp_id>/', EmployeeDetailsView_V1.as_view(), name='get_employee_detail_profile_v1'),
   path('get-team-members/', GetTeameMemebers_V1.as_view(), name='get_team_members_v1'),
   path('get-request-count/', GetRequestCount_V1.as_view(), name='get_request_count_v1'),

   path('dashboard/', DashboardAnniversaries_V1.as_view(), name='dashboard_anniversaries_v1'),
   #path('get-team-stats/<str:date>/<int:page>/', GetTeamStatsView_V1.as_view(), name='team_stats_v1'),
   #path('get-team-stats/<str:date>/<int:page>/<str:searchKeyword>/', GetTeamStatsViewbyKeyword_V1.as_view(), name='team_stats_v1'),
   path('get-application-data/', GetApplicationData_V1.as_view(), name='get_application_data_v1'),

    path('reset-password/', PasswordResetView_v1.as_view(),name="request_reset_email"),
    path('password-reset-complete/', SetNewPasswordAPIView_v1.as_view(),name='password-reset-complete'),
    path('api-check/', CheckResetAPIView_v1.as_view(),name='api-check'),
   #  path('get-vesion-status/', GetVersionStatus.as_view(),name='get_vesion_status'),

     path('save-employee-profile/', SaveEmployeeProileDetails_v1.as_view(),name='save_employee_profile'),
     path('get-pending-profile-approvals/', GetAllEmployeeProfilesWaitingAction_v1.as_view(),name='get_employee_details_awaiting_approval'),
     path('get-profile-info-awaiting-approval/<int:emp_id>/', GetEmployeeProfileInfoAwaitsAction_v1.as_view(),name='get_profile_info_awaiting_approval'),
     path('apply-action-on-profile-field/', ApplyActionOnProfileChange_v1.as_view(),name='apply_action_on_profile_field'),

     path('biometric-authentication/', BiometricLoginView.as_view(), name='biometric_authentication'),
     path('register-for-biometric-authentication/', BiometricRegistrationView.as_view(),name='biometric_authentication'),

     path('save-employee-profile-image/', SaveEmployeeProfileImage_v1.as_view(),name='save_employee_profile_image'),


]