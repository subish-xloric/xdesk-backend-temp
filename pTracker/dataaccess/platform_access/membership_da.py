from django.contrib.auth import get_user_model
from django.db.models import Q

from pTracker.dataaccess.platform_access.membership_models import Membership
from pTracker.dataaccess.platform_access.role_models import Role
from pTracker.dataaccess.platform_access.tenancy_models import Branch
from pTracker.dataaccess.platform_access.capability_models import Capability


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

    def get_active_memberships_for_user(self, user_id):
        """ Active memberships in active companies, primary first. A user can hold
        several rows per company (different branch/role); callers group by company. """
        return list(Membership.objects.filter(
            user_id=user_id, status=Membership.STATUS_ACTIVE, company__is_active=True,
        ).select_related('company', 'role').order_by('-is_primary', 'company_id', 'id'))

    def get_effective_capability_codes(self, user_id, company_id):
        """ Union of the role capabilities and the extra capabilities of every active
        membership the user holds in this one company. Never spans companies. """
        memberships = Membership.objects.filter(
            user_id=user_id, company_id=company_id, status=Membership.STATUS_ACTIVE)
        from_roles = Capability.objects.filter(
            roles__is_active=True, roles__memberships__in=memberships).values_list('code', flat=True)
        from_extra = Capability.objects.filter(
            extra_on_memberships__in=memberships).values_list('code', flat=True)
        return set(from_roles) | set(from_extra)

    def get_user_ids_with_capability(self, company_id, capability_code):
        """ Users whose active membership in this company grants the capability,
        through an active role or the membership's extra capabilities. """
        return Membership.objects.filter(
            Q(role__is_active=True, role__capabilities__code=capability_code)
            | Q(extra_capabilities__code=capability_code),
            company_id=company_id, status=Membership.STATUS_ACTIVE,
        ).values_list('user_id', flat=True).distinct()

    def update_membership(self, membership_id, **fields):
        Membership.objects.filter(pk=membership_id).update(**fields)
        return self.get_membership_by_id(membership_id)

    def role_belongs_to_company(self, role_id, company_id):
        return Role.objects.filter(pk=role_id, company_id=company_id).exists()

    def branch_belongs_to_company(self, branch_id, company_id):
        return Branch.objects.filter(pk=branch_id, company_id=company_id).exists()

    def set_extra_capabilities(self, membership_id, capability_codes):
        membership = self.get_membership_by_id(membership_id)
        if not membership:
            return None
        capabilities = Capability.objects.filter(code__in=capability_codes)
        membership.extra_capabilities.set(capabilities)
        return membership
