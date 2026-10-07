from datetime import date, datetime, time

from pTracker.api.attendance_v2.attendance_v2_helper import active_company_id
from pTracker.api.attendance_v2.attendance_v2_helper import can
from pTracker.api.attendance_v2.attendance_v2_helper import guarded
from pTracker.api.attendance_v2.attendance_v2_helper import paginate
from pTracker.api.attendance_v2.attendance_v2_helper import parse_query_int
from pTracker.api.attendance_v2.attendance_v2_helper import fmt_dt
from pTracker.api.attendance_v2.attendance_v2_helper import V2Error
from pTracker.api.attendance_v2.attendance_v2_helper import CAP_MANAGE_DEVICES
from pTracker.api.attendance_v2.attendance_v2_helper import CAP_MANAGE_SHIFTS
from pTracker.api.attendance_v2.attendance_v2_helper import CAP_CORRECT
from pTracker.dataaccess.attendance_v2_access.audit_da import AuditDA
from pTracker.dataaccess.attendance_v2_access.org_da import OrgDA


def _jsonable(value):
    if isinstance(value, (datetime, date, time)):
        return value.isoformat()
    if isinstance(value, dict):
        return {k: _jsonable(v) for k, v in value.items()}
    if isinstance(value, (list, tuple, set)):
        return [_jsonable(v) for v in value]
    return value


def record_audit(company_id, user_id, entity_type, entity_id, action, old=None, new=None, remarks=None):
    """ Callers must never pass secrets (e.g. collector keys) in old/new. """
    AuditDA().create(company_id=company_id, entity_type=entity_type, entity_id=entity_id, action=action,
                     old_values=_jsonable(old), new_values=_jsonable(new),
                     remarks=(remarks or None) and str(remarks)[:500], changed_by=user_id)


def snapshot_fields(instance, fields):
    return {field: getattr(instance, field) for field in fields}


class AuditBL:

    @guarded('list_audit_logs')
    def list_logs(self, user_id, query):
        company_id = active_company_id(user_id)
        if not any(can(user_id, c) for c in (CAP_MANAGE_DEVICES, CAP_MANAGE_SHIFTS, CAP_CORRECT)):
            raise V2Error('You do not have permission to view the attendance audit log', 403)
        logs = AuditDA().get_logs(company_id, query.get('entity_type'), parse_query_int(query.get('entity_id'),
                                                                                       'entity_id'))
        names = {}

        def row(log):
            if log.changed_by and log.changed_by not in names:
                names.update(OrgDA().get_user_names([log.changed_by]))
            return {
                'id': log.id, 'entity_type': log.entity_type, 'entity_id': log.entity_id,
                'action': log.action, 'old_values': log.old_values, 'new_values': log.new_values,
                'remarks': log.remarks, 'changed_by': log.changed_by,
                'changed_by_name': names.get(log.changed_by, {}).get('name'),
                'changed_at': fmt_dt(log.changed_at),
            }
        return paginate(logs, query, row)
