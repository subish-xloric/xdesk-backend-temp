from django.db import migrations

# Data-scope capabilities. They replace the legacy "role_id in (1, 2, 3)" (everyone)
# and "role_id == 4" (own team) checks in the leave and attendance modules; see
# data_scope() in pTracker/common/company_authorization.py. A user with view_all
# sees the whole company; with only view_team, their own team; with neither, only
# themselves. view_all wins when both are granted.
CAPABILITIES = [
    ('leave.view_all', 'leave', 'View and act on leave and comp-off for every employee in the company'),
    ('leave.view_team', 'leave', 'View and act on leave and comp-off for own team only'),
    ('attendance.view_all', 'attendance', 'View attendance and WFH for every employee in the company'),
    ('attendance.view_team', 'attendance', 'View attendance and WFH for own team only'),
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
        ('platform_access', '0009_seed_modules'),
    ]

    operations = [
        migrations.RunPython(seed, unseed),
    ]
