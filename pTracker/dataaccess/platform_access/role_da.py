from pTracker.dataaccess.platform_access.role_models import Role
from pTracker.dataaccess.platform_access.capability_models import Capability


class RoleDA():

    def create_role(self, company_id, name, description=None):
        return Role.objects.create(company_id=company_id, name=name, description=description)

    def get_roles_for_company(self, company_id):
        return Role.objects.filter(company_id=company_id).order_by('name')

    def get_role_by_id(self, role_id):
        return Role.objects.filter(pk=role_id).first()

    def update_role(self, role_id, **fields):
        Role.objects.filter(pk=role_id).update(**fields)
        return self.get_role_by_id(role_id)

    def set_capabilities(self, role_id, capability_codes):
        role = self.get_role_by_id(role_id)
        if not role:
            return None
        capabilities = Capability.objects.filter(code__in=capability_codes)
        role.capabilities.set(capabilities)
        return role
