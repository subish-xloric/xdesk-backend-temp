import calendar
from collections import defaultdict
from datetime import date

from pTracker.api.attendance_v2.attendance_v2_helper import active_company_id
from pTracker.api.attendance_v2.attendance_v2_helper import ensure_employee_visible
from pTracker.api.attendance_v2.attendance_v2_helper import guarded
from pTracker.api.attendance_v2.attendance_v2_helper import today_local
from pTracker.api.attendance_v2.attendance_v2_helper import V2Error
from pTracker.api.attendance_v2.processing_biz import AttendanceProcessorBL
from pTracker.dataaccess.attendance_v2_access.constants import DAY_HOLIDAY
from pTracker.dataaccess.attendance_v2_access.constants import DAY_WEEKLY_OFF
from pTracker.dataaccess.attendance_v2_access.constants import LEAVE_FULL
from pTracker.dataaccess.attendance_v2_access.constants import LEAVE_HALF
from pTracker.dataaccess.attendance_v2_access.constants import STATUS_ABSENT
from pTracker.dataaccess.attendance_v2_access.constants import STATUS_HALF_DAY
from pTracker.dataaccess.attendance_v2_access.constants import STATUS_HOLIDAY
from pTracker.dataaccess.attendance_v2_access.constants import STATUS_INCOMPLETE
from pTracker.dataaccess.attendance_v2_access.constants import STATUS_LEAVE
from pTracker.dataaccess.attendance_v2_access.constants import STATUS_NOT_STARTED
from pTracker.dataaccess.attendance_v2_access.constants import STATUS_WEEKLY_OFF
from pTracker.dataaccess.attendance_v2_access.daily_da import DailyDA
from pTracker.dataaccess.attendance_v2_access.org_da import OrgDA
from pTracker.dataaccess.attendance_v2_access.punch_da import PunchDA
from pTracker.dataaccess.ptracker_access.holiday_da import HolidayDA

DEFAULT_WORK_MINUTES = 480  # used for work_percentage when the day has no shift


