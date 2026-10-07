from django.db import migrations

# Extends the starter catalog from 0003/0005. Sourced from a combined
# backend (is_permitted()/get_user_role_by_id() call sites) + frontend
# (Angular role-gated UI) audit across every module. See conversation
# history / project notes for the full evidence table per capability.
CAPABILITIES = [
    ('appraisal.view', 'appraisal', 'View appraisal forms and reports'),
    ('assessment.manage', 'assessment', 'Create, cancel, and reschedule assessments'),
    ('assessment.view_all', 'assessment', 'View all assessments and reports across the company'),
    ('attendance.view_reports', 'attendance', 'View company-wide attendance reports and analytics'),
    ('payroll.manage_ctc', 'payroll', 'Manage and modify employee CTC'),
    ('payroll.manage_tds', 'payroll', 'Manage and modify employee TDS data'),
    ('payroll.manage_tax_periods', 'payroll', 'Add, delete, and manage tax assessment periods'),
    ('payroll.view_tax_periods', 'payroll', 'View tax assessment periods'),
    ('payroll.manage_tax_claims', 'payroll', 'Approve, view, and manage employee tax claims and declarations'),
    ('induction.manage', 'induction', 'Create, update, and manage employee inductions'),
    ('induction.view', 'induction', 'View induction details'),
    ('interview.manage_candidates', 'interview', 'Create, modify, and reject candidates; release offers'),
    ('interview.view_candidates', 'interview', 'View candidate list and details'),
    ('interview.manage_interviews', 'interview', 'Create, modify, cancel, and reschedule interviews and scorecards'),
    ('interview.manage_openings', 'interview', 'Create, close, and delete career openings'),
    ('offboard.manage', 'offboard', 'Create, update, and view offboarding requests and exit forms'),
    ('offboard.terminate_employee', 'offboard', "Terminate an employee's access and records"),
    ('onboarding.manage', 'onboarding', 'Create and edit onboarding candidates'),
    ('project.view_all', 'project', 'View all projects and dashboards company-wide'),
    ('resource.manage_allocation', 'resource', 'View and manage employee-project resource allocation'),
    ('rewards.manage_nominations', 'rewards', 'Create, approve, reject, and cancel reward nominations'),
    ('rewards.view_reports', 'rewards', 'View company-wide rewards reports'),
    ('rewards.manage_tv_content', 'rewards', 'Manage TV notice board and DM Vibes content'),
    ('ticket.view_all', 'ticket', 'View and manage all tickets, not just assigned ones'),
    ('timesheet.view_reports', 'timesheet', 'View team and company-wide timesheet reports'),
    ('timesheet.manage_exceptions', 'timesheet', 'Exclude an employee from the missing-timesheet login block'),
    ('employee.manage', 'employee', 'Create and edit employee records; manage login access'),
    ('employee.view_list', 'employee', 'View the employee list and detail profiles'),
    ('employee.approve_profile_changes', 'employee', 'Approve or reject employee-submitted profile changes'),
    ('wiki.manage_content', 'wiki', 'Moderate, approve, and remove wiki pages and categories'),
    ('wiki.view_reports', 'wiki', 'View wiki usage statistics and reports'),
]


def seed(apps, schema_editor):
    Capability = apps.get_model('platform_access', 'Capability')
    for code, module, description in CAPABILITIES:
        Capability.objects.get_or_create(code=code, defaults={'module': module, 'description': description})


def unseed(apps, schema_editor):
    Capability = apps.get_model('platform_access', 'Capability')
    Capability.objects.filter(code__in=[c[0] for c in CAPABILITIES]).delete()


class Migration(migrations.Migration):

    dependencies = [
        ('platform_access', '0006_membership_extra_capabilities'),
    ]

    operations = [
        migrations.RunPython(seed, unseed),
    ]
