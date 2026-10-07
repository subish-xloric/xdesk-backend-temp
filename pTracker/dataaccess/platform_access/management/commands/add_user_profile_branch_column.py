from django.core.management.base import BaseCommand
from django.db import connection

# user_profile lives in pTracker.dataaccess.ptracker_access, which (like the
# leave tables) has no Django migration history. Same approach as
# add_leave_company_branch_columns: idempotent raw SQL, not a Django
# migration. The corresponding model field is added separately in
# user_models.py, with UserProfile marked managed=False.
TABLE = 'user_profile'
COLUMN = ('branch_id', 'BIGINT NULL')


class Command(BaseCommand):
    help = ('One-off: add a nullable branch_id column to user_profile, so an employee\'s '
            'branch can be read directly (same pattern as the existing company_id field). '
            'Idempotent - checks information_schema before altering, safe to re-run.')

    def handle(self, *args, **options):
        db_name = connection.settings_dict['NAME']
        column, ddl_type = COLUMN
        with connection.cursor() as cursor:
            cursor.execute(
                "SELECT column_name FROM information_schema.columns "
                "WHERE table_schema = %s AND table_name = %s AND column_name = %s",
                [db_name, TABLE, column],
            )
            if cursor.fetchone():
                self.stdout.write(f'{TABLE}.{column}: already exists, skipping')
                return

            cursor.execute(f'ALTER TABLE {TABLE} ADD COLUMN {column} {ddl_type}')
            self.stdout.write(self.style.SUCCESS(f'{TABLE}.{column}: added'))
