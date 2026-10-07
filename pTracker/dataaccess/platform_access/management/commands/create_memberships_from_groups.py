from collections import Counter

from django.contrib.auth import get_user_model
from django.core.management.base import BaseCommand
from django.db import transaction

from pTracker.dataaccess.platform_access.capability_models import Capability
from pTracker.dataaccess.platform_access.membership_models import Membership
from pTracker.dataaccess.platform_access.role_models import Role
from pTracker.dataaccess.platform_access.tenancy_models import Branch
from pTracker.dataaccess.platform_access.tenancy_models import Company
from pTracker.dataaccess.ptracker_access.user_models import UserProfile

# ---------------------------------------------------------------------------
# SAMPLE MAPPING - placeholder values, to be corrected by the business.
# Edit the three tables below and re-run with --update-existing.
# ---------------------------------------------------------------------------

# Django auth Group name (legacy role) -> platform Role name, per company
# (Company.short_name). Roles come from seed_dm_group_org_structure.
GROUP_TO_ROLE = {
    'Digital Mesh': {
        'Director': 'Director',
        'HR': 'HR',
        'Manager': 'Manager',
        'Lead': 'Team Lead',
        'Developer': 'Developer',
    },
    'EM Soft': {
        'Director': 'CEO',
        'HR': 'HR Manager',
        'Manager': 'Account',
        'Lead': 'Account',
        'Developer': 'Account',
    },
}

# Role given to an employee who is in no Django group (lowest-privilege role).
UNGROUPED_ROLE = {
    'Digital Mesh': 'Developer',
    'EM Soft': 'Account',
}

# Platform Role name -> capabilities. 'module.*' expands to every capability of
# that module; '*' is the whole catalog. Roles are set to exactly this list.
BASELINE = ['leave.apply']

ROLE_CAPABILITIES = {
    'Director': ['*'],
    'CEO': ['*'],
    'HR': [
        'employee.*', 'leave.*', 'attendance.*', 'timesheet.*', 'onboarding.*', 'offboard.*',
        'induction.*', 'interview.*', 'appraisal.*', 'assessment.*', 'rewards.*', 'wiki.*',
        'payroll.view', 'company.manage_members', 'resource.manage_allocation', 'asset.*',
    ],
    'HR Manager': [
        'employee.*', 'leave.*', 'attendance.*', 'timesheet.*', 'onboarding.*', 'offboard.*',
        'induction.*', 'interview.*', 'appraisal.*', 'assessment.*', 'rewards.*', 'wiki.*',
        'payroll.view', 'company.manage_members', 'resource.manage_allocation', 'asset.*',
    ],
    'Manager': [
        'leave.*', 'attendance.*', 'timesheet.*', 'project.*', 'resource.*', 'ticket.*',
        'employee.view_list', 'employee.manage', 'appraisal.view', 'assessment.view_all',
        'rewards.view_reports', 'rewards.view_all', 'interview.view_all',
    ],
    'Team Lead': [
        *BASELINE, 'leave.approve', 'leave.report', 'leave.view_team', 'timesheet.approve', 'timesheet.view_reports',
        'timesheet.view_team', 'attendance.view_reports', 'attendance.view_team', 'project.view_all', 'ticket.*',
        'employee.view_list', 'interview.view_team', 'assessment.view_team', 'rewards.view_team',
    ],
    'Developer': [*BASELINE, 'ticket.view_all'],
    'Branch Manager': [
        *BASELINE, 'leave.report', 'attendance.view_reports', 'timesheet.view_reports',
        'payroll.view', 'payroll.view_tax_periods',
    ],
    'Account': [*BASELINE, 'payroll.*'],
}

# Capabilities granted to one employee on top of their role (Membership.extra_capabilities),
# keyed by auth_user id. Carries over exceptions that used to be hardcoded in code.
EXTRA_CAPABILITIES_BY_USER_ID = {
    7: ['leave.manage_all'],  # was `role_id == 2 or user_id == 7` in leave_biz.py ("Added Ajith as per his request")
}


