from django.db import models

from pTracker.dataaccess.platform_access.tenancy_models import Company
from pTracker.dataaccess.platform_access.tenancy_models import Branch
from pTracker.dataaccess.attendance_v2_access.constants import LOCATION_TYPES
""" The following tables are created here
AttendanceLocation

Self-referencing hierarchy (building -> floor -> area/room, any depth) inside
one company. A top-level location may point at an existing platform Branch so
the V2 hierarchy hangs off the office structure that already exists instead of
duplicating it.
"""


class AttendanceLocation(models.Model):
    company = models.ForeignKey(Company, on_delete=models.PROTECT, related_name='attendance_locations')
    branch = models.ForeignKey(Branch, on_delete=models.SET_NULL, null=True, blank=True,
        related_name='attendance_locations')
    parent = models.ForeignKey('self', on_delete=models.PROTECT, null=True, blank=True,
        related_name='children')
    name = models.CharField(max_length=150)
    code = models.CharField(max_length=50)
    location_type = models.CharField(max_length=20, choices=LOCATION_TYPES)
    is_active = models.BooleanField(default=True)
    created_by = models.IntegerField(null=True, blank=True)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        db_table = 'attv2_location'
        unique_together = ('company', 'code')

    def __str__(self):
        return f'{self.company_id}:{self.code}'
