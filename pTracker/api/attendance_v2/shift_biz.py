""" Shift management: shifts, weekly schedules, shift assignments (with full
history) and the computed shift calendar.

Assignments are never overwritten. Assigning a new shift from date D closes the
target's running assignment on D-1; if the old assignment was meant to run past
the new one's end, its remainder is re-created after it, so a temporary change
does not lose the original shift. Past days keep the rules recorded on their
daily rows; use reprocess with refresh_shift to recalculate them on purpose.
"""

from datetime import timedelta

from django.db import transaction

from pTracker.api.attendance_v2.attendance_v2_helper import active_company_id
from pTracker.api.attendance_v2.attendance_v2_helper import require_capability
from pTracker.api.attendance_v2.attendance_v2_helper import can
from pTracker.api.attendance_v2.attendance_v2_helper import guarded
from pTracker.api.attendance_v2.attendance_v2_helper import first_error_message
from pTracker.api.attendance_v2.attendance_v2_helper import ensure_employee_visible
from pTracker.api.attendance_v2.attendance_v2_helper import date_range_from_query
from pTracker.api.attendance_v2.attendance_v2_helper import parse_query_int
from pTracker.api.attendance_v2.attendance_v2_helper import parse_query_date
from pTracker.api.attendance_v2.attendance_v2_helper import today_local
from pTracker.api.attendance_v2.attendance_v2_helper import fmt_time
from pTracker.api.attendance_v2.attendance_v2_helper import fmt_date
from pTracker.api.attendance_v2.attendance_v2_helper import V2Error
from pTracker.api.attendance_v2.attendance_v2_helper import CAP_MANAGE_SHIFTS
from pTracker.api.attendance_v2.audit_biz import record_audit
from pTracker.api.attendance_v2.audit_biz import snapshot_fields
from pTracker.api.attendance_v2.processing_biz import AttendanceProcessorBL
from pTracker.api.attendance_v2.serializers import ShiftSerializer
from pTracker.api.attendance_v2.serializers import ScheduleSerializer
from pTracker.api.attendance_v2.serializers import AssignmentSerializer
from pTracker.api.attendance_v2.serializers import AssignmentEndSerializer
from pTracker.api.attendance_v2.serializers import SettingsSerializer
from pTracker.api.attendance_v2.day_plan_biz import RuleSettings
from pTracker.dataaccess.attendance_v2_access.shift_da import ShiftDA
from pTracker.dataaccess.attendance_v2_access.daily_da import DailyDA
from pTracker.dataaccess.attendance_v2_access.org_da import OrgDA
from pTracker.dataaccess.attendance_v2_access.constants import SCOPE_EMPLOYEE
from pTracker.dataaccess.attendance_v2_access.constants import SCOPE_TEAM
from pTracker.dataaccess.attendance_v2_access.constants import SCOPE_BRANCH
from pTracker.dataaccess.attendance_v2_access.constants import WEEKDAYS

SHIFT_FIELDS = ('name', 'code', 'description', 'start_time', 'end_time', 'expected_work_minutes',
                'grace_in_minutes', 'grace_out_minutes', 'break_minutes', 'break_start', 'break_end',
                'is_flexible', 'min_present_minutes', 'half_day_minutes', 'overtime_enabled', 'overtime_basis',
                'min_overtime_minutes', 'checkin_window_before_minutes', 'checkout_window_after_minutes',
                'is_active')
ASSIGNMENT_FIELDS = ('shift_id', 'scope', 'employee_id', 'team_lead_id', 'branch_id', 'effective_from',
                     'effective_to', 'is_active')
SETTINGS_FIELDS = tuple(RuleSettings.__dataclass_fields__)
WEEKDAY_NAMES = dict(WEEKDAYS)
MAX_CALENDAR_DAYS = 62


def schedule_dict(row):
    return {'weekday': row.weekday, 'weekday_name': WEEKDAY_NAMES[row.weekday],
            'is_working_day': row.is_working_day, 'start_time': fmt_time(row.start_time),
            'end_time': fmt_time(row.end_time), 'expected_work_minutes': row.expected_work_minutes}


