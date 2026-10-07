""" Nightly finalization for Attendance V2, shared by the Celery task and the
process_attendance_v2 management command: builds every active employee's
daily row for a date (absent / leave / holiday / weekly off / incomplete),
for every active company that has the attendance module enabled. """

from pTracker.api.attendance_v2.processing_biz import AttendanceProcessorBL
from pTracker.common.company_modules import get_enabled_module_codes
from pTracker.common.exception_handler import ExceptionHandler
from pTracker.common.logs import Logs
from pTracker.dataaccess.platform_access.tenancy_models import Company


class AttendanceDailyJobBL:

    def run(self, work_date, company_ids=None):
        """ Returns {company_id: employees processed | 'error'}; one company
        failing does not stop the others. """
        results = {}
        companies = Company.objects.filter(is_active=True)
        if company_ids:
            companies = companies.filter(pk__in=company_ids)
        for company in companies.order_by('id'):
            if 'attendance' not in get_enabled_module_codes(company.id):
                continue
            try:
                results[company.id] = AttendanceProcessorBL(company).process_company_day(work_date)
            except Exception:
                Logs().error(f'[attendance_v2] daily job failed company={company.id} date={work_date} '
                             f'{ExceptionHandler().get_exception()}')
                results[company.id] = 'error'
        return results
