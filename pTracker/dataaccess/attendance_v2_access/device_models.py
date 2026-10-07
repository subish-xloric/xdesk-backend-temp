from django.db import models

from pTracker.dataaccess.platform_access.tenancy_models import Company
from pTracker.dataaccess.attendance_v2_access.location_models import AttendanceLocation
from pTracker.dataaccess.attendance_v2_access.constants import DEVICE_TYPES
from pTracker.dataaccess.attendance_v2_access.constants import COLLECTOR_STATUSES
from pTracker.dataaccess.attendance_v2_access.constants import COLLECTOR_STATUS_UNKNOWN
""" The following tables are created here
AttendanceDevice
AttendanceCollector (+ attv2_collector_devices)

AttendanceCollector is central configuration/monitoring for an external
collector process - NOT the collector's own storage. The collector's secret is
only ever stored as a SHA-256 hash; the plain key is shown once when issued.
The company a punch belongs to always comes from the collector row, never from
the request payload.
"""


class AttendanceDevice(models.Model):
    company = models.ForeignKey(Company, on_delete=models.PROTECT, related_name='attendance_devices')
    location = models.ForeignKey(AttendanceLocation, on_delete=models.PROTECT, null=True, blank=True,
        related_name='devices')
    name = models.CharField(max_length=150)
    code = models.CharField(max_length=50)
    device_type = models.CharField(max_length=20, choices=DEVICE_TYPES)
    serial_number = models.CharField(max_length=100, null=True, blank=True)
    ip_address = models.GenericIPAddressField(null=True, blank=True)
    # Web/mobile check-in only: require an approved work-from-home request for
    # the day (the rule the legacy web punch enforces).
    requires_wfh_approval = models.BooleanField(default=False)
    is_active = models.BooleanField(default=True)
    created_by = models.IntegerField(null=True, blank=True)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        db_table = 'attv2_device'
        unique_together = ('company', 'code')

    def __str__(self):
        return f'{self.company_id}:{self.code}'


class AttendanceCollector(models.Model):
    company = models.ForeignKey(Company, on_delete=models.PROTECT, related_name='attendance_collectors')
    devices = models.ManyToManyField(AttendanceDevice, blank=True, related_name='collectors',
        db_table='attv2_collector_devices')
    # Public identifier sent by the collector (X-Collector-Id); globally unique
    # because it is looked up before the company is known.
    collector_id = models.CharField(max_length=64, unique=True)
    name = models.CharField(max_length=150)
    collector_type = models.CharField(max_length=20, choices=DEVICE_TYPES)
    api_key_hash = models.CharField(max_length=64)
    api_key_prefix = models.CharField(max_length=12)
    key_rotated_at = models.DateTimeField(null=True, blank=True)
    version = models.CharField(max_length=50, null=True, blank=True)
    reported_status = models.CharField(max_length=20, choices=COLLECTOR_STATUSES,
        default=COLLECTOR_STATUS_UNKNOWN)
    last_seen_at = models.DateTimeField(null=True, blank=True)
    last_sync_at = models.DateTimeField(null=True, blank=True)
    last_success_at = models.DateTimeField(null=True, blank=True)
    last_error_at = models.DateTimeField(null=True, blank=True)
    last_error = models.CharField(max_length=500, null=True, blank=True)
    last_ip = models.GenericIPAddressField(null=True, blank=True)
    is_active = models.BooleanField(default=True)
    created_by = models.IntegerField(null=True, blank=True)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        db_table = 'attv2_collector'

    def __str__(self):
        return self.collector_id
