from django.db.models import Q

from pTracker.dataaccess.attendance_v2_access.shift_models import AttendanceShift
from pTracker.dataaccess.attendance_v2_access.shift_models import AttendanceShiftSchedule
from pTracker.dataaccess.attendance_v2_access.shift_models import AttendanceShiftAssignment


class ShiftDA:

    # --- shifts -----------------------------------------------------------
    def get_shifts(self, company_id, include_inactive=False):
        shifts = AttendanceShift.objects.filter(company_id=company_id).prefetch_related('schedule')
        if not include_inactive:
            shifts = shifts.filter(is_active=True)
        return shifts.order_by('name')

    def get_shift(self, company_id, shift_id):
        return AttendanceShift.objects.filter(company_id=company_id, pk=shift_id).prefetch_related('schedule').first()

    def code_exists(self, company_id, code, exclude_id=None):
        shifts = AttendanceShift.objects.filter(company_id=company_id, code=code)
        if exclude_id:
            shifts = shifts.exclude(pk=exclude_id)
        return shifts.exists()

    def create_shift(self, **fields):
        return AttendanceShift.objects.create(**fields)

    def update_shift(self, shift, **fields):
        for key, value in fields.items():
            setattr(shift, key, value)
        shift.save()
        return shift

    def shift_in_use(self, shift_id, on_or_after):
        """ Whether an assignment still applies to the shift on or after a date. """
        return AttendanceShiftAssignment.objects.filter(shift_id=shift_id, is_active=True).filter(
            Q(effective_to__isnull=True) | Q(effective_to__gte=on_or_after)).exists()

    # --- weekly schedule --------------------------------------------------
    def replace_schedule(self, shift, rows):
        AttendanceShiftSchedule.objects.filter(shift=shift).delete()
        AttendanceShiftSchedule.objects.bulk_create(
            [AttendanceShiftSchedule(shift=shift, **row) for row in rows])
        return list(AttendanceShiftSchedule.objects.filter(shift=shift).order_by('weekday'))

    # --- assignments ------------------------------------------------------
    def _target_filter(self, scope, employee_id=None, team_lead_id=None, branch_id=None):
        return {
            'employee': {'employee_id': employee_id},
            'team': {'team_lead_id': team_lead_id},
            'branch': {'branch_id': branch_id},
            'company': {},
        }[scope]

    def get_assignments(self, company_id, filters):
        assignments = AttendanceShiftAssignment.objects.filter(company_id=company_id, is_active=True) \
            .select_related('shift', 'employee', 'team_lead', 'branch')
        if filters.get('scope'):
            assignments = assignments.filter(scope=filters['scope'])
        if filters.get('employee_id'):
            assignments = assignments.filter(employee_id=filters['employee_id'])
        if filters.get('shift_id'):
            assignments = assignments.filter(shift_id=filters['shift_id'])
        if filters.get('on_date'):
            on_date = filters['on_date']
            assignments = assignments.filter(effective_from__lte=on_date).filter(
                Q(effective_to__isnull=True) | Q(effective_to__gte=on_date))
        return assignments.order_by('scope', '-effective_from', '-id')

    def get_assignment(self, company_id, assignment_id):
        return AttendanceShiftAssignment.objects.filter(
            company_id=company_id, pk=assignment_id, is_active=True).select_related('shift').first()

    def get_target_assignments(self, company_id, scope, **target):
        """ Every active assignment of one target (employee/team/branch/company),
        oldest first - used to keep a target's history non-overlapping. """
        return list(AttendanceShiftAssignment.objects.filter(
            company_id=company_id, scope=scope, is_active=True, **self._target_filter(scope, **target),
        ).select_for_update().order_by('effective_from', 'id'))

    def create_assignment(self, **fields):
        return AttendanceShiftAssignment.objects.create(**fields)

    def update_assignment(self, assignment, **fields):
        for key, value in fields.items():
            setattr(assignment, key, value)
        assignment.save()
        return assignment

    def get_assignments_covering(self, company_id, start_date, end_date, employee_id, team_lead_ids, branch_id):
        """ Every assignment that can apply to one employee anywhere in
        [start_date, end_date]: their own, any team lead's they had in the range,
        their branch's, and the company default. One query per resolution batch. """
        target = Q(scope='employee', employee_id=employee_id) | Q(scope='company')
        if team_lead_ids:
            target |= Q(scope='team', team_lead_id__in=list(team_lead_ids))
        if branch_id:
            target |= Q(scope='branch', branch_id=branch_id)
        return list(AttendanceShiftAssignment.objects.filter(
            target, company_id=company_id, is_active=True, effective_from__lte=end_date,
        ).filter(Q(effective_to__isnull=True) | Q(effective_to__gte=start_date))
            .select_related('shift').prefetch_related('shift__schedule'))
