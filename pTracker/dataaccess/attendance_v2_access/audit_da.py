from pTracker.dataaccess.attendance_v2_access.audit_models import AttendanceAuditLog


class AuditDA:

    def create(self, **fields):
        return AttendanceAuditLog.objects.create(**fields)

    def get_logs(self, company_id, entity_type=None, entity_id=None):
        logs = AttendanceAuditLog.objects.filter(company_id=company_id)
        if entity_type:
            logs = logs.filter(entity_type=entity_type)
        if entity_id:
            logs = logs.filter(entity_id=entity_id)
        return logs.order_by('-changed_at', '-id')
