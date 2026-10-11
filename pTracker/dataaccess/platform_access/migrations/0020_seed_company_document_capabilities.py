from django.db import migrations

# 'company' is not a catalog module, so these are never switched off by a
# company's module settings. Granted to no role here: an admin assigns them
# per company (platform role capabilities API).
CAPABILITIES = [
    ('company.view_documents', 'company',
     'View and download the company\'s confidential documents'),
    ('company.manage_documents', 'company',
     'Upload, replace and delete company documents and the company logo; view restricted documents'),
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
        ('platform_access', '0019_company_document'),
    ]

    operations = [
        migrations.RunPython(seed, unseed),
    ]
