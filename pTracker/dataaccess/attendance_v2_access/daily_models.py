from django.conf import settings
from django.db import models

from pTracker.dataaccess.platform_access.tenancy_models import Company
from pTracker.dataaccess.attendance_v2_access.location_models import AttendanceLocation
from pTracker.dataaccess.attendance_v2_access.punch_models import AttendanceEvent
from pTracker.dataaccess.attendance_v2_access.shift_models import AttendanceShift
from pTracker.dataaccess.attendance_v2_access.constants import SESSION_STATUSES
from pTracker.dataaccess.attendance_v2_access.constants import DAY_TYPES
from pTracker.dataaccess.attendance_v2_access.constants import DAY_WORKING
from pTracker.dataaccess.attendance_v2_access.constants import DAILY_STATUSES
from pTracker.dataaccess.attendance_v2_access.constants import LEAVE_PORTIONS
from pTracker.dataaccess.attendance_v2_access.constants import LEAVE_NONE
from pTracker.dataaccess.attendance_v2_access.constants import UNSPECIFIED_MODES
from pTracker.dataaccess.attendance_v2_access.constants import UNSPECIFIED_ALTERNATE
""" The following tables are created here
EmployeeDailyAttendance
AttendanceSession
AttendanceSettings

Sessions and the daily summary are derived data: the engine rebuilds them for
an employee/work date from that date's active events. The daily row keeps a
snapshot of the shift rules it was calculated with (shift_snapshot) so a later
edit to the shift does not silently change historical results.
"""


class EmployeeDailyAttendance(models.Model):
    company = models.ForeignKey(Company, on_delete=models.PROTECT, related_name='attendance_daily')
    employee = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.PROTECT,
        related_name='attendance_v2_daily')
    attendance_date = models.DateField()
    shift = models.ForeignKey(AttendanceShift, on_delete=models.SET_NULL, null=True, blank=True,
        related_name='daily_attendance')
    shift_snapshot = models.JSONField(null=True, blank=True)
    day_type = models.CharField(max_length=20, choices=DAY_TYPES, default=DAY_WORKING)
    leave_portion = models.CharField(max_length=10, choices=LEAVE_PORTIONS, default=LEAVE_NONE)
    status = models.CharField(max_length=20, choices=DAILY_STATUSES)
    first_in = models.DateTimeField(null=True, blank=True)
    last_out = models.DateTimeField(null=True, blank=True)
    first_in_location = models.ForeignKey(AttendanceLocation, on_delete=models.SET_NULL, null=True,
        blank=True, related_name='+')
    last_out_location = models.ForeignKey(AttendanceLocation, on_delete=models.SET_NULL, null=True,
        blank=True, related_name='+')
    total_work_minutes = models.IntegerField(default=0)
    total_break_minutes = models.IntegerField(default=0)
    expected_work_minutes = models.IntegerField(default=0)
    late_minutes = models.IntegerField(default=0)
    early_departure_minutes = models.IntegerField(default=0)
    overtime_minutes = models.IntegerField(default=0)
    is_late = models.BooleanField(default=False)
    is_early_departure = models.BooleanField(default=False)
    session_count = models.IntegerField(default=0)
    has_missing_punch = models.BooleanField(default=False)
    remarks = models.CharField(max_length=500, null=True, blank=True)
    processed_at = models.DateTimeField()
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        db_table = 'attv2_daily_attendance'
        unique_together = ('company', 'employee', 'attendance_date')
        indexes = [
            models.Index(fields=['company', 'attendance_date', 'status'], name='attv2_daily_date_status'),
        ]


class AttendanceSession(models.Model):
    company = models.ForeignKey(Company, on_delete=models.PROTECT, related_name='attendance_sessions')
    employee = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.PROTECT,
        related_name='attendance_v2_sessions')
    daily = models.ForeignKey(EmployeeDailyAttendance, on_delete=models.CASCADE, related_name='sessions')
    attendance_date = models.DateField()
    sequence = models.PositiveSmallIntegerField()
    check_in = models.DateTimeField(null=True, blank=True)
    check_out = models.DateTimeField(null=True, blank=True)
    check_in_location = models.ForeignKey(AttendanceLocation, on_delete=models.SET_NULL, null=True,
        blank=True, related_name='+')
    check_out_location = models.ForeignKey(AttendanceLocation, on_delete=models.SET_NULL, null=True,
        blank=True, related_name='+')
    check_in_event = models.ForeignKey(AttendanceEvent, on_delete=models.SET_NULL, null=True, blank=True,
        related_name='+')
    check_out_event = models.ForeignKey(AttendanceEvent, on_delete=models.SET_NULL, null=True, blank=True,
        related_name='+')
    duration_minutes = models.IntegerField(default=0)
    status = models.CharField(max_length=20, choices=SESSION_STATUSES)

    class Meta:
        db_table = 'attv2_session'
        indexes = [
            models.Index(fields=['company', 'employee', 'attendance_date'], name='attv2_session_emp_date'),
        ]


class AttendanceSettings(models.Model):
    """ Company-wide attendance rules that are not tied to a shift. One row per
    company; defaults apply until an admin saves settings. """
    company = models.OneToOneField(Company, on_delete=models.CASCADE, related_name='attendance_settings')
    # Punches closer together than this (same direction, or undirected) are
    # treated as one accidental double punch.
    duplicate_punch_window_minutes = models.PositiveIntegerField(default=2)
    unspecified_punch_mode = models.CharField(max_length=20, choices=UNSPECIFIED_MODES,
        default=UNSPECIFIED_ALTERNATE)
    # Collector is shown as offline when silent for longer than this.
    collector_offline_after_minutes = models.PositiveIntegerField(default=15)
    # Legacy calendars (holidays/additional_working_days/leaves) are consulted.
    use_holiday_calendar = models.BooleanField(default=True)
    use_leave_records = models.BooleanField(default=True)
    updated_by = models.IntegerField(null=True, blank=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        db_table = 'attv2_settings'
