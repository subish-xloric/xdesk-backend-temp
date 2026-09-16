from rest_framework.permissions import IsAuthenticated
from rest_framework.response import Response
from rest_framework.views import APIView

from pTracker.common.platform_jwt_auth import PlatformJWTAuthentication
from pTracker.common.permissions import IsPlatformUser
from pTracker.api.platform.platform_auth_biz import PlatformAuthBL
from pTracker.api.platform.tenancy_biz import TenancyBL
from pTracker.api.platform.role_biz import CapabilityBL
from pTracker.api.platform.role_biz import RoleBL
from pTracker.api.platform.membership_biz import MembershipBL


class PlatformLoginView(APIView):
    authentication_classes = []
    permission_classes = []

    def post(self, request):
        response = PlatformAuthBL().login(request.data.get('email'), request.data.get('password'))
        return Response(response, status=response.get('status', 200))


class TenantListCreateView(APIView):
    authentication_classes = [PlatformJWTAuthentication]
    permission_classes = [IsAuthenticated, IsPlatformUser]

    def get(self, request):
        response = TenancyBL().list_tenants()
        return Response(response, status=response.get('status', 200))

    def post(self, request):
        response = TenancyBL().create_tenant(request.data)
        return Response(response, status=response.get('status', 200))


class TenantDetailView(APIView):
    authentication_classes = [PlatformJWTAuthentication]
    permission_classes = [IsAuthenticated, IsPlatformUser]

    def get(self, request, tenant_id):
        response = TenancyBL().get_tenant(tenant_id)
        return Response(response, status=response.get('status', 200))

    def put(self, request, tenant_id):
        response = TenancyBL().update_tenant(tenant_id, request.data)
        return Response(response, status=response.get('status', 200))


class CompanyListCreateView(APIView):
    authentication_classes = [PlatformJWTAuthentication]
    permission_classes = [IsAuthenticated, IsPlatformUser]

    def get(self, request, tenant_id):
        response = TenancyBL().list_companies(tenant_id)
        return Response(response, status=response.get('status', 200))

    def post(self, request, tenant_id):
        response = TenancyBL().create_company(tenant_id, request.data)
        return Response(response, status=response.get('status', 200))


class CompanyDetailView(APIView):
    authentication_classes = [PlatformJWTAuthentication]
    permission_classes = [IsAuthenticated, IsPlatformUser]

    def get(self, request, company_id):
        response = TenancyBL().get_company(company_id)
        return Response(response, status=response.get('status', 200))

    def put(self, request, company_id):
        response = TenancyBL().update_company(company_id, request.data)
        return Response(response, status=response.get('status', 200))


class BranchListCreateView(APIView):
    authentication_classes = [PlatformJWTAuthentication]
    permission_classes = [IsAuthenticated, IsPlatformUser]

    def get(self, request, company_id):
        response = TenancyBL().list_branches(company_id)
        return Response(response, status=response.get('status', 200))

    def post(self, request, company_id):
        response = TenancyBL().create_branch(company_id, request.data)
        return Response(response, status=response.get('status', 200))


class BranchDetailView(APIView):
    authentication_classes = [PlatformJWTAuthentication]
    permission_classes = [IsAuthenticated, IsPlatformUser]

    def get(self, request, branch_id):
        response = TenancyBL().get_branch(branch_id)
        return Response(response, status=response.get('status', 200))

    def put(self, request, branch_id):
        response = TenancyBL().update_branch(branch_id, request.data)
        return Response(response, status=response.get('status', 200))


class CapabilityListView(APIView):
    authentication_classes = [PlatformJWTAuthentication]
    permission_classes = [IsAuthenticated, IsPlatformUser]

    def get(self, request):
        response = CapabilityBL().list_capabilities()
        return Response(response, status=response.get('status', 200))


class RoleListCreateView(APIView):
    authentication_classes = [PlatformJWTAuthentication]
    permission_classes = [IsAuthenticated, IsPlatformUser]

    def get(self, request, company_id):
        response = RoleBL().list_roles(company_id)
        return Response(response, status=response.get('status', 200))

    def post(self, request, company_id):
        response = RoleBL().create_role(company_id, request.data)
        return Response(response, status=response.get('status', 200))


class RoleDetailView(APIView):
    authentication_classes = [PlatformJWTAuthentication]
    permission_classes = [IsAuthenticated, IsPlatformUser]

    def get(self, request, role_id):
        response = RoleBL().get_role(role_id)
        return Response(response, status=response.get('status', 200))

    def put(self, request, role_id):
        response = RoleBL().update_role(role_id, request.data)
        return Response(response, status=response.get('status', 200))


class RoleCapabilitiesView(APIView):
    authentication_classes = [PlatformJWTAuthentication]
    permission_classes = [IsAuthenticated, IsPlatformUser]

    def put(self, request, role_id):
        response = RoleBL().set_role_capabilities(role_id, request.data.get('capability_codes', []))
        return Response(response, status=response.get('status', 200))


class MembershipListCreateView(APIView):
    authentication_classes = [PlatformJWTAuthentication]
    permission_classes = [IsAuthenticated, IsPlatformUser]

    def get(self, request, company_id):
        response = MembershipBL().list_memberships(company_id)
        return Response(response, status=response.get('status', 200))

    def post(self, request, company_id):
        response = MembershipBL().create_membership(company_id, request.data)
        return Response(response, status=response.get('status', 200))


class MembershipDetailView(APIView):
    authentication_classes = [PlatformJWTAuthentication]
    permission_classes = [IsAuthenticated, IsPlatformUser]

    def get(self, request, membership_id):
        response = MembershipBL().get_membership(membership_id)
        return Response(response, status=response.get('status', 200))

    def put(self, request, membership_id):
        response = MembershipBL().update_membership(membership_id, request.data)
        return Response(response, status=response.get('status', 200))
