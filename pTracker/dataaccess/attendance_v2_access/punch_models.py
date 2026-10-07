from django.conf import settings
from django.db import models

from pTracker.dataaccess.platform_access.tenancy_models import Company
from pTracker.dataaccess.attendance_v2_access.location_models import AttendanceLocation
from pTracker.dataaccess.attendance_v2_access.device_models import AttendanceDevice
from pTracker.dataaccess.attendance_v2_access.device_models import AttendanceCollector
from pTracker.dataaccess.attendance_v2_access.constants import PUNCH_TYPES
from pTracker.dataaccess.attendance_v2_access.constants import PUNCH_UNSPECIFIED
from pTracker.dataaccess.attendance_v2_access.constants import RAW_STATUSES
from pTracker.dataaccess.attendance_v2_access.constants import RAW_PENDING
from pTracker.dataaccess.attendance_v2_access.constants import EVENT_STATUSES
from pTracker.dataaccess.attendance_v2_access.constants import EVENT_ACTIVE
from pTracker.dataaccess.attendance_v2_access.constants import SYNC_STATUSES
from pTracker.dataaccess.attendance_v2_access.constants import SYNC_KINDS
from pTracker.dataaccess.attendance_v2_access.constants import SYNC_KIND_PUNCHES
""" The following tables are created here
AttendanceSyncLog
AttendanceRawPunch
AttendanceEvent

Raw punch = exactly what arrived (kept for audit/troubleshooting, raw_data is
the collector's original record). Event = the normalized, device-independent
punch the attendance engine works on. (device, external_punch_id) is unique,
which is what makes collector retries idempotent.
"""


class AttendanceSyncLog(models.Model):
    company = models.ForeignKey(Company, on_delete=models.PROTECT, null=True, blank=True,
        related_name='attendance_sync_logs')
    collector = models.ForeignKey(AttendanceCollector, on_delete=models.SET_NULL, null=True, blank=True,
        related_name='sync_logs')
    device = models.ForeignKey(AttendanceDevice, on_delete=models.SET_NULL, null=True, blank=True,
        related_name='sync_logs')
    kind = models.CharField(max_length=20, choices=SYNC_KINDS, default=SYNC_KIND_PUNCHES)
    request_id = models.CharField(max_length=64)
    remote_ip = models.GenericIPAddressField(null=True, blank=True)
    status = models.CharField(max_length=20, choices=SYNC_STATUSES)
    received_count = models.IntegerField(default=0)
    accepted_count = models.IntegerField(default=0)
    duplicate_count = models.IntegerField(default=0)
    failed_count = models.IntegerField(default=0)
    errors = models.JSONField(null=True, blank=True)
    message = models.CharField(max_length=500, null=True, blank=True)
    started_at = models.DateTimeField()
    finished_at = models.DateTimeField(null=True, blank=True)

    class Meta:
        db_table = 'attv2_sync_log'
        indexes = [
            models.Index(fields=['company', 'started_at'], name='attv2_sync_company_started'),
            models.Index(fields=['collector', 'started_at'], name='attv2_sync_collector_started'),
        ]


class AttendanceRawPunch(models.Model):
    company = models.ForeignKey(Company, on_delete=models.PROTECT, related_name='attendance_raw_punches')
    collector = models.ForeignKey(AttendanceCollector, on_delete=models.PROTECT, null=True, blank=True,
        related_name='raw_punches')
    device = models.ForeignKey(AttendanceDevice, on_delete=models.PROTECT, related_name='raw_punches')
    sync_log = models.ForeignKey(AttendanceSyncLog, on_delete=models.SET_NULL, null=True, blank=True,
        related_name='raw_punches')
    employee = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.PROTECT, null=True, blank=True,
        related_name='attendance_v2_raw_punches')
    external_employee_id = models.CharField(max_length=64)
    # Collector-supplied id, or a deterministic "auto:<sha256>" fallback.
    external_punch_id = models.CharField(max_length=128)
    punch_time = models.DateTimeField()
    raw_punch_type = models.CharField(max_length=32, null=True, blank=True)
    punch_type = models.CharField(max_length=12, choices=PUNCH_TYPES, default=PUNCH_UNSPECIFIED)
    source = models.CharField(max_length=20)
    location = models.ForeignKey(AttendanceLocation, on_delete=models.SET_NULL, null=True, blank=True,
        related_name='raw_punches')
    raw_data = models.JSONField(null=True, blank=True)
    received_at = models.DateTimeField()
    status = models.CharField(max_length=24, choices=RAW_STATUSES, default=RAW_PENDING)
    error_message = models.CharField(max_length=500, null=True, blank=True)
    processed_at = models.DateTimeField(null=True, blank=True)

    class Meta:
        db_table = 'attv2_raw_punch'
        unique_together = ('device', 'external_punch_id')
        indexes = [
            models.Index(fields=['company', 'punch_time'], name='attv2_raw_company_time'),
            models.Index(fields=['company', 'status'], name='attv2_raw_company_status'),
            models.Index(fields=['employee', 'punch_time'], name='attv2_raw_employee_time'),
        ]


class AttendanceEvent(models.Model):
    company = models.ForeignKey(Company, on_delete=models.PROTECT, related_name='attendance_events')
    employee = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.PROTECT,
        related_name='attendance_v2_events')
    event_time = models.DateTimeField()
    # As received: IN / OUT, or UNSPECIFIED when the device gives no direction
    # (the engine then decides the direction from sequence and company settings).
    event_type = models.CharField(max_length=12, choices=PUNCH_TYPES, default=PUNCH_UNSPECIFIED)
    # Work date this punch counts towards (differs from event_time's date for
    # overnight shifts); set by the attendance engine.
    attendance_date = models.DateField(null=True, blank=True)
    location = models.ForeignKey(AttendanceLocation, on_delete=models.SET_NULL, null=True, blank=True,
        related_name='events')
    device = models.ForeignKey(AttendanceDevice, on_delete=models.SET_NULL, null=True, blank=True,
        related_name='events')
    source = models.CharField(max_length=20)
    raw_punch = models.OneToOneField(AttendanceRawPunch, on_delete=models.PROTECT, null=True, blank=True,
        related_name='event')
    is_manual = models.BooleanField(default=False)
    manual_reason = models.CharField(max_length=500, null=True, blank=True)
    status = models.CharField(max_length=10, choices=EVENT_STATUSES, default=EVENT_ACTIVE)
    void_reason = models.CharField(max_length=500, null=True, blank=True)
    voided_by = models.IntegerField(null=True, blank=True)
    voided_at = models.DateTimeField(null=True, blank=True)
    created_by = models.IntegerField(null=True, blank=True)
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        db_table = 'attv2_event'
        indexes = [
            models.Index(fields=['company', 'employee', 'event_time'], name='attv2_event_emp_time'),
            models.Index(fields=['company', 'employee', 'attendance_date'], name='attv2_event_emp_date'),
        ]
