from pTracker.dataaccess.platform_access.tenancy_da import TenancyDA
from pTracker.dataaccess.platform_access.tenancy_models import Tenant
from pTracker.dataaccess.platform_access.tenancy_models import Branch
from pTracker.common.logs import Logs
from pTracker.common.exception_handler import ExceptionHandler


def _tenant_dict(tenant):
    return {
        'id': tenant.id,
        'slug': tenant.slug,
        'name': tenant.name,
        'status': tenant.status,
        'created_at': tenant.created_at,
        'updated_at': tenant.updated_at,
    }


def _company_dict(company):
    return {
        'id': company.id,
        'tenant_id': company.tenant_id,
        'parent_company_id': company.parent_company_id,
        'legal_name': company.legal_name,
        'short_name': company.short_name,
        'registered_address': company.registered_address,
        'contact_email': company.contact_email,
        'is_active': company.is_active,
        'created_at': company.created_at,
        'updated_at': company.updated_at,
    }


def _branch_dict(branch):
    return {
        'id': branch.id,
        'company_id': branch.company_id,
        'name': branch.name,
        'code': branch.code,
        'kind': branch.kind,
        'timezone': branch.timezone,
        'address': branch.address,
        'is_active': branch.is_active,
        'created_at': branch.created_at,
        'updated_at': branch.updated_at,
    }


class TenancyBL():

    def __init__(self):
        self.__log = Logs()
        self.__exception = ExceptionHandler()
        self.__da = TenancyDA()

    # Tenant

    def create_tenant(self, data):
        slug = data.get('slug')
        name = data.get('name')
        if not slug or not name:
            return {'error': 'slug and name are required', 'status': 400}
        if self.__da.get_tenant_by_slug(slug):
            return {'error': 'A tenant with this slug already exists', 'status': 400}

        status = data.get('status', Tenant.STATUS_TRIAL)
        tenant = self.__da.create_tenant(slug=slug, name=name, status=status)
        return {'tenant': _tenant_dict(tenant), 'status': 201}

    def list_tenants(self):
        tenants = self.__da.get_all_tenants()
        return {'tenants': [_tenant_dict(t) for t in tenants], 'status': 200}

    def get_tenant(self, tenant_id):
        tenant = self.__da.get_tenant_by_id(tenant_id)
        if not tenant:
            return {'error': 'Tenant not found', 'status': 404}
        return {'tenant': _tenant_dict(tenant), 'status': 200}

    def update_tenant(self, tenant_id, data):
        tenant = self.__da.get_tenant_by_id(tenant_id)
        if not tenant:
            return {'error': 'Tenant not found', 'status': 404}

        fields = {}
        for key in ('name', 'status'):
            if key in data:
                fields[key] = data[key]
        if not fields:
            return {'error': 'No updatable fields provided', 'status': 400}

        tenant = self.__da.update_tenant(tenant_id, **fields)
        return {'tenant': _tenant_dict(tenant), 'status': 200}

    # Company

    def create_company(self, tenant_id, data):
        tenant = self.__da.get_tenant_by_id(tenant_id)
        if not tenant:
            return {'error': 'Tenant not found', 'status': 404}

        legal_name = data.get('legal_name')
        short_name = data.get('short_name')
        if not legal_name or not short_name:
            return {'error': 'legal_name and short_name are required', 'status': 400}

        parent_company_id = data.get('parent_company_id')
        if parent_company_id:
            parent = self.__da.get_company_by_id(parent_company_id)
            if not parent or parent.tenant_id != tenant.id:
                return {'error': 'parent_company_id must belong to the same tenant', 'status': 400}

        company = self.__da.create_company(
            tenant_id=tenant.id,
            legal_name=legal_name,
            short_name=short_name,
            parent_company_id=parent_company_id,
            registered_address=data.get('registered_address'),
            contact_email=data.get('contact_email'),
        )
        return {'company': _company_dict(company), 'status': 201}

    def list_companies(self, tenant_id):
        if not self.__da.get_tenant_by_id(tenant_id):
            return {'error': 'Tenant not found', 'status': 404}
        companies = self.__da.get_companies_for_tenant(tenant_id)
        return {'companies': [_company_dict(c) for c in companies], 'status': 200}

    def get_company(self, company_id):
        company = self.__da.get_company_by_id(company_id)
        if not company:
            return {'error': 'Company not found', 'status': 404}
        return {'company': _company_dict(company), 'status': 200}

    def update_company(self, company_id, data):
        company = self.__da.get_company_by_id(company_id)
        if not company:
            return {'error': 'Company not found', 'status': 404}

        fields = {}
        for key in ('legal_name', 'short_name', 'registered_address', 'contact_email', 'is_active'):
            if key in data:
                fields[key] = data[key]
        if not fields:
            return {'error': 'No updatable fields provided', 'status': 400}

        company = self.__da.update_company(company_id, **fields)
        return {'company': _company_dict(company), 'status': 200}

    # Branch

    def create_branch(self, company_id, data):
        company = self.__da.get_company_by_id(company_id)
        if not company:
            return {'error': 'Company not found', 'status': 404}

        name = data.get('name')
        code = data.get('code')
        if not name or not code:
            return {'error': 'name and code are required', 'status': 400}

        branch = self.__da.create_branch(
            company_id=company.id,
            name=name,
            code=code,
            kind=data.get('kind', Branch.KIND_OFFICE),
            timezone=data.get('timezone', 'Asia/Kolkata'),
            address=data.get('address'),
        )
        return {'branch': _branch_dict(branch), 'status': 201}

    def list_branches(self, company_id):
        if not self.__da.get_company_by_id(company_id):
            return {'error': 'Company not found', 'status': 404}
        branches = self.__da.get_branches_for_company(company_id)
        return {'branches': [_branch_dict(b) for b in branches], 'status': 200}

    def get_branch(self, branch_id):
        branch = self.__da.get_branch_by_id(branch_id)
        if not branch:
            return {'error': 'Branch not found', 'status': 404}
        return {'branch': _branch_dict(branch), 'status': 200}

    def update_branch(self, branch_id, data):
        branch = self.__da.get_branch_by_id(branch_id)
        if not branch:
            return {'error': 'Branch not found', 'status': 404}

        fields = {}
        for key in ('name', 'code', 'kind', 'timezone', 'address', 'is_active'):
            if key in data:
                fields[key] = data[key]
        if not fields:
            return {'error': 'No updatable fields provided', 'status': 400}

        branch = self.__da.update_branch(branch_id, **fields)
        return {'branch': _branch_dict(branch), 'status': 200}
