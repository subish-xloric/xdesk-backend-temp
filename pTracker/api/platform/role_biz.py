from pTracker.dataaccess.platform_access.role_da import RoleDA
from pTracker.dataaccess.platform_access.capability_da import CapabilityDA
from pTracker.dataaccess.platform_access.tenancy_da import TenancyDA
from pTracker.common.logs import Logs
from pTracker.common.exception_handler import ExceptionHandler


def _capability_dict(capability):
    return {
        'code': capability.code,
        'module': capability.module,
        'description': capability.description,
    }


def _role_dict(role):
    return {
        'id': role.id,
        'company_id': role.company_id,
        'name': role.name,
        'description': role.description,
        'is_active': role.is_active,
        'capabilities': [c.code for c in role.capabilities.all()],
        'created_at': role.created_at,
        'updated_at': role.updated_at,
    }


class CapabilityBL():

    def __init__(self):
        self.__da = CapabilityDA()

    def list_capabilities(self):
        capabilities = self.__da.get_all()
        return {'capabilities': [_capability_dict(c) for c in capabilities], 'status': 200}


class RoleBL():

    def __init__(self):
        self.__log = Logs()
        self.__exception = ExceptionHandler()
        self.__role_da = RoleDA()
        self.__capability_da = CapabilityDA()
        self.__tenancy_da = TenancyDA()

    def create_role(self, company_id, data):
        if not self.__tenancy_da.get_company_by_id(company_id):
            return {'error': 'Company not found', 'status': 404}

        name = data.get('name')
        if not name:
            return {'error': 'name is required', 'status': 400}

        role = self.__role_da.create_role(company_id, name, data.get('description'))
        return {'role': _role_dict(role), 'status': 201}

    def list_roles(self, company_id):
        if not self.__tenancy_da.get_company_by_id(company_id):
            return {'error': 'Company not found', 'status': 404}
        roles = self.__role_da.get_roles_for_company(company_id)
        return {'roles': [_role_dict(r) for r in roles], 'status': 200}

    def get_role(self, role_id):
        role = self.__role_da.get_role_by_id(role_id)
        if not role:
            return {'error': 'Role not found', 'status': 404}
        return {'role': _role_dict(role), 'status': 200}

    def update_role(self, role_id, data):
        role = self.__role_da.get_role_by_id(role_id)
        if not role:
            return {'error': 'Role not found', 'status': 404}

        fields = {}
        for key in ('name', 'description', 'is_active'):
            if key in data:
                fields[key] = data[key]
        if not fields:
            return {'error': 'No updatable fields provided', 'status': 400}

        role = self.__role_da.update_role(role_id, **fields)
        return {'role': _role_dict(role), 'status': 200}

    def set_role_capabilities(self, role_id, capability_codes):
        role = self.__role_da.get_role_by_id(role_id)
        if not role:
            return {'error': 'Role not found', 'status': 404}
        if not isinstance(capability_codes, list):
            return {'error': 'capability_codes must be a list', 'status': 400}

        existing = set(self.__capability_da.get_by_codes(capability_codes).values_list('code', flat=True))
        unknown = set(capability_codes) - existing
        if unknown:
            return {'error': f'Unknown capability codes: {sorted(unknown)}', 'status': 400}

        role = self.__role_da.set_capabilities(role_id, capability_codes)
        return {'role': _role_dict(role), 'status': 200}
