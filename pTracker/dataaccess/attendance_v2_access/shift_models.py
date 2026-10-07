from django.conf import settings
from django.db import models

from pTracker.dataaccess.platform_access.tenancy_models import Company
from pTracker.dataaccess.platform_access.tenancy_models import Branch
from pTracker.dataaccess.attendance_v2_access.constants import OVERTIME_BASES
from pTracker.dataaccess.attendance_v2_access.constants import OVERTIME_AFTER_SHIFT_END
from pTracker.dataaccess.attendance_v2_access.constants import ASSIGNMENT_SCOPES
from pTracker.dataaccess.attendance_v2_access.constants import WEEKDAYS
""" The following tables are created here
AttendanceShift
AttendanceShiftSchedule
AttendanceShiftAssignment

Every value that drives an attendance decision (start/end, grace, break,
overtime, half-day thresholds, punch windows) is a column here, per company -
nothing is a code constant. An overnight shift simply has end_time <= start_time.

Assignments are never overwritten: a shift change closes the previous
assignment (effective_to) and adds a new one, so attendance for any past date
resolves to the shift that applied on that date. Scope order when resolving:
employee -> team (reporting lead, from emp_lead_mapping) -> branch -> company.
"""


class AttendanceShift(models.Model):
    company = models.ForeignKey(Company, on_delete=models.PROTECT, related_name='attendance_shifts')
    name = models.CharField(max_length=100)
    code = models.CharField(max_length=30)
    description = models.CharField(max_length=500, null=True, blank=True)
    start_time = models.TimeField()
    end_time = models.TimeField()
    expected_work_minutes = models.PositiveIntegerField()
    grace_in_minutes = models.PositiveIntegerField(default=0)
    grace_out_minutes = models.PositiveIntegerField(default=0)
    break_minutes = models.PositiveIntegerField(default=0)
    break_start = models.TimeField(null=True, blank=True)
    break_end = models.TimeField(null=True, blank=True)
    # Flexible: only worked minutes matter; no late/early marking.
    is_flexible = models.BooleanField(default=False)
    # Minimum worked minutes for "present" / "half day"; null = not applied.
    min_present_minutes = models.PositiveIntegerField(null=True, blank=True)
    half_day_minutes = models.PositiveIntegerField(null=True, blank=True)
    overtime_enabled = models.BooleanField(default=False)
    overtime_basis = models.CharField(max_length=20, choices=OVERTIME_BASES, default=OVERTIME_AFTER_SHIFT_END)
    min_overtime_minutes = models.PositiveIntegerField(default=0)
    # Punches this long before the shift start / after the shift end still
    # count towards that shift's work date.
    checkin_window_before_minutes = models.PositiveIntegerField(default=240)
    checkout_window_after_minutes = models.PositiveIntegerField(default=480)
    is_active = models.BooleanField(default=True)
    created_by = models.IntegerField(null=True, blank=True)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        db_table = 'attv2_shift'
        unique_together = ('company', 'code')

    @property
    def is_overnight(self):
        return self.end_time <= self.start_time

    def __str__(self):
        return f'{self.company_id}:{self.code}'


class AttendanceShiftSchedule(models.Model):
    """ Optional per-weekday override. A weekday with no row uses the shift's
    own timings as a working day; weekly offs are configured explicitly. """
    shift = models.ForeignKey(AttendanceShift, on_delete=models.CASCADE, related_name='schedule')
    weekday = models.PositiveSmallIntegerField(choices=WEEKDAYS)
    is_working_day = models.BooleanField(default=True)
    start_time = models.TimeField(null=True, blank=True)
    end_time = models.TimeField(null=True, blank=True)
    expected_work_minutes = models.PositiveIntegerField(null=True, blank=True)

    class Meta:
        db_table = 'attv2_shift_schedule'
        unique_together = ('shift', 'weekday')


class AttendanceShiftAssignment(models.Model):
    company = models.ForeignKey(Company, on_delete=models.PROTECT, related_name='attendance_shift_assignments')
    shift = models.ForeignKey(AttendanceShift, on_delete=models.PROTECT, related_name='assignments')
    scope = models.CharField(max_length=20, choices=ASSIGNMENT_SCOPES)
    employee = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.PROTECT, null=True, blank=True,
        related_name='attendance_shift_assignments')
    team_lead = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.PROTECT, null=True, blank=True,
        related_name='attendance_team_shift_assignments')
    branch = models.ForeignKey(Branch, on_delete=models.PROTECT, null=True, blank=True,
        related_name='attendance_shift_assignments')
    effective_from = models.DateField()
    effective_to = models.DateField(null=True, blank=True)
    is_active = models.BooleanField(default=True)
    remarks = models.CharField(max_length=500, null=True, blank=True)
    created_by = models.IntegerField(null=True, blank=True)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        db_table = 'attv2_shift_assignment'
        indexes = [
            models.Index(fields=['company', 'scope', 'effective_from'], name='attv2_assign_scope_from'),
            models.Index(fields=['employee', 'effective_from'], name='attv2_assign_emp_from'),
        ]
