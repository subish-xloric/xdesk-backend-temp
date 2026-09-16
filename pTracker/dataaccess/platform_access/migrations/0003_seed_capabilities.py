from django.db import migrations

# Starter catalog only - exercises the new Role/Membership model end to
# end. Not a full mapping of the existing ~64 is_permitted() codenames;
# that mapping is future work once a specific module is migrated off
# auth_group/auth_permission.
CAPABILITIES = [
    ('leave.apply', 'leave', 'Apply for leave'),
    ('leave.approve', 'leave', 'Approve or reject leave requests'),
    ('attendance.manage', 'attendance', 'Manage attendance records and reports'),
    ('timesheet.approve', 'timesheet', 'Approve submitted timesheets'),
    ('payroll.process', 'payroll', 'Process and publish payslips'),
    ('payroll.view', 'payroll', 'View payroll records'),
    ('employee.view_salary', 'employee', 'View an employee\'s salary/CTC'),
    ('employee.view_pii', 'employee', 'View an employee\'s personal details'),
    ('project.manage', 'project', 'Create and manage projects'),
    ('ticket.manage', 'ticket', 'Manage tickets'),
    ('ticket.assign', 'ticket', 'Assign tickets to employees'),
    ('appraisal.manage', 'appraisal', 'Manage appraisal periods and forms'),
    ('company.manage_roles', 'company', 'Create and edit roles for the company'),
    ('company.manage_members', 'company', 'Add or edit company memberships'),
]


def seed_capabilities(apps, schema_editor):
    Capability = apps.get_model('platform_access', 'Capability')
    for code, module, description in CAPABILITIES:
        Capability.objects.get_or_create(
            code=code,
            defaults={'module': module, 'description': description},
        )


def remove_capabilities(apps, schema_editor):
    Capability = apps.get_model('platform_access', 'Capability')
    Capability.objects.filter(code__in=[c[0] for c in CAPABILITIES]).delete()


class Migration(migrations.Migration):

    dependencies = [
        ('platform_access', '0002_capability_role_membership'),
    ]

    operations = [
        migrations.RunPython(seed_capabilities, remove_capabilities),
    ]
