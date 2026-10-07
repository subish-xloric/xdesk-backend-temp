""" The device-independent attendance engine.

    events (IN / OUT / UNSPECIFIED, any source)
        -> work date (shift-aware, handles overnight shifts)
        -> sessions (multiple IN/OUT pairs, missing IN/OUT, double punches)
        -> daily summary (work/break minutes, late, early, overtime, status)

Every rule comes from the day plan (shift snapshot, calendar, leave) and the
company's AttendanceSettings. There is no device- or company-specific branch.
"""

from collections import defaultdict
from datetime import datetime, time, timedelta

from django.db import transaction

from pTracker.api.attendance_v2.attendance_v2_helper import now_local
from pTracker.api.attendance_v2.day_plan_biz import DayPlanBL
from pTracker.api.attendance_v2.day_plan_biz import RuleSettings
from pTracker.api.attendance_v2.day_plan_biz import break_window_on
from pTracker.dataaccess.attendance_v2_access.daily_da import DailyDA
from pTracker.dataaccess.attendance_v2_access.punch_da import PunchDA
from pTracker.dataaccess.attendance_v2_access.org_da import OrgDA
from pTracker.dataaccess.attendance_v2_access.constants import PUNCH_IN
from pTracker.dataaccess.attendance_v2_access.constants import PUNCH_OUT
from pTracker.dataaccess.attendance_v2_access.constants import PUNCH_UNSPECIFIED
from pTracker.dataaccess.attendance_v2_access.constants import UNSPECIFIED_FIRST_LAST
from pTracker.dataaccess.attendance_v2_access.constants import SESSION_COMPLETE
from pTracker.dataaccess.attendance_v2_access.constants import SESSION_MISSING_IN
from pTracker.dataaccess.attendance_v2_access.constants import SESSION_MISSING_OUT
from pTracker.dataaccess.attendance_v2_access.constants import DAY_WORKING
from pTracker.dataaccess.attendance_v2_access.constants import DAY_HOLIDAY
from pTracker.dataaccess.attendance_v2_access.constants import DAY_WEEKLY_OFF
from pTracker.dataaccess.attendance_v2_access.constants import LEAVE_FULL
from pTracker.dataaccess.attendance_v2_access.constants import LEAVE_HALF
from pTracker.dataaccess.attendance_v2_access.constants import LEAVE_NONE
from pTracker.dataaccess.attendance_v2_access.constants import OVERTIME_AFTER_SHIFT_END
from pTracker.dataaccess.attendance_v2_access.constants import STATUS_PRESENT
from pTracker.dataaccess.attendance_v2_access.constants import STATUS_HALF_DAY
from pTracker.dataaccess.attendance_v2_access.constants import STATUS_ABSENT
from pTracker.dataaccess.attendance_v2_access.constants import STATUS_LEAVE
from pTracker.dataaccess.attendance_v2_access.constants import STATUS_HOLIDAY
from pTracker.dataaccess.attendance_v2_access.constants import STATUS_WEEKLY_OFF
from pTracker.dataaccess.attendance_v2_access.constants import STATUS_INCOMPLETE
from pTracker.dataaccess.attendance_v2_access.constants import STATUS_NOT_STARTED

# Synchronous reprocess limit (employees x days); bigger jobs use the
# process_attendance_v2 management command.
MAX_SYNC_EMPLOYEE_DAYS = 5000


