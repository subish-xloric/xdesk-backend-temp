from django.core.management.base import BaseCommand
from django.db import connection

# pTracker/dataaccess/ptracker_access has no Django migration history (123
# models, never migrated - see leave_models.py). Rather than introduce
# migrations to that whole app just to add 2 columns to 4 tables, this adds
# them directly via idempotent raw SQL, matching how this app's schema has
# always been managed outside Django. The corresponding Django model fields
# (leave_models.py) are added separately, marked managed=False.
TABLES = ['leave_requests', 'leaves', 'compensatory_leave_request', 'leave_quota']
COLUMNS = [
    ('company_id', 'BIGINT NULL'),
    ('branch_id', 'BIGINT NULL'),
]


class Command(BaseCommand):
    help = ('One-off: add nullable company_id/branch_id columns to the Leave module\'s '
            'transactional tables. Idempotent - checks information_schema before altering, '
            'safe to re-run.')

    def handle(self, *args, **options):
        db_name = connection.settings_dict['NAME']
        with connection.cursor() as cursor:
            for table in TABLES:
                cursor.execute(
                    "SELECT column_name FROM information_schema.columns "
                    "WHERE table_schema = %s AND table_name = %s",
                    [db_name, table],
                )
                existing_columns = {row[0] for row in cursor.fetchall()}

                for column, ddl_type in COLUMNS:
                    if column in existing_columns:
                        self.stdout.write(f'{table}.{column}: already exists, skipping')
                        continue
                    cursor.execute(f'ALTER TABLE {table} ADD COLUMN {column} {ddl_type}')
                    self.stdout.write(self.style.SUCCESS(f'{table}.{column}: added'))
