from django.contrib.auth.models import User
from django.db.models import Q

from pTracker.dataaccess.platform_access.tenancy_models import Company
from pTracker.dataaccess.platform_access.tenancy_models import Branch
from pTracker.dataaccess.platform_access.membership_models import Membership
from pTracker.dataaccess.ptracker_access.user_models import EmployeeLeadMapping
from pTracker.dataaccess.ptracker_access.models import Holidays
from pTracker.dataaccess.ptracker_access.models import AdditionalWorkingDays
from pTracker.dataaccess.ptracker_access.models import WFHRequest
from pTracker.dataaccess.ptracker_access.leave_models import Leave

# Values of the existing leave/WFH tables (settings.LEAVE_REQUEST_STATUS /
# WFH_REQUEST_STATUS / LEAVE_DAY_TYPE).
APPROVED_STATUS = 2
LEAVE_FULL_DAY_TYPE = 1


class OrgDA:
    """ Read-only access to the existing company, employee, team and HR calendar
    tables that Attendance V2 reuses instead of duplicating. Every employee
    lookup is limited to active members of one company. """

    def get_company(self, company_id):
        return Company.objects.filter(pk=company_id, is_active=True).first()

    def get_branches(self, company_id):
        return Branch.objects.filter(company_id=company_id, is_active=True).order_by('name').values('id', 'name', 'code')

    def branch_belongs_to_company(self, branch_id, company_id):
        return Branch.objects.filter(pk=branch_id, company_id=company_id).exists()

    def _active_members(self, company_id):
        return Membership.objects.filter(
            company_id=company_id, status=Membership.STATUS_ACTIVE, user__is_active=True)

    def is_company_member(self, company_id, user_id):
        return self._active_members(company_id).filter(user_id=user_id).exists()

    def get_member_ids(self, company_id, user_ids=None):
        members = self._active_members(company_id)
        if user_ids is not None:
            members = members.filter(user_id__in=list(user_ids))
        return set(members.values_list('user_id', flat=True))

    def resolve_employee_codes(self, company_id, codes):
        """ Employee code (auth_user.username, as the legacy module and eSSL use
        it) -> user id, for active members of this company only. Codes of other
        companies' employees are indistinguishable from unknown codes. """
        rows = User.objects.filter(
            username__in=list(codes), is_active=True,
            company_memberships__company_id=company_id,
            company_memberships__status=Membership.STATUS_ACTIVE,
        ).values_list('username', 'id').distinct()
        return dict(rows)

    def get_employees(self, company_id, user_ids=None, search=None):
        members = self._active_members(company_id)
        if user_ids is not None:
            members = members.filter(user_id__in=list(user_ids))
        users = User.objects.filter(id__in=members.values('user_id'))
        if search:
            users = users.filter(Q(first_name__icontains=search) | Q(last_name__icontains=search)
                                 | Q(username__icontains=search))
        return users.order_by('first_name', 'last_name').only('id', 'username', 'first_name', 'last_name')

    def get_user_names(self, user_ids):
        users = User.objects.filter(id__in=list(user_ids)).only('id', 'username', 'first_name', 'last_name')
        return {u.id: {'name': f'{u.first_name} {u.last_name}'.strip(), 'employee_code': u.username}
                for u in users}

    def get_member_branch_id(self, company_id, user_id):
        membership = self._active_members(company_id).filter(
            user_id=user_id, branch__isnull=False).order_by('-is_primary', 'id').first()
        return membership.branch_id if membership else None

    def get_lead_history(self, user_id):
        """ [(lead_id, from_date, to_date)] of every live mapping, newest first;
        either date may be null (open-ended). """
        return list(EmployeeLeadMapping.objects.filter(emp_id=user_id, is_deleted=0)
                    .order_by('-from_date', '-id').values_list('lead_id', 'from_date', 'to_date'))

    def get_team_member_ids(self, lead_id):
        """ Same definition of "team" as the legacy attendance/leave modules. """
        return set(EmployeeLeadMapping.objects.filter(lead_id=lead_id, is_deleted=0)
                   .values_list('emp_id', flat=True))

    def get_holiday_dates(self, company_id, start_date, end_date):
        if company_id is None:
            return set()
        return set(Holidays.objects.filter(
            company_id=company_id, deleted=0, holiday_date__range=[start_date, end_date],
        ).values_list('holiday_date', flat=True))

    def get_additional_working_dates(self, company_id, start_date, end_date):
        if company_id is None:
            return set()
        return set(AdditionalWorkingDays.objects.filter(
            company_id=company_id, deleted=0, working_date__range=[start_date, end_date],
        ).values_list('working_date', flat=True))

    def get_approved_leave_days(self, user_id, start_date, end_date):
        """ {date: True if full day else False} for approved leave. """
        leaves = Leave.objects.filter(
            employee_id=user_id, status=APPROVED_STATUS, leave_date__range=[start_date, end_date],
        ).values_list('leave_date', 'leave_day_type')
        result = {}
        for leave_date, day_type in leaves:
            result[leave_date] = result.get(leave_date, False) or day_type == LEAVE_FULL_DAY_TYPE
        return result

    def has_approved_wfh(self, user_id, on_date):
        return WFHRequest.objects.filter(
            emp_id=user_id, status=APPROVED_STATUS, start_date__lte=on_date, end_date__gte=on_date,
        ).exists()
