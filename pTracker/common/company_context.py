""" Resolves which company a request is acting for.

A user can hold active Memberships in several companies. The client picks one
after login and sends it on every request in the X-Company-Id header (the
platform Company.id). The header is only a request - the company is used only
if the authenticated user holds an active Membership in it, checked here on
every request so a suspended membership takes effect immediately. A user with
exactly one active company needs no header; with several, the header is
mandatory and there is no fallback to a "default" company.

The result is also held in a ContextVar for the duration of the request so the
biz layer can call has_capability() without threading `request` through.
"""

from contextvars import ContextVar
from dataclasses import dataclass

from pTracker.dataaccess.platform_access.membership_da import MembershipDA

COMPANY_HEADER = 'HTTP_X_COMPANY_ID'


class CompanyContextError(Exception):

    def __init__(self, code, message, status):
        super().__init__(message)
        self.code = code
        self.message = message
        self.status = status


@dataclass(frozen=True)
class ActiveCompany:
    user_id: int
    company_id: int
    company_name: str


_active = ContextVar('active_company', default=None)
# Per-request memo for capability lookups: biz code often checks inside loops.
_memo = ContextVar('capability_memo', default=None)


def set_active_company(active):
    _active.set(active)
    _memo.set({})


def clear_active_company():
    _active.set(None)
    _memo.set(None)


def get_request_memo():
    """ Dict that lives for the current request, or None outside one. """
    return _memo.get()


def get_active_company():
    return _active.get()


def get_active_company_id():
    active = _active.get()
    return active.company_id if active else None


def group_memberships_by_company(memberships):
    grouped = {}
    for membership in memberships:
        grouped.setdefault(membership.company_id, []).append(membership)
    return grouped


def resolve_active_company(user_id, meta):
    """ Returns the ActiveCompany for this user and request headers, or raises
    CompanyContextError (400 = company must be chosen, 403 = not allowed). """
    grouped = group_memberships_by_company(MembershipDA().get_active_memberships_for_user(user_id))
    if not grouped:
        raise CompanyContextError('no_membership', 'You have no active company membership', 403)

    requested = meta.get(COMPANY_HEADER)
    if requested in (None, ''):
        if len(grouped) > 1:
            raise CompanyContextError('company_required', 'X-Company-Id header is required', 400)
        company_id = next(iter(grouped))
    else:
        try:
            company_id = int(requested)
        except (TypeError, ValueError):
            raise CompanyContextError('company_invalid', 'X-Company-Id must be a company id', 400)
        if company_id not in grouped:
            raise CompanyContextError('company_forbidden', 'You have no active membership in this company', 403)

    company = grouped[company_id][0].company
    return ActiveCompany(user_id=user_id, company_id=company_id, company_name=company.short_name)
