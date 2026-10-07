""" Small helpers shared by the Attendance V2 business layer: the active
company, capability/data-scope checks, time handling, pagination and the
unexpected-error guard. Nothing here is device specific. """

import functools
import re
import uuid
from datetime import date, datetime, time, timedelta
from zoneinfo import ZoneInfo

from django.conf import settings
from django.utils import timezone
from django.utils.dateparse import parse_date, parse_datetime

from pTracker.common.company_context import get_active_company
from pTracker.common.company_authorization import has_capability
from pTracker.common.company_authorization import data_scope
from pTracker.common.company_authorization import SCOPE_ALL
from pTracker.common.company_authorization import SCOPE_TEAM
from pTracker.common.exception_handler import ExceptionHandler
from pTracker.common.logs import Logs
from pTracker.dataaccess.attendance_v2_access.org_da import OrgDA

CAP_MANAGE_DEVICES = 'attendance.manage_devices'
CAP_MANAGE_SHIFTS = 'attendance.manage_shifts'
CAP_CORRECT = 'attendance.correct'

MAX_PAGE_SIZE = 200
MAX_RANGE_DAYS = 93

_DEFAULTS = {
    'COLLECTOR_RATE': '120/min',
    'MAX_BATCH_SIZE': 500,
    'MAX_PUNCH_AGE_DAYS': 60,
    'MAX_FUTURE_SKEW_MINUTES': 10,
    'MAX_RAW_DATA_BYTES': 4096,
}


def v2_setting(name):
    """ Optional overrides via settings.ATTENDANCE_V2 = {...}; defaults above.
    REQUIRE_HTTPS defaults to "not DEBUG". """
    configured = getattr(settings, 'ATTENDANCE_V2', {}) or {}
    if name == 'REQUIRE_HTTPS':
        return configured.get(name, not settings.DEBUG)
    return configured.get(name, _DEFAULTS[name])


class V2Error(Exception):
    """ Expected, client-facing failure; turned into {'error', 'status'}. """

    def __init__(self, message, status=400, errors=None):
        super().__init__(message)
        self.message = message
        self.status = status
        self.errors = errors


def error(message, status=400, errors=None):
    response = {'error': message, 'status': status}
    if errors:
        response['errors'] = errors
    return response


def guarded(context_name):
    """ Wraps a biz method: V2Error -> its response; anything unexpected is
    logged server-side with a reference id and reported without internals. """
    def decorator(func):
        @functools.wraps(func)
        def wrapper(*args, **kwargs):
            try:
                return func(*args, **kwargs)
            except V2Error as exc:
                return error(exc.message, exc.status, exc.errors)
            except Exception:
                reference = uuid.uuid4().hex[:12]
                active = get_active_company()
                Logs().error(f'[attendance_v2] {context_name} failed ref={reference} '
                             f'company={getattr(active, "company_id", None)} '
                             f'user={getattr(active, "user_id", None)} '
                             f'{ExceptionHandler().get_exception()}')
                return error(f'Something went wrong. Reference: {reference}', 500)
        return wrapper
    return decorator


# --- company / access ------------------------------------------------------

def active_company_id(user_id):
    """ Company set for this request by ModuleGateMiddleware (verified active
    membership). Never taken from a client-supplied id. """
    active = get_active_company()
    if active is None or active.user_id != user_id:
        raise V2Error('No active company for this request', 403)
    return active.company_id


def require_capability(user_id, capability):
    if not has_capability(user_id, capability):
        raise V2Error(settings.ERROR_MSG.get('no_permission', 'Permission denied'), 403)


def can(user_id, capability):
    return has_capability(user_id, capability)


def visible_employee_ids(user_id, company_id):
    """ None = every employee of the company (attendance.view_all); otherwise the
    set the caller may see: their team (attendance.view_team) plus themselves. """
    scope = data_scope(user_id, 'attendance')
    if scope == SCOPE_ALL:
        return None
    ids = {user_id}
    if scope == SCOPE_TEAM:
        ids |= OrgDA().get_team_member_ids(user_id)
    return OrgDA().get_member_ids(company_id, ids)


def ensure_employee_visible(user_id, company_id, employee_id):
    """ 404 (not 403) for employees outside the caller's company or scope, so
    ids of other companies' employees cannot be probed. """
    if not OrgDA().is_company_member(company_id, employee_id):
        raise V2Error('Employee not found', 404)
    visible = visible_employee_ids(user_id, company_id)
    if visible is not None and employee_id not in visible:
        raise V2Error('Employee not found', 404)


