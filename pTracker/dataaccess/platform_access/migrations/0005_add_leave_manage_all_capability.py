from django.db import migrations

CAPABILITY = ('leave.manage_all', 'leave', 'View and manage leave for all employees (company-wide admin gate)')


def seed(apps, schema_editor):
    Capability = apps.get_model('platform_access', 'Capability')
    code, module, description = CAPABILITY
    Capability.objects.get_or_create(code=code, defaults={'module': module, 'description': description})


def unseed(apps, schema_editor):
    Capability = apps.get_model('platform_access', 'Capability')
    Capability.objects.filter(code=CAPABILITY[0]).delete()


class Migration(migrations.Migration):

    dependencies = [
        ('platform_access', '0004_company_legacy_company_id'),
    ]

    operations = [
        migrations.RunPython(seed, unseed),
    ]
