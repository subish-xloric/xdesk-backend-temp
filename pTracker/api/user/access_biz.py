from pTracker.common.company_authorization import has_capability
from pTracker.common.company_context import CompanyContextError
from pTracker.common.company_context import group_memberships_by_company
from pTracker.common.company_context import resolve_active_company
from pTracker.common.company_modules import get_catalog_module_codes
from pTracker.common.company_modules import get_enabled_module_codes
from pTracker.dataaccess.platform_access.membership_da import MembershipDA


def _company_summary(memberships):
    """ One entry per company; the user's roles there, primary membership first. """
    company = memberships[0].company
    return {
        'id': company.id,
        'name': company.short_name,
        'roles': sorted({m.role.name for m in memberships}),
        'is_primary': any(m.is_primary for m in memberships),
    }


class AccessBL():
    """ What the client is allowed to show. This is a UI snapshot only - the
    backend re-checks membership, module and capability on every request. """

    def __init__(self):
        self.__da = MembershipDA()

    def get_login_access(self, user_id):
        """ Added to every login response. With one active company it is chosen
        automatically; with several the client must let the user pick and then
        call get_access with that company. """
        grouped = group_memberships_by_company(self.__da.get_active_memberships_for_user(user_id))
        companies = [_company_summary(m) for m in grouped.values()]
        single = companies[0] if len(companies) == 1 else None
        single_id = single['id'] if single else None
        return {
            # Legacy flags older clients still read at login. They can only be
            # answered once a company is known, so they are False until the user
            # has picked one (clients should read /me/access capabilities instead).
            'master_accountant': bool(single_id and has_capability(user_id, 'payroll.process', single_id)),
            'manage_assessment_menu': bool(
                single_id and has_capability(user_id, 'payroll.view_tax_periods', single_id)),
            'companies': companies,
            'active_company': {'id': single['id'], 'name': single['name']} if single else None,
            'company_selection_required': len(companies) > 1,
            'enabled_modules': sorted(get_enabled_module_codes(single['id'])) if single else [],
        }

    def get_access(self, user_id, meta):
        grouped = group_memberships_by_company(self.__da.get_active_memberships_for_user(user_id))
        companies = [_company_summary(m) for m in grouped.values()]
        try:
            active = resolve_active_company(user_id, meta)
        except CompanyContextError as error:
            result = {'error': error.message, 'code': error.code, 'status': error.status}
            if error.code in ('company_required', 'company_forbidden'):
                result['companies'] = companies  # lets the client show its company picker
            return result

        memberships = grouped[active.company_id]
        modules = get_enabled_module_codes(active.company_id)
        # Same rule as has_capability: a catalog module's capabilities count only
        # if the company enabled it; prefixes that are not modules (e.g. 'company') are kept.
        catalog = get_catalog_module_codes()
        capabilities = sorted(
            code for code in self.__da.get_effective_capability_codes(user_id, active.company_id)
            if (code.split('.')[0] not in catalog) or (code.split('.')[0] in modules))
        return {
            'company': {'id': active.company_id, 'name': active.company_name},
            'companies': companies,
            'memberships': [
                {'id': m.id, 'role': {'id': m.role_id, 'name': m.role.name},
                 'branch_id': m.branch_id, 'is_primary': m.is_primary}
                for m in memberships
            ],
            'modules': sorted(modules),
            'capabilities': capabilities,
            'status': 200,
        }
