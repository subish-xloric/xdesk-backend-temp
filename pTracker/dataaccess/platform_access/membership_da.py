from django.contrib.auth import get_user_model

from pTracker.dataaccess.platform_access.membership_models import Membership
from pTracker.dataaccess.platform_access.role_models import Role
from pTracker.dataaccess.platform_access.tenancy_models import Branch


class MembershipDA():

    def user_exists(self, user_id):
        return get_user_model().objects.filter(pk=user_id).exists()

    def create_membership(self, user_id, company_id, role_id, branch_id=None,
            is_primary=False, status=Membership.STATUS_ACTIVE):
        return Membership.objects.create(
            user_id=user_id,
            company_id=company_id,
            branch_id=branch_id,
            role_id=role_id,
            is_primary=is_primary,
            status=status,
        )

    def get_memberships_for_company(self, company_id):
        return Membership.objects.filter(company_id=company_id).order_by('user_id')

    def get_membership_by_id(self, membership_id):
        return Membership.objects.filter(pk=membership_id).first()

    def update_membership(self, membership_id, **fields):
        Membership.objects.filter(pk=membership_id).update(**fields)
        return self.get_membership_by_id(membership_id)

    def role_belongs_to_company(self, role_id, company_id):
        return Role.objects.filter(pk=role_id, company_id=company_id).exists()

    def branch_belongs_to_company(self, branch_id, company_id):
        return Branch.objects.filter(pk=branch_id, company_id=company_id).exists()
