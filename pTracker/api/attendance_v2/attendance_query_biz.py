""" Read-side of Attendance V2. Every list is limited to the caller's company
and to the employees their attendance data scope allows (self / team / all). """

from datetime import timedelta

from pTracker.api.attendance_v2.attendance_v2_helper import active_company_id
from pTracker.api.attendance_v2.attendance_v2_helper import require_capability
from pTracker.api.attendance_v2.attendance_v2_helper import can
from pTracker.api.attendance_v2.attendance_v2_helper import guarded
from pTracker.api.attendance_v2.attendance_v2_helper import paginate
from pTracker.api.attendance_v2.attendance_v2_helper import visible_employee_ids
from pTracker.api.attendance_v2.attendance_v2_helper import narrow_employee_ids
from pTracker.api.attendance_v2.attendance_v2_helper import ensure_employee_visible
from pTracker.api.attendance_v2.attendance_v2_helper import date_range_from_query
from pTracker.api.attendance_v2.attendance_v2_helper import parse_query_int
from pTracker.api.attendance_v2.attendance_v2_helper import parse_query_date
from pTracker.api.attendance_v2.attendance_v2_helper import day_bounds
from pTracker.api.attendance_v2.attendance_v2_helper import today_local
from pTracker.api.attendance_v2.attendance_v2_helper import fmt_dt
from pTracker.api.attendance_v2.attendance_v2_helper import fmt_date
from pTracker.api.attendance_v2.attendance_v2_helper import CAP_MANAGE_DEVICES
from pTracker.api.attendance_v2.attendance_v2_helper import CAP_MANAGE_SHIFTS
from pTracker.api.attendance_v2.attendance_v2_helper import CAP_CORRECT
from pTracker.api.attendance_v2.device_biz import collector_dict
from pTracker.api.attendance_v2.day_plan_biz import RuleSettings
from pTracker.common.company_authorization import data_scope
from pTracker.dataaccess.attendance_v2_access.daily_da import DailyDA
from pTracker.dataaccess.attendance_v2_access.punch_da import PunchDA
from pTracker.dataaccess.attendance_v2_access.device_da import CollectorDA
from pTracker.dataaccess.attendance_v2_access.org_da import OrgDA


def _name(user):
    return f'{user.first_name} {user.last_name}'.strip() if user else None


def daily_dict(row):
    snapshot = row.shift_snapshot or {}
    return {
        'id': row.id,
        'employee_id': row.employee_id,
        'employee_name': _name(row.employee),
        'employee_code': row.employee.username,
        'attendance_date': fmt_date(row.attendance_date),
        'shift_id': row.shift_id,
        'shift_code': snapshot.get('shift_code'),
        'shift_name': snapshot.get('shift_name'),
        'shift_start': (snapshot.get('start_time') or '')[:5] or None,
        'shift_end': (snapshot.get('end_time') or '')[:5] or None,
        'day_type': row.day_type,
        'leave_portion': row.leave_portion,
        'status': row.status,
        'first_in': fmt_dt(row.first_in),
        'last_out': fmt_dt(row.last_out),
        'first_in_location': row.first_in_location.name if row.first_in_location_id else None,
        'last_out_location': row.last_out_location.name if row.last_out_location_id else None,
        'total_work_minutes': row.total_work_minutes,
        'total_break_minutes': row.total_break_minutes,
        'expected_work_minutes': row.expected_work_minutes,
        'late_minutes': row.late_minutes,
        'early_departure_minutes': row.early_departure_minutes,
        'overtime_minutes': row.overtime_minutes,
        'is_late': row.is_late,
        'is_early_departure': row.is_early_departure,
        'session_count': row.session_count,
        'has_missing_punch': row.has_missing_punch,
        'remarks': row.remarks,
        'processed_at': fmt_dt(row.processed_at),
    }


def session_dict(session):
    return {
        'id': session.id,
        'employee_id': session.employee_id,
        'employee_name': _name(session.employee),
        'attendance_date': fmt_date(session.attendance_date),
        'sequence': session.sequence,
        'check_in': fmt_dt(session.check_in),
        'check_out': fmt_dt(session.check_out),
        'check_in_location': session.check_in_location.name if session.check_in_location_id else None,
        'check_out_location': session.check_out_location.name if session.check_out_location_id else None,
        'duration_minutes': session.duration_minutes,
        'status': session.status,
    }


