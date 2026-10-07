from django.db import migrations

# Data-scope capabilities for interview and assessment, same pattern as migrations
# 0010/0011 (leave, attendance, timesheet, ticket). assessment.view_all already
# existed (0007); this adds its view_team counterpart plus both for interview.
# See data_scope() in pTracker/common/company_authorization.py.
CAPABILITIES = [
    ('interview.view_all', 'interview', 'View and act on candidates/interviews/career openings company-wide'),
    ('interview.view_team', 'interview', 'View and act on candidates/interviews/career openings for own team only'),
    ('assessment.view_team', 'assessment', 'View and manage assessments for own team only (assessment.view_all already covers company-wide)'),
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
        ('platform_access', '0011_seed_timesheet_ticket_view_scope'),
    ]

    operations = [
        migrations.RunPython(seed, unseed),
    ]
