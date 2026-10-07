from datetime import date, timedelta

from django.core.management.base import BaseCommand, CommandError

from pTracker.api.attendance_v2.daily_job_biz import AttendanceDailyJobBL


class Command(BaseCommand):
    help = ('Attendance V2: build/finalize daily attendance (absent, leave, holiday, weekly off, '
            'missing punches) for a date or date range. Defaults to yesterday.')

    def add_arguments(self, parser):
        parser.add_argument('--date', help='YYYY-MM-DD (default: yesterday)')
        parser.add_argument('--to-date', help='YYYY-MM-DD, process --date..--to-date inclusive')
        parser.add_argument('--company', type=int, action='append', help='platform Company.id (repeatable)')

    def handle(self, *args, **options):
        try:
            start = date.fromisoformat(options['date']) if options['date'] else date.today() - timedelta(days=1)
            end = date.fromisoformat(options['to_date']) if options['to_date'] else start
        except ValueError:
            raise CommandError('Dates must be YYYY-MM-DD')
        if end < start or (end - start).days > 92:
            raise CommandError('--to-date must be on or after --date and within 93 days')

        current = start
        while current <= end:
            results = AttendanceDailyJobBL().run(current, options['company'])
            self.stdout.write(f'{current}: {results or "no companies with attendance enabled"}')
            current += timedelta(days=1)
