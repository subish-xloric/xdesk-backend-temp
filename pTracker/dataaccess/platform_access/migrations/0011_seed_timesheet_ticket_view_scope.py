from django.db import migrations

# Data-scope capabilities for timesheet and ticket, same pattern as migration 0010
# (leave, attendance): view_all() = whole company, view_team() = own team, neither =
# own records only. See data_scope() in pTracker/common/company_authorization.py.
CAPABILITIES = [
    ('timesheet.view_all', 'timesheet', 'View and act on timesheets for every employee in the company'),
    ('timesheet.view_team', 'timesheet', 'View and act on timesheets for own team only'),
    ('ticket.view_team', 'ticket', 'View and manage tickets for own team only (ticket.view_all already covers company-wide)'),
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
        ('platform_access', '0010_seed_view_scope_capabilities'),
    ]

    operations = [
        migrations.RunPython(seed, unseed),
    ]
