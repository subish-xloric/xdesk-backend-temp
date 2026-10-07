""" Capability check on the company-scoped Role/Membership system
(pTracker/dataaccess/platform_access).

A user has a capability only if, in the active company: the capability's
module is enabled for that company, AND one of the user's active memberships
there grants it through its Role (active roles only) or through the
membership's extra_capabilities. Everything is scoped to one company, so
permissions from another company the user belongs to never apply.

There is no legacy fallback: no active membership means no capability.
"""

from pTracker.common.company_context import get_active_company
from pTracker.common.company_context import get_request_memo
from pTracker.common.company_modules import is_catalog_module_disabled
from pTracker.dataaccess.platform_access.membership_da import MembershipDA


def has_capability(user_id, capability_code, company_id=None):
    """ company_id defaults to the company the current request is acting for
    (set by ModuleGateMiddleware); it only applies when it belongs to user_id. """
    if company_id is None:
        active = get_active_company()
        if active is None or active.user_id != user_id:
            return False
        company_id = active.company_id

    if is_catalog_module_disabled(company_id, capability_code.split('.')[0]):
        return False

    return capability_code in _effective_capabilities(user_id, company_id)


def users_with_capability(capability_code, company_id=None):
    """ Ids of the users holding capability_code in the company (default: the
    active request's company). Same rules as has_capability, from the other side. """
    if company_id is None:
        active = get_active_company()
        if active is None:
            return []
        company_id = active.company_id

    if is_catalog_module_disabled(company_id, capability_code.split('.')[0]):
        return []

    return MembershipDA().get_user_ids_with_capability(company_id, capability_code)


def _effective_capabilities(user_id, company_id):
    """ Loaded once per request per (user, company): biz code checks in loops. """
    memo = get_request_memo()
    key = ('capabilities', user_id, company_id)
    if memo is not None and key in memo:
        return memo[key]
    codes = MembershipDA().get_effective_capability_codes(user_id, company_id)
    if memo is not None:
        memo[key] = codes
    return codes


SCOPE_ALL = 'all'
SCOPE_TEAM = 'team'


def data_scope(user_id, module, company_id=None):
    """ How much of a module's data the user may see in the active company:
    SCOPE_ALL (<module>.view_all), SCOPE_TEAM (<module>.view_team) or None
    (only their own). Replaces the old role checks of the form
    "role in (1, 2, 3)" (all) and "role == 4" (own team). """
    if has_capability(user_id, f'{module}.view_all', company_id):
        return SCOPE_ALL
    if has_capability(user_id, f'{module}.view_team', company_id):
        return SCOPE_TEAM
    return None
