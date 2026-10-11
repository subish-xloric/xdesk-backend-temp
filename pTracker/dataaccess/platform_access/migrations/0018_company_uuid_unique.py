import uuid

from django.db import migrations, models


class Migration(migrations.Migration):
    """ Step 3 of 3: every row has a UUID now (0017), so make it required and
    unique. New companies get one generated server-side. """

    dependencies = [
        ('platform_access', '0017_company_uuid_backfill'),
    ]

    operations = [
        migrations.AlterField(
            model_name='company',
            name='uuid',
            field=models.UUIDField(default=uuid.uuid4, editable=False, unique=True),
        ),
    ]
