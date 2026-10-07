from django.db import models

from pTracker.dataaccess.platform_access.tenancy_models import Company
""" The following tables are created here
AttendanceAuditLog

The project has no structured audit framework (the generic `Logs` table holds
free-text error/debug messages only), so V2 keeps its own change log for
configuration changes, shift assignments and manual corrections. Secrets
(collector keys) are never written here.
"""


class AttendanceAuditLog(models.Model):
    company = models.ForeignKey(Company, on_delete=models.PROTECT, related_name='attendance_audit_logs')
    entity_type = models.CharField(max_length=40)
    entity_id = models.IntegerField(null=True, blank=True)
    action = models.CharField(max_length=40)
    old_values = models.JSONField(null=True, blank=True)
    new_values = models.JSONField(null=True, blank=True)
    remarks = models.CharField(max_length=500, null=True, blank=True)
    changed_by = models.IntegerField(null=True, blank=True)
    changed_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        db_table = 'attv2_audit_log'
        indexes = [
            models.Index(fields=['company', 'entity_type', 'entity_id'], name='attv2_audit_entity'),
            models.Index(fields=['company', 'changed_at'], name='attv2_audit_changed'),
        ]
