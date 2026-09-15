from django.conf import settings
from pTracker.wiki.data_access.wiki_models.models import WikiLogs
from pTracker.wiki.data_access.wiki_models.models import AuditLogs


class LogsDA:
    def __init__(self):
        pass

    def create(self, message, log_type):
        """
        To write application logs into `Logs`
        """
        logs = WikiLogs(message=message, log_type=log_type)
        logs.save()
        return logs.log_id


    def create_audit_logs(self, logs_data):
        # create new audit logs record
        AuditLogs.objects.create(**logs_data)
