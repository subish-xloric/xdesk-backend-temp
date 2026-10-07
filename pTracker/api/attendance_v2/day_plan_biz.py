""" Works out, for one employee and one work date, which rules apply: the
shift (by assignment priority and effective dates), that weekday's schedule,
holiday / weekly off, approved leave, and the time window whose punches belong
to that date. Device-independent: it never looks at where punches came from.
"""

from dataclasses import dataclass
from datetime import datetime, time, timedelta

from pTracker.dataaccess.attendance_v2_access.org_da import OrgDA
from pTracker.dataaccess.attendance_v2_access.shift_da import ShiftDA
from pTracker.dataaccess.attendance_v2_access.constants import ASSIGNMENT_PRIORITY
from pTracker.dataaccess.attendance_v2_access.constants import SCOPE_EMPLOYEE
from pTracker.dataaccess.attendance_v2_access.constants import SCOPE_TEAM
from pTracker.dataaccess.attendance_v2_access.constants import SCOPE_BRANCH
from pTracker.dataaccess.attendance_v2_access.constants import DAY_WORKING
from pTracker.dataaccess.attendance_v2_access.constants import DAY_WEEKLY_OFF
from pTracker.dataaccess.attendance_v2_access.constants import DAY_HOLIDAY
from pTracker.dataaccess.attendance_v2_access.constants import LEAVE_NONE
from pTracker.dataaccess.attendance_v2_access.constants import LEAVE_FULL
from pTracker.dataaccess.attendance_v2_access.constants import LEAVE_HALF
from pTracker.dataaccess.attendance_v2_access.constants import UNSPECIFIED_ALTERNATE


@dataclass(frozen=True)
class RuleSettings:
    """ Company-wide rules (AttendanceSettings row, or its defaults). """
    duplicate_punch_window_minutes: int = 2
    unspecified_punch_mode: str = UNSPECIFIED_ALTERNATE
    collector_offline_after_minutes: int = 15
    use_holiday_calendar: bool = True
    use_leave_records: bool = True

    @classmethod
    def from_row(cls, row):
        if row is None:
            return cls()
        return cls(**{field: getattr(row, field) for field in cls.__dataclass_fields__})


@dataclass
class DayPlan:
    work_date: object
    snapshot: dict = None           # shift rules used for this date; None = no shift
    day_type: str = DAY_WORKING
    leave_portion: str = LEAVE_NONE
    start_dt: datetime = None
    end_dt: datetime = None
    window_start: datetime = None
    window_end: datetime = None

    @property
    def shift_id(self):
        return self.snapshot['shift_id'] if self.snapshot else None

    @property
    def expected_work_minutes(self):
        if not self.snapshot or self.day_type != DAY_WORKING or self.leave_portion == LEAVE_FULL:
            return 0
        expected = self.snapshot['expected_work_minutes']
        return expected // 2 if self.leave_portion == LEAVE_HALF else expected


def _t(value):
    return value.strftime('%H:%M:%S') if value else None


def _parse_t(value):
    return time.fromisoformat(value) if value else None


def build_snapshot(shift, work_date):
    """ The shift rules in force on work_date, with that weekday's schedule
    override applied. Stored on the daily row so later shift edits do not
    change already-calculated days unless they are explicitly recalculated. """
    override = next((row for row in shift.schedule.all() if row.weekday == work_date.weekday()), None)
    start = override.start_time if override and override.start_time else shift.start_time
    end = override.end_time if override and override.end_time else shift.end_time
    expected = override.expected_work_minutes if override and override.expected_work_minutes \
        else shift.expected_work_minutes
    return {
        'shift_id': shift.id,
        'shift_code': shift.code,
        'shift_name': shift.name,
        'is_working_day': override.is_working_day if override else True,
        'start_time': _t(start),
        'end_time': _t(end),
        'expected_work_minutes': expected,
        'grace_in_minutes': shift.grace_in_minutes,
        'grace_out_minutes': shift.grace_out_minutes,
        'break_minutes': shift.break_minutes,
        'break_start': _t(shift.break_start),
        'break_end': _t(shift.break_end),
        'is_flexible': shift.is_flexible,
        'min_present_minutes': shift.min_present_minutes,
        'half_day_minutes': shift.half_day_minutes,
        'overtime_enabled': shift.overtime_enabled,
        'overtime_basis': shift.overtime_basis,
        'min_overtime_minutes': shift.min_overtime_minutes,
        'checkin_window_before_minutes': shift.checkin_window_before_minutes,
        'checkout_window_after_minutes': shift.checkout_window_after_minutes,
    }


def shift_times_on(snapshot, work_date):
    """ (start, end) datetimes of the shift on work_date; the end rolls to the
    next day for an overnight shift (end_time <= start_time). """
    start = datetime.combine(work_date, _parse_t(snapshot['start_time']))
    end = datetime.combine(work_date, _parse_t(snapshot['end_time']))
    if end <= start:
        end += timedelta(days=1)
    return start, end


