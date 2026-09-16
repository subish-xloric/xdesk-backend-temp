from django.urls import path

from pTracker.api.platform.views import PlatformLoginView
from pTracker.api.platform.views import TenantListCreateView
from pTracker.api.platform.views import TenantDetailView
from pTracker.api.platform.views import CompanyListCreateView
from pTracker.api.platform.views import CompanyDetailView
from pTracker.api.platform.views import BranchListCreateView
from pTracker.api.platform.views import BranchDetailView
from pTracker.api.platform.views import CapabilityListView
from pTracker.api.platform.views import RoleListCreateView
from pTracker.api.platform.views import RoleDetailView
from pTracker.api.platform.views import RoleCapabilitiesView
from pTracker.api.platform.views import MembershipListCreateView
from pTracker.api.platform.views import MembershipDetailView


urlpatterns = [
    path('auth/login/', PlatformLoginView.as_view(), name='platform_login'),

    path('tenants/', TenantListCreateView.as_view(), name='platform_tenant_list_create'),
    path('tenants/<int:tenant_id>/', TenantDetailView.as_view(), name='platform_tenant_detail'),
    path('tenants/<int:tenant_id>/companies/', CompanyListCreateView.as_view(), name='platform_company_list_create'),

    path('companies/<int:company_id>/', CompanyDetailView.as_view(), name='platform_company_detail'),
    path('companies/<int:company_id>/branches/', BranchListCreateView.as_view(), name='platform_branch_list_create'),
    path('companies/<int:company_id>/roles/', RoleListCreateView.as_view(), name='platform_role_list_create'),
    path('companies/<int:company_id>/memberships/', MembershipListCreateView.as_view(), name='platform_membership_list_create'),

    path('branches/<int:branch_id>/', BranchDetailView.as_view(), name='platform_branch_detail'),

    path('capabilities/', CapabilityListView.as_view(), name='platform_capability_list'),

    path('roles/<int:role_id>/', RoleDetailView.as_view(), name='platform_role_detail'),
    path('roles/<int:role_id>/capabilities/', RoleCapabilitiesView.as_view(), name='platform_role_capabilities'),

    path('memberships/<int:membership_id>/', MembershipDetailView.as_view(), name='platform_membership_detail'),
]