def event_dict(event):
    return {
        'id': event.id,
        'employee_id': event.employee_id,
        'event_time': fmt_dt(event.event_time),
        'event_type': event.event_type,
        'attendance_date': fmt_date(event.attendance_date),
        'source': event.source,
        'device': event.device.name if event.device_id else None,
        'location': event.location.name if event.location_id else None,
        'is_manual': event.is_manual,
        'manual_reason': event.manual_reason,
        'status': event.status,
        'void_reason': event.void_reason,
    }


def raw_punch_dict(punch):
    return {
        'id': punch.id,
        'collector_id': punch.collector.collector_id if punch.collector_id else None,
        'device_code': punch.device.code,
        'device_name': punch.device.name,
        'employee_id': punch.employee_id,
        'employee_name': _name(punch.employee),
        'external_employee_id': punch.external_employee_id,
        'external_punch_id': punch.external_punch_id,
        'punch_time': fmt_dt(punch.punch_time),
        'raw_punch_type': punch.raw_punch_type,
        'punch_type': punch.punch_type,
        'source': punch.source,
        'location': punch.location.name if punch.location_id else None,
        'raw_data': punch.raw_data,
        'received_at': fmt_dt(punch.received_at),
        'status': punch.status,
        'error_message': punch.error_message,
        'processed_at': fmt_dt(punch.processed_at),
        'sync_log_id': punch.sync_log_id,
    }


def sync_log_dict(log):
    return {
        'id': log.id,
        'collector_id': log.collector.collector_id if log.collector_id else None,
        'device_code': log.device.code if log.device_id else None,
        'kind': log.kind,
        'request_id': log.request_id,
        'remote_ip': log.remote_ip,
        'status': log.status,
        'received_count': log.received_count,
        'accepted_count': log.accepted_count,
        'duplicate_count': log.duplicate_count,
        'failed_count': log.failed_count,
        'errors': log.errors,
        'message': log.message,
        'started_at': fmt_dt(log.started_at),
        'finished_at': fmt_dt(log.finished_at),
    }


