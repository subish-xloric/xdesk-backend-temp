from django.db import migrations

# Attendance V2 administration. Viewing other employees' V2 attendance reuses
# the existing attendance.view_all / attendance.view_team data scope.
CAPABILITIES = [
    ('attendance.manage_devices', 'attendance',
     'Manage attendance locations, devices and collectors; view raw punches and sync logs'),
    ('attendance.manage_shifts', 'attendance',
     'Manage shifts, weekly schedules, shift assignments and attendance rules'),
    ('attendance.correct', 'attendance',
     'Add or void attendance punches and recalculate attendance'),
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
        ('platform_access', '0013_seed_rewards_view_scope'),
    ]

    operations = [
        migrations.RunPython(seed, unseed),
    ]