def shift_dict(shift):
    data = {field: getattr(shift, field) for field in SHIFT_FIELDS}
    for field in ('start_time', 'end_time', 'break_start', 'break_end'):
        data[field] = fmt_time(data[field])
    data['id'] = shift.id
    data['is_overnight'] = shift.is_overnight
    data['schedule'] = [schedule_dict(r) for r in sorted(shift.schedule.all(), key=lambda r: r.weekday)]
    return data


def assignment_dict(assignment, names):
    target = assignment.employee_id or assignment.team_lead_id
    return {
        'id': assignment.id,
        'shift_id': assignment.shift_id,
        'shift_code': assignment.shift.code,
        'shift_name': assignment.shift.name,
        'scope': assignment.scope,
        'employee_id': assignment.employee_id,
        'team_lead_id': assignment.team_lead_id,
        'branch_id': assignment.branch_id,
        'branch_name': assignment.branch.name if assignment.branch_id else None,
        'target_name': names.get(target, {}).get('name') if target else None,
        'effective_from': fmt_date(assignment.effective_from),
        'effective_to': fmt_date(assignment.effective_to),
        'remarks': assignment.remarks,
        'created_by': assignment.created_by,
    }


class ShiftBL:

    def __init__(self):
        self.__da = ShiftDA()

    # --- shifts -----------------------------------------------------------
    @guarded('list_shifts')
    def list_shifts(self, user_id, query):
        company_id = active_company_id(user_id)
        include_inactive = query.get('include_inactive') in ('1', 'true', 'True')
        return {'shifts': [shift_dict(s) for s in self.__da.get_shifts(company_id, include_inactive)],
                'status': 200}

    @guarded('get_shift')
    def get_shift(self, user_id, shift_id):
        company_id = active_company_id(user_id)
        return {'shift': shift_dict(self._get_shift(company_id, shift_id)), 'status': 200}

    @guarded('create_shift')
    def create_shift(self, user_id, data):
        company_id = active_company_id(user_id)
        require_capability(user_id, CAP_MANAGE_SHIFTS)
        fields = self._validated_shift(company_id, data)
        with transaction.atomic():
            shift = self.__da.create_shift(company_id=company_id, created_by=user_id, **fields)
            record_audit(company_id, user_id, 'shift', shift.id, 'create', new=snapshot_fields(shift, SHIFT_FIELDS))
        return {'shift': shift_dict(self._get_shift(company_id, shift.id)), 'status': 201}

    @guarded('update_shift')
    def update_shift(self, user_id, shift_id, data, partial=False):
        company_id = active_company_id(user_id)
        require_capability(user_id, CAP_MANAGE_SHIFTS)
        shift = self._get_shift(company_id, shift_id)
        if partial:
            data = {**{f: getattr(shift, f) for f in SHIFT_FIELDS}, **data}
        fields = self._validated_shift(company_id, data, shift)
        if fields.get('is_active') is False and self.__da.shift_in_use(shift.id, today_local()):
            raise V2Error('The shift is assigned for current or future dates; end those assignments first', 409)
        with transaction.atomic():
            old = snapshot_fields(shift, SHIFT_FIELDS)
            self.__da.update_shift(shift, **fields)
            record_audit(company_id, user_id, 'shift', shift.id, 'update', old=old,
                         new=snapshot_fields(shift, SHIFT_FIELDS))
        return {'shift': shift_dict(self._get_shift(company_id, shift.id)),
                'message': 'Saved. Already-calculated past days keep their recorded rules; reprocess with '
                           'refresh_shift to apply the change to them.', 'status': 200}

    @guarded('deactivate_shift')
    def deactivate_shift(self, user_id, shift_id):
        company_id = active_company_id(user_id)
        require_capability(user_id, CAP_MANAGE_SHIFTS)
        shift = self._get_shift(company_id, shift_id)
        if self.__da.shift_in_use(shift.id, today_local()):
            raise V2Error('The shift is assigned for current or future dates; end those assignments first', 409)
        with transaction.atomic():
            self.__da.update_shift(shift, is_active=False)
            record_audit(company_id, user_id, 'shift', shift.id, 'deactivate')
        return {'message': 'Shift deactivated', 'status': 200}

    # --- weekly schedule --------------------------------------------------
    @guarded('get_shift_schedule')
    def get_schedule(self, user_id, shift_id):
        company_id = active_company_id(user_id)
        shift = self._get_shift(company_id, shift_id)
        return {'shift_id': shift.id, 'days': shift_dict(shift)['schedule'], 'status': 200}

    @guarded('replace_shift_schedule')
    def replace_schedule(self, user_id, shift_id, data):
        """ Replaces the weekly schedule. Weekdays left out use the shift's own
        timings as working days. """
        company_id = active_company_id(user_id)
        require_capability(user_id, CAP_MANAGE_SHIFTS)
        shift = self._get_shift(company_id, shift_id)
        serializer = ScheduleSerializer(data=data)
        if not serializer.is_valid():
            raise V2Error('Validation failed', 400, first_error_message(serializer.errors))
        with transaction.atomic():
            old = [schedule_dict(r) for r in shift.schedule.all()]
            rows = self.__da.replace_schedule(shift, serializer.validated_data['days'])
            new = [schedule_dict(r) for r in rows]
            record_audit(company_id, user_id, 'shift_schedule', shift.id, 'replace', old=old, new=new)
        return {'shift_id': shift.id, 'days': new, 'status': 200}

    # --- assignments ------------------------------------------------------
    @guarded('list_assignments')
    def list_assignments(self, user_id, query):
        company_id = active_company_id(user_id)
        employee_id = parse_query_int(query.get('employee_id'), 'employee_id')
        if not can(user_id, CAP_MANAGE_SHIFTS):
            employee_id = employee_id or user_id
            ensure_employee_visible(user_id, company_id, employee_id)
            query = {**query, 'scope': SCOPE_EMPLOYEE}
        filters = {'scope': query.get('scope'), 'employee_id': employee_id,
                   'shift_id': parse_query_int(query.get('shift_id'), 'shift_id'),
                   'on_date': parse_query_date(query.get('on_date'), 'on_date')}
        assignments = list(self.__da.get_assignments(company_id, filters))
        names = OrgDA().get_user_names({a.employee_id or a.team_lead_id for a in assignments} - {None})
        return {'assignments': [assignment_dict(a, names) for a in assignments], 'status': 200}

    @guarded('create_assignment')
    def create_assignment(self, user_id, data):
        company_id = active_company_id(user_id)
        require_capability(user_id, CAP_MANAGE_SHIFTS)
        serializer = AssignmentSerializer(data=data)
        if not serializer.is_valid():
            raise V2Error('Validation failed', 400, first_error_message(serializer.errors))
        fields = dict(serializer.validated_data)
        shift = self._get_shift(company_id, fields['shift_id'])
        if not shift.is_active:
            raise V2Error('Inactive shifts cannot be assigned')
        target = self._validated_target(company_id, fields)

        new_from, new_to = fields['effective_from'], fields.get('effective_to')
        with transaction.atomic():
            existing = self.__da.get_target_assignments(company_id, fields['scope'], **target)
            for current in existing:
                starts_inside = current.effective_from >= new_from and (new_to is None or
                                                                       current.effective_from <= new_to)
                if starts_inside:
                    raise V2Error(f'An assignment for this target already starts on '
                                  f'{current.effective_from}; end or delete it first', 409)
            for current in existing:
                if current.effective_from < new_from and (current.effective_to is None or
                                                          current.effective_to >= new_from):
                    self._split_around(company_id, user_id, current, new_from, new_to)
            assignment = self.__da.create_assignment(
                company_id=company_id, shift=shift, scope=fields['scope'], effective_from=new_from,
                effective_to=new_to, remarks=fields.get('remarks') or None, created_by=user_id, **target)
            record_audit(company_id, user_id, 'shift_assignment', assignment.id, 'assign',
                         new={**snapshot_fields(assignment, ASSIGNMENT_FIELDS), 'shift_code': shift.code},
                         remarks=fields.get('remarks'))
        return self._assignment_response(company_id, assignment, 201)

    @guarded('end_assignment')
    def end_assignment(self, user_id, assignment_id, data):
        company_id = active_company_id(user_id)
        require_capability(user_id, CAP_MANAGE_SHIFTS)
        serializer = AssignmentEndSerializer(data=data)
        if not serializer.is_valid():
            raise V2Error('Validation failed', 400, first_error_message(serializer.errors))
        new_to = serializer.validated_data['effective_to']
        with transaction.atomic():
            assignment = self._get_assignment(company_id, assignment_id)
            if new_to < assignment.effective_from:
                raise V2Error('effective_to cannot be before effective_from')
            target = {'employee_id': assignment.employee_id, 'team_lead_id': assignment.team_lead_id,
                      'branch_id': assignment.branch_id}
            later = [a for a in self.__da.get_target_assignments(company_id, assignment.scope, **target)
                     if a.id != assignment.id and a.effective_from > assignment.effective_from]
            if later and new_to >= min(a.effective_from for a in later):
                raise V2Error('effective_to would overlap the next assignment of this target', 409)
            old = snapshot_fields(assignment, ASSIGNMENT_FIELDS)
            self.__da.update_assignment(assignment, effective_to=new_to)
            record_audit(company_id, user_id, 'shift_assignment', assignment.id, 'end', old=old,
                         new=snapshot_fields(assignment, ASSIGNMENT_FIELDS),
                         remarks=serializer.validated_data.get('remarks'))
        return self._assignment_response(company_id, assignment, 200)

    @guarded('delete_assignment')
    def delete_assignment(self, user_id, assignment_id):
        """ Only assignments that have not started yet can be removed; started
        ones are part of history and can only be ended. """
        company_id = active_company_id(user_id)
        require_capability(user_id, CAP_MANAGE_SHIFTS)
        assignment = self._get_assignment(company_id, assignment_id)
        if assignment.effective_from <= today_local():
            raise V2Error('This assignment has already started; set effective_to instead', 409)
        with transaction.atomic():
            old = snapshot_fields(assignment, ASSIGNMENT_FIELDS)
            self.__da.update_assignment(assignment, is_active=False)
            record_audit(company_id, user_id, 'shift_assignment', assignment.id, 'delete', old=old)
        return {'message': 'Assignment removed', 'status': 200}

    def _split_around(self, company_id, user_id, current, new_from, new_to):
        old = snapshot_fields(current, ASSIGNMENT_FIELDS)
        original_to = current.effective_to
        self.__da.update_assignment(current, effective_to=new_from - timedelta(days=1))
        record_audit(company_id, user_id, 'shift_assignment', current.id, 'end', old=old,
                     new=snapshot_fields(current, ASSIGNMENT_FIELDS), remarks='Closed by a new assignment')
        if new_to is not None and (original_to is None or original_to > new_to):
            remainder = self.__da.create_assignment(
                company_id=company_id, shift_id=current.shift_id, scope=current.scope,
                employee_id=current.employee_id, team_lead_id=current.team_lead_id, branch_id=current.branch_id,
                effective_from=new_to + timedelta(days=1), effective_to=original_to,
                remarks='Resumes after a temporary assignment', created_by=user_id)
            record_audit(company_id, user_id, 'shift_assignment', remainder.id, 'assign',
                         new=snapshot_fields(remainder, ASSIGNMENT_FIELDS),
                         remarks='Resumes after a temporary assignment')

    def _assignment_response(self, company_id, assignment, status):
        assignment = self.__da.get_assignment(company_id, assignment.id)
        names = OrgDA().get_user_names({assignment.employee_id or assignment.team_lead_id} - {None})
        response = {'assignment': assignment_dict(assignment, names), 'status': status}
        if assignment.effective_from < today_local():
            response['message'] = ('Assignment starts in the past. Days already calculated keep their recorded '
                                   'shift; reprocess them with refresh_shift to apply this assignment.')
        return response

    def _validated_target(self, company_id, fields):
        org_da = OrgDA()
        scope = fields['scope']
        if scope == SCOPE_EMPLOYEE:
            if not org_da.is_company_member(company_id, fields['employee_id']):
                raise V2Error('employee_id is not an employee of your company')
            return {'employee_id': fields['employee_id']}
        if scope == SCOPE_TEAM:
            if not org_da.is_company_member(company_id, fields['team_lead_id']):
                raise V2Error('team_lead_id is not an employee of your company')
            return {'team_lead_id': fields['team_lead_id']}
        if scope == SCOPE_BRANCH:
            if not org_da.branch_belongs_to_company(fields['branch_id'], company_id):
                raise V2Error('branch_id is not a branch of your company')
            return {'branch_id': fields['branch_id']}
        return {}

    # --- calendar ---------------------------------------------------------
    @guarded('shift_calendar')
    def calendar(self, user_id, query):
        company_id = active_company_id(user_id)
        employee_id = parse_query_int(query.get('employee_id'), 'employee_id') or user_id
        if can(user_id, CAP_MANAGE_SHIFTS):
            if not OrgDA().is_company_member(company_id, employee_id):
                raise V2Error('Employee not found', 404)
        else:
            ensure_employee_visible(user_id, company_id, employee_id)
        start, end = date_range_from_query(query, default_days=13, max_days=MAX_CALENDAR_DAYS)
        company = OrgDA().get_company(company_id)
        planner = AttendanceProcessorBL(company).planner(employee_id, start, end)
        days = []
        current = start
        while current <= end:
            plan = planner.plan(current)
            snapshot = plan.snapshot or {}
            days.append({
                'date': current.isoformat(),
                'weekday': WEEKDAY_NAMES[current.weekday()],
                'shift_id': plan.shift_id,
                'shift_code': snapshot.get('shift_code'),
                'shift_name': snapshot.get('shift_name'),
                'start_time': (snapshot.get('start_time') or '')[:5] or None,
                'end_time': (snapshot.get('end_time') or '')[:5] or None,
                'is_overnight': bool(plan.end_dt and plan.end_dt.date() > current),
                'day_type': plan.day_type,
                'leave_portion': plan.leave_portion,
                'expected_work_minutes': plan.expected_work_minutes,
            })
            current += timedelta(days=1)
        return {'employee_id': employee_id, 'days': days, 'status': 200}

    # --- helpers ----------------------------------------------------------
    def _get_shift(self, company_id, shift_id):
        shift = self.__da.get_shift(company_id, shift_id)
        if shift is None:
            raise V2Error('Shift not found', 404)
        return shift

    def _get_assignment(self, company_id, assignment_id):
        assignment = self.__da.get_assignment(company_id, assignment_id)
        if assignment is None:
            raise V2Error('Assignment not found', 404)
        return assignment

    def _validated_shift(self, company_id, data, existing=None):
        serializer = ShiftSerializer(data=data)
        if not serializer.is_valid():
            raise V2Error('Validation failed', 400, first_error_message(serializer.errors))
        fields = dict(serializer.validated_data)
        if self.__da.code_exists(company_id, fields['code'], existing.id if existing else None):
            raise V2Error(f"Shift code {fields['code']} already exists", 409)
        return fields


class SettingsBL:

    @guarded('get_settings')
    def get_settings(self, user_id):
        company_id = active_company_id(user_id)
        rules = RuleSettings.from_row(DailyDA().get_settings(company_id))
        return {'settings': {f: getattr(rules, f) for f in SETTINGS_FIELDS}, 'status': 200}

    @guarded('update_settings')
    def update_settings(self, user_id, data):
        company_id = active_company_id(user_id)
        require_capability(user_id, CAP_MANAGE_SHIFTS)
        serializer = SettingsSerializer(data=data)
        if not serializer.is_valid():
            raise V2Error('Validation failed', 400, first_error_message(serializer.errors))
        with transaction.atomic():
            old = RuleSettings.from_row(DailyDA().get_settings(company_id))
            row = DailyDA().save_settings(company_id, user_id, **serializer.validated_data)
            new = RuleSettings.from_row(row)
            record_audit(company_id, user_id, 'settings', row.id, 'update',
                         old={f: getattr(old, f) for f in SETTINGS_FIELDS},
                         new={f: getattr(new, f) for f in SETTINGS_FIELDS})
        return {'settings': {f: getattr(new, f) for f in SETTINGS_FIELDS}, 'status': 200}