class Command(BaseCommand):
    help = ('Creates a Membership for every active employee from their Django Group, and sets the '
            'capabilities of each mapped Role. Uses the SAMPLE mapping at the top of this file. '
            'Safe to re-run. Use --dry-run first.')

    def add_arguments(self, parser):
        parser.add_argument('--dry-run', action='store_true', help='Show what would change; write nothing')
        parser.add_argument('--update-existing', action='store_true',
                            help='If an employee has exactly one membership in the company and its role '
                                 'differs from the mapping, change it. Default: leave existing ones alone.')
        parser.add_argument('--profile-company-is', choices=['platform', 'legacy'], default='platform',
                            help="What user_profile.company_id holds: the platform Company.id (default) "
                                 "or the legacy 2/3 id (Company.legacy_company_id)")

    def handle(self, *args, **options):
        self.stats = Counter()
        with transaction.atomic():
            self.sync_role_capabilities()
            self.sync_memberships(options['update_existing'], options['profile_company_is'])
            if options['dry_run']:
                transaction.set_rollback(True)

        self.stdout.write('')
        for key, count in sorted(self.stats.items()):
            self.stdout.write(f'  {key}: {count}')
        prefix = 'DRY RUN - nothing written. ' if options['dry_run'] else ''
        self.stdout.write(self.style.SUCCESS(prefix + 'Done.'))

    def expand_capabilities(self, patterns):
        catalog = set(Capability.objects.values_list('code', flat=True))
        codes = set()
        for pattern in patterns:
            if pattern == '*':
                codes |= catalog
            elif pattern.endswith('.*'):
                matched = {c for c in catalog if c.startswith(pattern[:-1])}
                if not matched:
                    self.stderr.write(self.style.WARNING(f'  no capabilities match {pattern}'))
                codes |= matched
            elif pattern in catalog:
                codes.add(pattern)
            else:
                self.stderr.write(self.style.WARNING(f'  unknown capability {pattern} - skipped'))
        return codes

    def sync_role_capabilities(self):
        self.stdout.write('Role capabilities')
        for role in Role.objects.select_related('company').order_by('company_id', 'id'):
            if role.name not in ROLE_CAPABILITIES:
                self.stats['roles not in mapping (untouched)'] += 1
                continue
            wanted = self.expand_capabilities(ROLE_CAPABILITIES[role.name])
            role.capabilities.set(Capability.objects.filter(code__in=wanted))
            self.stats['roles set'] += 1
            self.stdout.write(f'  {role.company.short_name} / {role.name}: {len(wanted)} capabilities')

    def resolve_company(self, profile_company_id, source):
        field = 'id' if source == 'platform' else 'legacy_company_id'
        return Company.objects.filter(**{field: profile_company_id}, is_active=True).first()

    def sync_memberships(self, update_existing, source):
        self.stdout.write('Memberships')
        roles = {(r.company_id, r.name): r for r in Role.objects.all()}
        profiles = {p.user_id: p for p in UserProfile.objects.all()}
        users = get_user_model().objects.filter(is_active=True).prefetch_related('groups').order_by('id')

        for user in users:
            profile = profiles.get(user.id)
            company = self.resolve_company(profile.company_id, source) if profile and profile.company_id else None
            if not company:
                self.skip(user, 'no profile company / company not found')
                continue

            role = self.pick_role(user, company, roles)
            if role is None:
                continue

            branch_id = profile.branch_id if profile.branch_id and Branch.objects.filter(
                pk=profile.branch_id, company=company).exists() else None

            existing = list(Membership.objects.filter(user=user, company=company))
            if not existing:
                Membership.objects.create(user=user, company=company, role=role, branch_id=branch_id,
                                          is_primary=True, status=Membership.STATUS_ACTIVE)
                self.stats['memberships created'] += 1
                self.stdout.write(f'  + {user.email or user.username}: {company.short_name} / {role.name}')
            elif len(existing) == 1 and existing[0].role_id != role.id and update_existing:
                existing[0].role = role
                existing[0].save(update_fields=['role', 'updated_at'])
                self.stats['memberships updated'] += 1
                self.stdout.write(f'  ~ {user.email or user.username}: role -> {role.name}')
            else:
                self.stats['memberships left as is'] += 1
            self.grant_extra_capabilities(user, company)

    def grant_extra_capabilities(self, user, company):
        codes = EXTRA_CAPABILITIES_BY_USER_ID.get(user.id)
        if not codes:
            return
        capabilities = Capability.objects.filter(code__in=self.expand_capabilities(codes))
        for membership in Membership.objects.filter(user=user, company=company):
            membership.extra_capabilities.add(*capabilities)
            self.stats['extra capabilities granted'] += 1
            self.stdout.write(f'  + {user.email or user.username}: extra {sorted(codes)}')

    def pick_role(self, user, company, roles):
        groups = sorted(user.groups.all(), key=lambda g: g.id)
        if len(groups) > 1:
            self.stderr.write(self.style.WARNING(
                f'  {user.email or user.username} is in {len(groups)} groups; using "{groups[0].name}"'))
        if groups:
            role_name = GROUP_TO_ROLE.get(company.short_name, {}).get(groups[0].name)
            if not role_name:
                self.skip(user, f'group "{groups[0].name}" not mapped for {company.short_name}')
                return None
        else:
            role_name = UNGROUPED_ROLE.get(company.short_name)
            if not role_name:
                self.skip(user, f'no group and no ungrouped role for {company.short_name}')
                return None
            self.stats['users with no group (fallback role)'] += 1

        role = roles.get((company.id, role_name))
        if role is None:
            self.skip(user, f'role "{role_name}" does not exist in {company.short_name}')
        return role

    def skip(self, user, reason):
        self.stats['users skipped'] += 1
        self.stderr.write(self.style.WARNING(f'  ! skipped {user.email or user.username}: {reason}'))
