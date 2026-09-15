from django.urls import re_path as url
from django.contrib import admin
from django.urls import path
from rest_framework.generics import UpdateAPIView

from pTracker.api.user.views import  CreateUserView, EmployeeIDCheck, UpdateUserView
from pTracker.api.user.views import  EmployeeWorkAnniversaries
from pTracker.api.user.views import  DashboardAnniversaries
from pTracker.api.user.views import  EmployeeListView
from pTracker.api.user.views import  EmployeeDetailsView
from pTracker.api.user.views import  EmployeeManageFilterView
from pTracker.api.user.views import  EmployeeCreateDropDownsView
from pTracker.api.user.views import  GetLeads
from pTracker.api.user.views import  GetemployeesByLead
from pTracker.api.user.views import  EmployeeLeadMapping
from pTracker.api.user.views import PasswordResetView
from pTracker.api.user.views import CheckResetAPIView
from pTracker.api.user.views import SetNewPasswordAPIView
from pTracker.api.user.views import GetEmployeeProfileInfo
from pTracker.api.user.views import UpdateUserViewV2
from pTracker.api.user.views import ResendProfileQRCode
from pTracker.api.user.views import GetEmployeeProfileInfoV1
from pTracker.api.user.views import UpdateUserViewV3


urlpatterns = [
                #   url(r'work_anniversaries/', CustomLoginView.as_view(), name='custom_login'),
                url(r'create-new-user/', CreateUserView.as_view(), name='create_new_user'),
                url(r'employee-work-anniversaries/', EmployeeWorkAnniversaries.as_view(), name='work_anniversaries'),
                url(r'dashboard-anniversaries/', DashboardAnniversaries.as_view(), name='dashboard_anniversaries'),
                url(r'get-employee-list/', EmployeeListView.as_view(), name='get_employee_list'),
                url(r'get-employee-list-filters/', EmployeeManageFilterView.as_view(), name='get_employee_list_filters'),
                url(r'get-employee-detail-profile/', EmployeeDetailsView.as_view(), name='get_employee_detail_profile'),
                url(r'get-create-new-user-dropdowns/', EmployeeCreateDropDownsView.as_view(), name='get_create_new_user_dropdowns'),
                url(r'update-user/', UpdateUserView.as_view(), name='update_user'),
                url(r'check-employee-id/', EmployeeIDCheck.as_view(), name='check_employee_id'),
                url(r'get-leads/', GetLeads.as_view(), name='get-leads'),
                url(r'get-team-members/', GetemployeesByLead.as_view(), name='get-team-members'),
                url(r'create-emp-lead-mapping/', EmployeeLeadMapping.as_view(), name='create_emp_lead_mapping'),
                path('request-reset-email/', PasswordResetView.as_view(),name="request_reset_email"),
                path('password-reset-complete/', SetNewPasswordAPIView.as_view(),name='password-reset-complete'),
                path('api-check/', CheckResetAPIView.as_view(),name='api-check'),
                path('get-employee-profile-info/', GetEmployeeProfileInfo.as_view(),name='get_employee_profile_info/'),
                path('update-user-v2/', UpdateUserViewV2.as_view(),name='update_user_v2/'),
                path('resend-qr-code-by-user-id/<int:user_id>', ResendProfileQRCode.as_view(),name='resend_qr_code_by_user_id'),
                path('get-employee-profile-info-v1/', GetEmployeeProfileInfoV1.as_view(),name='get_employee_profile_info_v1'),
                path('update-user-v3/', UpdateUserViewV3.as_view(),name='update_user_v3'),
            ]