def break_window_on(snapshot, work_date, shift_start):
    if not snapshot.get('break_start') or not snapshot.get('break_end'):
        return None
    start = datetime.combine(work_date, _parse_t(snapshot['break_start']))
    if start < shift_start:
        start += timedelta(days=1)          # break after midnight in a night shift
    end = datetime.combine(start.date(), _parse_t(snapshot['break_end']))
    if end <= start:
        end += timedelta(days=1)
    return start, end


class DayPlanBL:
    """ Plans for one employee over a date range, loading assignments, lead
    history, calendar and leave once for the whole range. """

    def __init__(self, company, employee_id, rules, start_date, end_date, stored_snapshots=None):
        """ stored_snapshots: {date: shift snapshot} already saved on daily rows;
        those dates keep their recorded rules instead of re-resolving the shift. """
        self.company = company
        self.stored_snapshots = stored_snapshots or {}
        self.employee_id = employee_id
        self.rules = rules
        # Margin each side: work-date assignment looks at neighbouring days.
        self.start = start_date - timedelta(days=2)
        self.end = end_date + timedelta(days=2)
        org_da = OrgDA()
        self.lead_history = org_da.get_lead_history(employee_id)
        self.branch_id = org_da.get_member_branch_id(company.id, employee_id)
        lead_ids = {lead for lead, _, _ in self.lead_history if lead}
        self.assignments = ShiftDA().get_assignments_covering(
            company.id, self.start, self.end, employee_id, lead_ids, self.branch_id)
        if rules.use_holiday_calendar:
            self.holidays = org_da.get_holiday_dates(company.id, self.start, self.end)
        else:
            self.holidays = set()
        self.extra_working = org_da.get_additional_working_dates(company.id, self.start, self.end)
        self.leaves = org_da.get_approved_leave_days(employee_id, self.start, self.end) \
            if rules.use_leave_records else {}
        self._cache = {}

    def _lead_on(self, work_date):
        for lead_id, from_date, to_date in self.lead_history:
            if (from_date is None or from_date <= work_date) and (to_date is None or to_date >= work_date):
                return lead_id
        return None

    def resolve_shift(self, work_date):
        """ Most specific assignment in force on work_date:
        employee -> team (reporting lead on that date) -> branch -> company. """
        lead_id = self._lead_on(work_date)
        for scope in ASSIGNMENT_PRIORITY:
            matches = [a for a in self.assignments if a.scope == scope
                       and a.effective_from <= work_date
                       and (a.effective_to is None or a.effective_to >= work_date)
                       and self._targets_employee(a, scope, lead_id)]
            if matches:
                return max(matches, key=lambda a: (a.effective_from, a.id)).shift
        return None

    def _targets_employee(self, assignment, scope, lead_id):
        if scope == SCOPE_EMPLOYEE:
            return assignment.employee_id == self.employee_id
        if scope == SCOPE_TEAM:
            return lead_id is not None and assignment.team_lead_id == lead_id
        if scope == SCOPE_BRANCH:
            return self.branch_id is not None and assignment.branch_id == self.branch_id
        return True

    def plan(self, work_date):
        if work_date in self._cache:
            return self._cache[work_date]
        snapshot = self.stored_snapshots.get(work_date)
        if snapshot is None:
            shift = self.resolve_shift(work_date)
            snapshot = build_snapshot(shift, work_date) if shift else None
        plan = DayPlan(work_date=work_date, snapshot=snapshot)

        scheduled_working = snapshot['is_working_day'] if snapshot else True
        if work_date in self.holidays and work_date not in self.extra_working:
            plan.day_type = DAY_HOLIDAY
        elif not scheduled_working and work_date not in self.extra_working:
            plan.day_type = DAY_WEEKLY_OFF

        if work_date in self.leaves:
            plan.leave_portion = LEAVE_FULL if self.leaves[work_date] else LEAVE_HALF

        if snapshot:
            plan.start_dt, plan.end_dt = shift_times_on(snapshot, work_date)
            plan.window_start = plan.start_dt - timedelta(minutes=snapshot['checkin_window_before_minutes'])
            plan.window_end = plan.end_dt + timedelta(minutes=snapshot['checkout_window_after_minutes'])
        else:
            plan.window_start = datetime.combine(work_date, time.min)
            plan.window_end = plan.window_start + timedelta(days=1)
        self._cache[work_date] = plan
        return plan

    def work_date_for(self, event_time):
        """ The work date a punch belongs to. Normally its calendar date; an
        early-morning punch belongs to the previous date while it is inside
        that date's (overnight) shift window and before today's window opens,
        and a late-evening punch to the next date when it falls in that date's
        window (e.g. a shift starting just after midnight). """
        day = event_time.date()
        current = self.plan(day)
        previous = self.plan(day - timedelta(days=1))
        if event_time < previous.window_end and event_time < current.window_start:
            return previous.work_date
        following = self.plan(day + timedelta(days=1))
        if event_time >= following.window_start and event_time >= current.window_end:
            return following.work_date
        return day
