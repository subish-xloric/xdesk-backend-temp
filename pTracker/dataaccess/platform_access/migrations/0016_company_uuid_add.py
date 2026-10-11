from django.db import migrations, models


class Migration(migrations.Migration):
    """ Step 1 of 3: nullable and not unique, so existing rows can be added
    without all receiving the same default value. """

    dependencies = [
        ('platform_access', '0015_company_leave_sandwich_rule'),
    ]

    operations = [
        migrations.AddField(
            model_name='company',
            name='uuid',
            field=models.UUIDField(null=True, editable=False),
        ),
    ]
