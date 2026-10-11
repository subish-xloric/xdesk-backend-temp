import uuid

from django.db import migrations


def backfill_company_uuids(apps, schema_editor):
    """ Step 2 of 3: a distinct UUID for every company that has none yet.
    Primary keys and relations are untouched; existing UUIDs are kept. """
    Company = apps.get_model('platform_access', 'Company')
    for company in Company.objects.filter(uuid__isnull=True).only('pk'):
        Company.objects.filter(pk=company.pk, uuid__isnull=True).update(uuid=uuid.uuid4())


class Migration(migrations.Migration):

    dependencies = [
        ('platform_access', '0016_company_uuid_add'),
    ]

    operations = [
        # Reverse is a no-op: 0016's reverse drops the column anyway.
        migrations.RunPython(backfill_company_uuids, migrations.RunPython.noop),
    ]