def narrow_employee_ids(user_id, company_id, requested_employee_id):
    """ Employee filter for list endpoints: an explicit employee (checked), or
    everything the caller may see. """
    if requested_employee_id:
        ensure_employee_visible(user_id, company_id, requested_employee_id)
        return {requested_employee_id}
    return visible_employee_ids(user_id, company_id)


# --- time ------------------------------------------------------------------

def now_local():
    """ Naive server-local time (USE_TZ is False; TIME_ZONE is local). """
    return timezone.now().replace(microsecond=0)


def today_local():
    return now_local().date()


def to_local_naive(value):
    """ Aware datetimes are converted to settings.TIME_ZONE; naive ones are
    taken as already local. """
    if value.tzinfo is not None:
        value = value.astimezone(ZoneInfo(settings.TIME_ZONE)).replace(tzinfo=None)
    return value.replace(microsecond=0)


def parse_iso_datetime(value):
    if isinstance(value, datetime):
        return to_local_naive(value)
    try:
        parsed = parse_datetime(str(value).strip())
    except ValueError:
        parsed = None
    if parsed is None:
        raise ValueError('must be an ISO-8601 date-time, e.g. 2026-09-23T08:52:14+05:30')
    return to_local_naive(parsed)


def parse_query_date(value, name, required=False):
    if value in (None, ''):
        if required:
            raise V2Error(f'{name} is required (YYYY-MM-DD)')
        return None
    try:
        parsed = parse_date(str(value))
    except ValueError:
        parsed = None
    if parsed is None:
        raise V2Error(f'{name} must be a date (YYYY-MM-DD)')
    return parsed


def parse_query_int(value, name):
    if value in (None, ''):
        return None
    try:
        return int(value)
    except (TypeError, ValueError):
        raise V2Error(f'{name} must be a number')


def date_range_from_query(query, default_days=0, max_days=MAX_RANGE_DAYS):
    start = parse_query_date(query.get('from_date'), 'from_date')
    end = parse_query_date(query.get('to_date'), 'to_date')
    today = today_local()
    end = end or (start + timedelta(days=default_days) if start else today)
    start = start or end - timedelta(days=default_days)
    if start > end:
        raise V2Error('from_date must be on or before to_date')
    if (end - start).days > max_days:
        raise V2Error(f'Date range cannot exceed {max_days} days')
    return start, end


def day_bounds(start_date, end_date):
    return datetime.combine(start_date, time.min), datetime.combine(end_date + timedelta(days=1), time.min)


def fmt_dt(value):
    return value.strftime('%Y-%m-%dT%H:%M:%S') if value else None


def fmt_date(value):
    return value.isoformat() if isinstance(value, date) else value


def fmt_time(value):
    return value.strftime('%H:%M') if value else None


# --- misc ------------------------------------------------------------------

def paginate(queryset_or_list, query, serializer):
    page = max(parse_query_int(query.get('page'), 'page') or 1, 1)
    page_size = parse_query_int(query.get('page_size'), 'page_size') or 50
    page_size = min(max(page_size, 1), MAX_PAGE_SIZE)
    total = len(queryset_or_list) if isinstance(queryset_or_list, list) else queryset_or_list.count()
    offset = (page - 1) * page_size
    rows = queryset_or_list[offset:offset + page_size]
    return {'results': [serializer(row) for row in rows], 'count': total, 'page': page,
            'page_size': page_size, 'status': 200}


_REQUEST_ID_RE = re.compile(r'^[A-Za-z0-9._:-]{1,64}$')


def request_id_from(meta):
    supplied = meta.get('HTTP_X_REQUEST_ID', '')
    return supplied if _REQUEST_ID_RE.match(supplied) else uuid.uuid4().hex


def client_ip(meta):
    ip = meta.get('REMOTE_ADDR')
    return ip or None


def first_error_message(serializer_errors):
    """ Flattens DRF serializer errors into "field: message" strings. """
    messages = []

    def walk(prefix, value):
        if isinstance(value, dict):
            for key, inner in value.items():
                walk(f'{prefix}.{key}' if prefix else str(key), inner)
        elif isinstance(value, list):
            for inner in value:
                walk(prefix, inner)
        else:
            messages.append(f'{prefix}: {value}' if prefix else str(value))

    walk('', serializer_errors)
    return messages