class AttendanceQueryBL:

    def __init__(self):
        self.__daily_da = DailyDA()
        self.__punch_da = PunchDA()

    @guarded('list_daily')
    def list_daily(self, user_id, query):
        company_id = active_company_id(user_id)
        employee_ids = narrow_employee_ids(user_id, company_id,
                                           parse_query_int(query.get('employee_id'), 'employee_id'))
        start, end = date_range_from_query(query, default_days=6)
        rows = self.__daily_da.get_daily_list(company_id, employee_ids, start, end, query.get('status'))
        return paginate(rows, query, daily_dict)

    @guarded('daily_detail')
    def daily_detail(self, user_id, query):
        company_id = active_company_id(user_id)
        employee_id = parse_query_int(query.get('employee_id'), 'employee_id') or user_id
        ensure_employee_visible(user_id, company_id, employee_id)
        work_date = parse_query_date(query.get('date'), 'date', required=True)
        daily = self.__daily_da.get_daily(company_id, employee_id, work_date)
        sessions = self.__daily_da.get_sessions(company_id, {employee_id}, work_date, work_date)
        events = self.__punch_da.get_events(company_id, {employee_id}, work_date, work_date)
        return {
            'daily': daily_dict(daily) if daily else None,
            'shift_snapshot': daily.shift_snapshot if daily else None,
            'sessions': [session_dict(s) for s in sessions],
            'events': [event_dict(e) for e in events],
            'status': 200,
        }

    @guarded('list_sessions')
    def list_sessions(self, user_id, query):
        company_id = active_company_id(user_id)
        employee_ids = narrow_employee_ids(user_id, company_id,
                                           parse_query_int(query.get('employee_id'), 'employee_id'))
        start, end = date_range_from_query(query, default_days=6)
        return paginate(self.__daily_da.get_sessions(company_id, employee_ids, start, end), query, session_dict)

    @guarded('list_events')
    def list_events(self, user_id, query):
        company_id = active_company_id(user_id)
        employee_id = parse_query_int(query.get('employee_id'), 'employee_id') or user_id
        ensure_employee_visible(user_id, company_id, employee_id)
        start, end = date_range_from_query(query, default_days=0, max_days=31)
        events = self.__punch_da.get_events(company_id, {employee_id}, start, end)
        return {'events': [event_dict(e) for e in events], 'status': 200}

    @guarded('list_raw_punches')
    def list_raw_punches(self, user_id, query):
        company_id = active_company_id(user_id)
        require_capability(user_id, CAP_MANAGE_DEVICES)
        start, end = date_range_from_query(query, default_days=0)
        start_dt, end_dt = day_bounds(start, end)
        filters = {
            'device_id': parse_query_int(query.get('device_id'), 'device_id'),
            'collector_id': parse_query_int(query.get('collector_id'), 'collector_id'),
            'employee_id': parse_query_int(query.get('employee_id'), 'employee_id'),
            'status': query.get('status'),
            'search': (query.get('search') or '').strip()[:64] or None,
            'start': start_dt, 'end': end_dt,
        }
        return paginate(self.__punch_da.get_raw_punches(company_id, filters), query, raw_punch_dict)

    @guarded('list_sync_logs')
    def list_sync_logs(self, user_id, query):
        company_id = active_company_id(user_id)
        require_capability(user_id, CAP_MANAGE_DEVICES)
        start, end = date_range_from_query(query, default_days=6)
        start_dt, end_dt = day_bounds(start, end)
        logs = self.__punch_da.get_sync_logs(company_id, parse_query_int(query.get('collector_id'), 'collector_id'),
                                             query.get('status'), start_dt, end_dt)
        return paginate(logs, query, sync_log_dict)

    @guarded('dashboard')
    def dashboard(self, user_id, query):
        company_id = active_company_id(user_id)
        work_date = parse_query_date(query.get('date'), 'date') or today_local()
        employee_ids = visible_employee_ids(user_id, company_id)
        member_count = len(OrgDA().get_member_ids(company_id, employee_ids)) if employee_ids is not None \
            else len(OrgDA().get_member_ids(company_id))
        counts = self.__daily_da.count_by_status(company_id, employee_ids, work_date)
        response = {
            'date': work_date.isoformat(),
            'scope': data_scope(user_id, 'attendance') or 'self',
            'employee_count': member_count,
            'counts': counts,
            'not_recorded': max(member_count - sum(v for k, v in counts.items()
                                                   if k not in ('late', 'missing_punch')), 0),
            'status': 200,
        }
        if can(user_id, CAP_MANAGE_DEVICES):
            offline_after = RuleSettings.from_row(self.__daily_da.get_settings(company_id)) \
                .collector_offline_after_minutes
            collectors = [collector_dict(c, offline_after) for c in CollectorDA().get_collectors(company_id)]
            response['collectors'] = {
                'total': len(collectors),
                'online': sum(1 for c in collectors if c['is_online']),
                'offline': [c['collector_id'] for c in collectors if not c['is_online']],
            }
            yesterday_start, _ = day_bounds(work_date - timedelta(days=1), work_date)
            response['unresolved_punches'] = self.__punch_da.get_raw_punches(
                company_id, {'status': 'unresolved_employee', 'start': yesterday_start}).count()
        return response

    @guarded('list_employees')
    def list_employees(self, user_id, query):
        """ Employees the caller may pick in filters (their scope), or every
        company member for shift / correction administrators. """
        company_id = active_company_id(user_id)
        if any(can(user_id, c) for c in (CAP_MANAGE_SHIFTS, CAP_CORRECT)):
            employee_ids = None
        else:
            employee_ids = visible_employee_ids(user_id, company_id)
        users = OrgDA().get_employees(company_id, employee_ids, (query.get('search') or '').strip()[:50] or None)
        return {'employees': [{'id': u.id, 'employee_code': u.username, 'name': _name(u)} for u in users[:500]],
                'status': 200}

    @guarded('list_branches')
    def list_branches(self, user_id):
        company_id = active_company_id(user_id)
        return {'branches': list(OrgDA().get_branches(company_id)), 'status': 200}

    @guarded('my_access')
    def my_access(self, user_id):
        """ UI hints only - every endpoint re-checks on the server. """
        active_company_id(user_id)
        return {
            'scope': data_scope(user_id, 'attendance') or 'self',
            'can_manage_devices': can(user_id, CAP_MANAGE_DEVICES),
            'can_manage_shifts': can(user_id, CAP_MANAGE_SHIFTS),
            'can_correct': can(user_id, CAP_CORRECT),
            'status': 200,
        }

