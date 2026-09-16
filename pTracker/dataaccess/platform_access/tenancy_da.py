from pTracker.dataaccess.platform_access.tenancy_models import Tenant
from pTracker.dataaccess.platform_access.tenancy_models import Company
from pTracker.dataaccess.platform_access.tenancy_models import Branch


class TenancyDA():

    # Tenant

    def create_tenant(self, slug, name, status=Tenant.STATUS_TRIAL):
        return Tenant.objects.create(slug=slug, name=name, status=status)

    def get_all_tenants(self):
        return Tenant.objects.all().order_by('name')

    def get_tenant_by_id(self, tenant_id):
        return Tenant.objects.filter(pk=tenant_id).first()

    def get_tenant_by_slug(self, slug):
        return Tenant.objects.filter(slug=slug).first()

    def update_tenant(self, tenant_id, **fields):
        Tenant.objects.filter(pk=tenant_id).update(**fields)
        return self.get_tenant_by_id(tenant_id)

    # Company

    def create_company(self, tenant_id, legal_name, short_name, parent_company_id=None,
            registered_address=None, contact_email=None):
        return Company.objects.create(
            tenant_id=tenant_id,
            parent_company_id=parent_company_id,
            legal_name=legal_name,
            short_name=short_name,
            registered_address=registered_address,
            contact_email=contact_email,
        )

    def get_companies_for_tenant(self, tenant_id):
        return Company.objects.filter(tenant_id=tenant_id).order_by('legal_name')

    def get_company_by_id(self, company_id):
        return Company.objects.filter(pk=company_id).first()

    def update_company(self, company_id, **fields):
        Company.objects.filter(pk=company_id).update(**fields)
        return self.get_company_by_id(company_id)

    # Branch

    def create_branch(self, company_id, name, code, kind=Branch.KIND_OFFICE,
            timezone='Asia/Kolkata', address=None):
        return Branch.objects.create(
            company_id=company_id,
            name=name,
            code=code,
            kind=kind,
            timezone=timezone,
            address=address,
        )

    def get_branches_for_company(self, company_id):
        return Branch.objects.filter(company_id=company_id).order_by('name')

    def get_branch_by_id(self, branch_id):
        return Branch.objects.filter(pk=branch_id).first()

    def update_branch(self, branch_id, **fields):
        Branch.objects.filter(pk=branch_id).update(**fields)
        return self.get_branch_by_id(branch_id)