class MonthlyAttendanceBL():
    """ An employee's attendance for one month, from Attendance V2, in the shape
    the legacy eSSL-based endpoints returned (one entry per day up to today).

    Access: yourself, your team (attendance.view_team) or anyone in the company
    (attendance.view_all); anyone else - including other companies' employees -
    is "Employee not found" (404). Returns {'attendance': [...], 'status'} or
    {'error', 'status'}.
    """

    @guarded('monthly_attendance')
    def get_month(self, user_id, year, month, employee_id=None):
        try:
            year, month = int(year), int(month)
            employee_id = int(employee_id) if employee_id else user_id
        except (TypeError, ValueError):
            raise V2Error('Invalid year, month or employee', 400)
        if not 1 <= month <= 12 or not 2000 <= year <= 2100:
            raise V2Error('Invalid year or month', 400)

        company_id = active_company_id(user_id)
        ensure_employee_visible(user_id, company_id, employee_id)

        start = date(year, month, 1)
        end = min(date(year, month, calendar.monthrange(year, month)[1]), today_local())
        if start > end:
            return {'attendance': [], 'status': 200}

        daily_rows = {row.attendance_date: row for row in
                      DailyDA().get_daily_list(company_id, {employee_id}, start, end)}
        punches = defaultdict(list)
        for event in PunchDA().get_events(company_id, {employee_id}, start, end, include_void=False):
            punches[event.attendance_date].append(event)
        holiday_titles = {h.holiday_date: h.title for h in HolidayDA().get_company_holidays(company_id, start, end)}
        planner = AttendanceProcessorBL(OrgDA().get_company(company_id)).planner(employee_id, start, end)

        days = []
        current = start
        while current <= end:
            row = daily_rows.get(current)
            if row is None:
                status, leave_portion = self.__unprocessed_status(planner.plan(current), current)
            else:
                status, leave_portion = row.status, row.leave_portion
            days.append(self.__day(current, status, leave_portion, row, punches.get(current, []),
                                   holiday_titles.get(current)))
            current = date.fromordinal(current.toordinal() + 1)
        return {'attendance': days, 'status': 200}

    def __unprocessed_status(self, plan, work_date):
        """ Status for a day the V2 engine hasn't written a row for yet (today,
        or before the nightly job ran), from that day's plan. """
        if plan.day_type == DAY_HOLIDAY:
            return STATUS_HOLIDAY, plan.leave_portion
        if plan.day_type == DAY_WEEKLY_OFF:
            return STATUS_WEEKLY_OFF, plan.leave_portion
        if plan.leave_portion == LEAVE_FULL:
            return STATUS_LEAVE, plan.leave_portion
        return (STATUS_NOT_STARTED if work_date == today_local() else STATUS_ABSENT), plan.leave_portion

    def __day(self, work_date, status, leave_portion, row, events, holiday_title):
        entry = {'error': '', 'date': work_date.isoformat(), 'status': status}
        if status == STATUS_HOLIDAY:
            entry.update(date_status='holiday', date_remark=holiday_title or 'Holiday')
            return entry
        if status == STATUS_WEEKLY_OFF:
            entry.update(date_status='weekend', date_remark='Weekly Off')
            return entry
        if status == STATUS_LEAVE:
            entry.update(date_status='leave', date_remark='Leave')
            return entry
        if status == STATUS_ABSENT and not events:
            entry.update(date_status='absent', date_remark='Absent')
            return entry
        if status == STATUS_NOT_STARTED and not events:
            entry.update(date_status='not_started', date_remark='')
            return entry

        remarks = []
        if leave_portion == LEAVE_HALF:
            remarks.append('Half day leave')
        if status == STATUS_HALF_DAY:
            remarks.append('Half day')
        if status == STATUS_INCOMPLETE:
            remarks.append('Missing punch')
        work_minutes = row.total_work_minutes if row else 0
        expected = (row.expected_work_minutes if row else 0) or DEFAULT_WORK_MINUTES
        late_minutes = (row.late_minutes or 0) if row else 0
        is_late = 0
        if row and row.is_late:
            is_late = 2 if work_minutes >= expected else 1
        log = [{'time': e.event_time.strftime('%I:%M %p'), 'direction': e.event_type.lower(),
                'source': e.source, 'location': e.location.name if e.location_id else None} for e in events]
        location_logs = self.__location_logs(events)
        entry.update(
            date_status='working',
            date_remark=', '.join(remarks),
            work_percentage=int(work_minutes * 100 // expected),
            effective_hours=self.__hh_mm(work_minutes),
            gross_hours=self.__gross_hours(row),
            arrival={'is_late': is_late, 'late_hours': f'{self.__hh_mm(late_minutes)} hrs late' if is_late else ''},
            log={'first_log': location_logs[0]['location_name'] if location_logs else '',
                 'punches': log, 'location_logs': location_logs},
        )
        return entry

    def __location_logs(self, events):
        """ The day's punches grouped by V2 attendance location (e.g. First Floor
        DM-CSEZ-FF, Second Floor DM-CSEZ-SF), in the order each location was first
        used; punches without a location (web / mobile remote punch) go under
        'Remote'. """
        groups = {}
        for event in events:
            key = event.location_id
            if key not in groups:
                groups[key] = {
                    'location_id': event.location_id,
                    'location_code': event.location.code if event.location_id else None,
                    'location_name': event.location.name if event.location_id else 'Remote',
                    'log': [],
                }
            groups[key]['log'].append({'time': event.event_time.strftime('%I:%M %p'),
                                       'direction': event.event_type.lower(), 'source': event.source})
        return list(groups.values())

    def __gross_hours(self, row):
        if not row or not row.first_in or not row.last_out or row.last_out <= row.first_in:
            return '00:00'
        return self.__hh_mm(int((row.last_out - row.first_in).total_seconds() // 60))

    def __hh_mm(self, minutes):
        minutes = max(int(minutes or 0), 0)
        return f'{minutes // 60:02d}:{minutes % 60:02d}'