def _minutes(delta):
    return max(int(delta.total_seconds() // 60), 0)


def _overlap_minutes(a_start, a_end, b_start, b_end):
    start, end = max(a_start, b_start), min(a_end, b_end)
    return _minutes(end - start) if end > start else 0


# --- pure rules (no DB) ----------------------------------------------------

def pair_events(events, rules):
    """ Turns one work date's events (time ordered) into sessions.
    Returns (sessions, ignored_count); a session is a dict with check_in_event /
    check_out_event (either may be None) and status. """
    window = timedelta(minutes=rules.duplicate_punch_window_minutes)
    accepted, ignored = [], 0
    for event in events:
        if accepted:
            previous = accepted[-1]
            same_or_undirected = event.event_type == previous.event_type or \
                PUNCH_UNSPECIFIED in (event.event_type, previous.event_type)
            if same_or_undirected and event.event_time - previous.event_time <= window:
                ignored += 1
                continue
        accepted.append(event)

    if not accepted:
        return [], ignored

    all_undirected = all(e.event_type == PUNCH_UNSPECIFIED for e in accepted)
    if all_undirected and rules.unspecified_punch_mode == UNSPECIFIED_FIRST_LAST:
        if len(accepted) == 1:
            return [_session(accepted[0], None)], ignored
        return [_session(accepted[0], accepted[-1])], ignored + len(accepted) - 2

    sessions, open_in = [], None
    for event in accepted:
        direction = event.event_type
        if direction == PUNCH_UNSPECIFIED:
            direction = PUNCH_OUT if open_in else PUNCH_IN
        if direction == PUNCH_IN:
            if open_in:
                sessions.append(_session(open_in, None))
            open_in = event
        elif open_in:
            sessions.append(_session(open_in, event))
            open_in = None
        else:
            sessions.append(_session(None, event))
    if open_in:
        sessions.append(_session(open_in, None))
    return sessions, ignored


def _session(check_in_event, check_out_event):
    if check_in_event and check_out_event:
        status = SESSION_COMPLETE
    elif check_in_event:
        status = SESSION_MISSING_OUT
    else:
        status = SESSION_MISSING_IN
    return {'check_in_event': check_in_event, 'check_out_event': check_out_event, 'status': status}


def summarize(plan, sessions, now):
    """ Daily figures and status from the sessions and the day plan. """
    snapshot = plan.snapshot or {}
    complete = [s for s in sessions if s['status'] == SESSION_COMPLETE]
    gross = sum(_minutes(s['check_out_event'].event_time - s['check_in_event'].event_time) for s in complete)

    breaks = 0
    timed = [s for s in sessions if s['check_in_event'] or s['check_out_event']]
    for earlier, later in zip(timed, timed[1:]):
        if earlier['check_out_event'] and later['check_in_event']:
            breaks += _minutes(later['check_in_event'].event_time - earlier['check_out_event'].event_time)

    # Unpunched break: the configured break window (time worked inside it is
    # not counted), or else the configured break length minus breaks taken.
    unpaid_break = 0
    break_minutes = snapshot.get('break_minutes') or 0
    if break_minutes and complete:
        window = break_window_on(snapshot, plan.work_date, plan.start_dt) if plan.start_dt else None
        if window:
            unpaid_break = sum(_overlap_minutes(s['check_in_event'].event_time, s['check_out_event'].event_time,
                                                *window) for s in complete)
        elif gross > break_minutes:
            unpaid_break = max(break_minutes - breaks, 0)
    work = max(gross - unpaid_break, 0)

    first_in = next((s['check_in_event'] for s in sessions if s['check_in_event']), None)
    last_session = sessions[-1] if sessions else None
    last_out = last_session['check_out_event'] if last_session else None
    has_missing = any(s['status'] != SESSION_COMPLETE for s in sessions)

    result = {
        'total_work_minutes': work,
        'total_break_minutes': breaks,
        'expected_work_minutes': plan.expected_work_minutes,
        'first_in': first_in.event_time if first_in else None,
        'last_out': last_out.event_time if last_out else None,
        'first_in_location_id': first_in.location_id if first_in else None,
        'last_out_location_id': last_out.location_id if last_out else None,
        'session_count': len(sessions),
        'has_missing_punch': has_missing,
        'late_minutes': 0, 'early_departure_minutes': 0, 'overtime_minutes': 0,
        'is_late': False, 'is_early_departure': False,
    }
    remarks = []
    working_day = plan.day_type == DAY_WORKING and plan.leave_portion != LEAVE_FULL
    timed_rules = bool(snapshot) and working_day and not snapshot.get('is_flexible') \
        and plan.leave_portion == LEAVE_NONE

    if timed_rules and first_in:
        grace_end = plan.start_dt + timedelta(minutes=snapshot['grace_in_minutes'])
        if first_in.event_time > grace_end:
            result['late_minutes'] = _minutes(first_in.event_time - plan.start_dt)
            result['is_late'] = True
    if timed_rules and last_out:
        grace_start = plan.end_dt - timedelta(minutes=snapshot['grace_out_minutes'])
        if last_out.event_time < grace_start:
            result['early_departure_minutes'] = _minutes(plan.end_dt - last_out.event_time)
            result['is_early_departure'] = True

    if snapshot.get('overtime_enabled') and work:
        if not working_day:
            overtime = work
        elif snapshot['overtime_basis'] == OVERTIME_AFTER_SHIFT_END:
            overtime = _minutes(last_out.event_time - plan.end_dt) if last_out and plan.end_dt else 0
        else:
            overtime = max(work - plan.expected_work_minutes, 0)
        if overtime >= (snapshot.get('min_overtime_minutes') or 0):
            result['overtime_minutes'] = overtime

    result['status'] = _status(plan, sessions, work, has_missing, now, remarks)
    if not plan.snapshot:
        remarks.append('No shift assigned')
    if plan.leave_portion == LEAVE_HALF:
        remarks.append('Half-day leave')
    if plan.leave_portion == LEAVE_FULL and sessions:
        remarks.append('Worked on a leave day')
    result['remarks'] = '; '.join(remarks) or None
    return result


def _status(plan, sessions, work, has_missing, now, remarks):
    if not sessions:
        if plan.day_type == DAY_HOLIDAY:
            return STATUS_HOLIDAY
        if plan.day_type == DAY_WEEKLY_OFF:
            return STATUS_WEEKLY_OFF
        if plan.leave_portion == LEAVE_FULL:
            return STATUS_LEAVE
        if now < plan.window_end:
            return STATUS_NOT_STARTED
        return STATUS_ABSENT

    if has_missing:
        if now < plan.window_end:
            return STATUS_PRESENT       # day still in progress
        remarks.append('Missing punch')
        return STATUS_INCOMPLETE

    if plan.day_type != DAY_WORKING:
        return STATUS_PRESENT
    snapshot = plan.snapshot or {}
    scale = 2 if plan.leave_portion == LEAVE_HALF else 1
    min_present = snapshot.get('min_present_minutes')
    half_day = snapshot.get('half_day_minutes')
    if min_present is None or work >= min_present // scale:
        return STATUS_PRESENT
    if half_day is not None and work >= half_day // scale:
        return STATUS_HALF_DAY
    remarks.append('Below minimum working minutes')
    return STATUS_ABSENT


# --- orchestration (DB) ----------------------------------------------------

class AttendanceProcessorBL:

    def __init__(self, company):
        self.company = company
        self.__daily_da = DailyDA()
        self.__punch_da = PunchDA()
        self.rules = RuleSettings.from_row(self.__daily_da.get_settings(company.id))

    def planner(self, employee_id, start_date, end_date, refresh_shift=False):
        """ Past dates keep the shift rules they were first calculated with;
        today and later always re-resolve (an assignment made today applies). """
        stored = {}
        if not refresh_shift:
            today = now_local().date()
            stored = {d: s for d, s in self.__daily_da.get_stored_snapshots(
                self.company.id, employee_id, start_date - timedelta(days=2), end_date + timedelta(days=2),
            ).items() if d < today}
        return DayPlanBL(self.company, employee_id, self.rules, start_date, end_date, stored)

    def process_new_events(self, events):
        """ After events were added: give each a work date and rebuild the
        affected employee/dates. Returns the number of days rebuilt. """
        by_employee = defaultdict(list)
        for event in events:
            by_employee[event.employee_id].append(event)
        rebuilt = 0
        for employee_id, employee_events in by_employee.items():
            dates = [e.event_time.date() for e in employee_events]
            planner = self.planner(employee_id, min(dates), max(dates))
            affected = set()
            for event in employee_events:
                work_date = planner.work_date_for(event.event_time)
                if event.attendance_date:
                    affected.add(event.attendance_date)
                if event.attendance_date != work_date:
                    self.__punch_da.set_event_dates([event.id], work_date)
                    event.attendance_date = work_date
                affected.add(work_date)
            for work_date in sorted(affected):
                self.process_day(employee_id, work_date, planner)
                rebuilt += 1
        return rebuilt

    def reprocess(self, employee_ids, start_date, end_date, refresh_shift=False):
        """ Re-derives work dates for every event around the range, then rebuilds
        every day in the range (creating absent/leave/holiday rows as needed). """
        days = (end_date - start_date).days + 1
        if len(employee_ids) * days > MAX_SYNC_EMPLOYEE_DAYS:
            raise ValueError(f'Too many employee-days ({len(employee_ids) * days}); narrow the range '
                             f'or use the process_attendance_v2 command')
        today = now_local().date()
        rebuilt = 0
        for employee_id in employee_ids:
            planner = self.planner(employee_id, start_date, end_date, refresh_shift)
            start_dt = datetime.combine(start_date - timedelta(days=1), time.min)
            end_dt = datetime.combine(end_date + timedelta(days=2), time.min)
            affected = set()
            for event in self.__punch_da.get_active_events_between(self.company.id, employee_id, start_dt, end_dt):
                work_date = planner.work_date_for(event.event_time)
                if event.attendance_date != work_date:
                    if event.attendance_date:
                        affected.add(event.attendance_date)
                    self.__punch_da.set_event_dates([event.id], work_date)
                affected.add(work_date)
            current = start_date
            while current <= end_date:
                affected.add(current)
                current += timedelta(days=1)
            for work_date in sorted(d for d in affected if d <= today):
                self.process_day(employee_id, work_date, planner)
                rebuilt += 1
        return rebuilt

    def process_company_day(self, work_date):
        """ Nightly: finalize one date for every active member of the company. """
        members = sorted(OrgDA().get_member_ids(self.company.id))
        for employee_id in members:
            self.reprocess([employee_id], work_date, work_date)
        return len(members)

    def process_day(self, employee_id, work_date, planner):
        now = now_local()
        with transaction.atomic():
            daily = self.__daily_da.lock_daily(self.company.id, employee_id, work_date,
                                               defaults={'status': STATUS_NOT_STARTED, 'processed_at': now})
            plan = planner.plan(work_date)
            events = self.__punch_da.get_active_events_for_date(self.company.id, employee_id, work_date)
            # Nothing to record: no punches and either no shift (no basis for
            # absent/off) or a date that has not started yet.
            if not events and (plan.snapshot is None or work_date > now.date()):
                self.__daily_da.delete_daily(daily)
                return None

            sessions, ignored = pair_events(events, self.rules)
            summary = summarize(plan, sessions, now)
            if ignored:
                note = f'{ignored} duplicate punch(es) ignored'
                summary['remarks'] = f"{summary['remarks']}; {note}" if summary['remarks'] else note

            self.__daily_da.save_daily(
                daily, shift_id=plan.shift_id, shift_snapshot=plan.snapshot, day_type=plan.day_type,
                leave_portion=plan.leave_portion, processed_at=now, **summary)
            self.__daily_da.replace_sessions(daily, [self._session_row(employee_id, work_date, i, s)
                                                     for i, s in enumerate(sessions, start=1)])
            return daily

    def _session_row(self, employee_id, work_date, sequence, session):
        check_in, check_out = session['check_in_event'], session['check_out_event']
        duration = _minutes(check_out.event_time - check_in.event_time) if check_in and check_out else 0
        return {
            'company_id': self.company.id,
            'employee_id': employee_id,
            'attendance_date': work_date,
            'sequence': sequence,
            'check_in': check_in.event_time if check_in else None,
            'check_out': check_out.event_time if check_out else None,
            'check_in_location_id': check_in.location_id if check_in else None,
            'check_out_location_id': check_out.location_id if check_out else None,
            'check_in_event_id': check_in.id if check_in else None,
            'check_out_event_id': check_out.id if check_out else None,
            'duration_minutes': duration,
            'status': session['status'],
        }
