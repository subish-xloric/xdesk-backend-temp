from django.db import migrations

# Data-scope capabilities for rewards, same pattern as migrations 0010-0012.
# rewards.view_reports already existed (0003) as a report-specific capability;
# these cover viewing/acting on individual reward nominations.
CAPABILITIES = [
    ('rewards.view_all', 'rewards', 'View and act on reward nominations company-wide'),
    ('rewards.view_team', 'rewards', 'View and act on reward nominations for own team only'),
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
        ('platform_access', '0012_seed_interview_assessment_view_scope'),
    ]

    operations = [
        migrations.RunPython(seed, unseed),
    ]
