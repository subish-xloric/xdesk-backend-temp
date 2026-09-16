from pTracker.dataaccess.platform_access.membership_da import MembershipDA
from pTracker.dataaccess.platform_access.tenancy_da import TenancyDA
from pTracker.common.logs import Logs
from pTracker.common.exception_handler import ExceptionHandler


def _membership_dict(membership):
    return {
        'id': membership.id,
        'user_id': membership.user_id,
        'company_id': membership.company_id,
        'branch_id': membership.branch_id,
        'role_id': membership.role_id,
        'is_primary': membership.is_primary,
        'status': membership.status,
        'created_at': membership.created_at,
        'updated_at': membership.updated_at,
    }


class MembershipBL():

    def __init__(self):
        self.__log = Logs()
        self.__exception = ExceptionHandler()
        self.__da = MembershipDA()
        self.__tenancy_da = TenancyDA()

    def create_membership(self, company_id, data):
        if not self.__tenancy_da.get_company_by_id(company_id):
            return {'error': 'Company not found', 'status': 404}

        user_id = data.get('user_id')
        role_id = data.get('role_id')
        if not user_id or not role_id:
            return {'error': 'user_id and role_id are required', 'status': 400}

        if not self.__da.user_exists(user_id):
            return {'error': 'User not found', 'status': 400}
        if not self.__da.role_belongs_to_company(role_id, company_id):
            return {'error': 'role_id must belong to the same company', 'status': 400}

        branch_id = data.get('branch_id')
        if branch_id and not self.__da.branch_belongs_to_company(branch_id, company_id):
            return {'error': 'branch_id must belong to the same company', 'status': 400}

        membership = self.__da.create_membership(
            user_id=user_id,
            company_id=company_id,
            role_id=role_id,
            branch_id=branch_id,
            is_primary=bool(data.get('is_primary', False)),
        )
        return {'membership': _membership_dict(membership), 'status': 201}

    def list_memberships(self, company_id):
        if not self.__tenancy_da.get_company_by_id(company_id):
            return {'error': 'Company not found', 'status': 404}
        memberships = self.__da.get_memberships_for_company(company_id)
        return {'memberships': [_membership_dict(m) for m in memberships], 'status': 200}

    def get_membership(self, membership_id):
        membership = self.__da.get_membership_by_id(membership_id)
        if not membership:
            return {'error': 'Membership not found', 'status': 404}
        return {'membership': _membership_dict(membership), 'status': 200}

    def update_membership(self, membership_id, data):
        membership = self.__da.get_membership_by_id(membership_id)
        if not membership:
            return {'error': 'Membership not found', 'status': 404}

        fields = {}
        for key in ('is_primary', 'status'):
            if key in data:
                fields[key] = data[key]

        if 'role_id' in data:
            if not self.__da.role_belongs_to_company(data['role_id'], membership.company_id):
                return {'error': 'role_id must belong to the same company', 'status': 400}
            fields['role_id'] = data['role_id']

        if 'branch_id' in data:
            branch_id = data['branch_id']
            if branch_id and not self.__da.branch_belongs_to_company(branch_id, membership.company_id):
                return {'error': 'branch_id must belong to the same company', 'status': 400}
            fields['branch_id'] = branch_id

        if not fields:
            return {'error': 'No updatable fields provided', 'status': 400}

        membership = self.__da.update_membership(membership_id, **fields)
        return {'membership': _membership_dict(membership), 'status': 200}
