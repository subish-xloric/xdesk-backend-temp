from datetime import datetime

from django.conf import settings
from django.contrib.auth.models import User

from pTracker.api.attendance_v2.attendance_v2_helper import active_company_id
from pTracker.api.attendance_v2.attendance_v2_helper import guarded
from pTracker.api.attendance_v2.attendance_v2_helper import today_local
from pTracker.api.attendance_v2.attendance_v2_helper import V2Error
from pTracker.api.attendance_v2.processing_biz import AttendanceProcessorBL
from pTracker.api.user.user_management_bl_v1 import UserManagementBL_V1
from pTracker.common.company_authorization import data_scope, SCOPE_ALL
from pTracker.dataaccess.attendance_v2_access.constants import DAY_HOLIDAY
from pTracker.dataaccess.attendance_v2_access.constants import DAY_WEEKLY_OFF
from pTracker.dataaccess.attendance_v2_access.constants import LEAVE_FULL
from pTracker.dataaccess.attendance_v2_access.constants import PUNCH_IN
from pTracker.dataaccess.attendance_v2_access.constants import PUNCH_OUT
from pTracker.dataaccess.attendance_v2_access.constants import SELF_CHECKIN_DEVICE_TYPES
from pTracker.dataaccess.attendance_v2_access.constants import STATUS_HALF_DAY
from pTracker.dataaccess.attendance_v2_access.constants import STATUS_HOLIDAY
from pTracker.dataaccess.attendance_v2_access.constants import STATUS_INCOMPLETE
from pTracker.dataaccess.attendance_v2_access.constants import STATUS_LEAVE
from pTracker.dataaccess.attendance_v2_access.constants import STATUS_PRESENT
from pTracker.dataaccess.attendance_v2_access.constants import STATUS_WEEKLY_OFF
from pTracker.dataaccess.attendance_v2_access.daily_da import DailyDA
from pTracker.dataaccess.attendance_v2_access.org_da import OrgDA
from pTracker.dataaccess.attendance_v2_access.punch_da import PunchDA
from pTracker.dataaccess.ptracker_access.user_models import UserProfile
from pTracker.user_management.employee import Employee

PAGE_SIZE = 25
IN_OFFICE, WFH, LEAVE, NOT_PUNCHED = 'In Office', 'WFH', 'Leave', 'Not Punched'
HOLIDAY, WEEKLY_OFF = 'Holiday', 'Weekly Off'
FILTERS = {'ALL': None, 'IN_OFFICE': IN_OFFICE, 'WFH': WFH, 'LEAVE': LEAVE, 'NOT_PUNCHED': NOT_PUNCHED,
           'HOLIDAY': HOLIDAY, 'WEEKLY_OFF': WEEKLY_OFF}
WORKED_STATUSES = (STATUS_PRESENT, STATUS_HALF_DAY, STATUS_INCOMPLETE)


class TeamStatsBL():
    """ Who is in office / on WFH / on leave / not punched on a day, from
    Attendance V2, for the employees of the active company the caller may see:
    everyone else in the company (attendance.view_all) or their team
    (attendance.view_team). """

    @guarded('team_stats')
    def get_team_stats(self, user_id, att_date=None, page=1, filter_by_type='ALL', keyword=None):
        try:
            work_date = datetime.strptime(att_date, '%Y-%m-%d').date() if att_date else today_local()
            page = max(int(page or 1), 1)
        except (TypeError, ValueError):
            raise V2Error('Invalid date or page', 400)
        filter_status = FILTERS.get(str(filter_by_type or 'ALL').upper(), 'invalid')
        if filter_status == 'invalid':
            raise V2Error('filterByType must be one of ' + ', '.join(FILTERS), 400)

        company_id = active_company_id(user_id)
        scope = data_scope(user_id, 'attendance')
        if scope is None:
            raise V2Error(settings.ERROR_MSG.get('access_denied'), 403)
        if scope == SCOPE_ALL:
            member_ids = set(OrgDA().get_member_ids(company_id))
        else:
            member_ids = set(OrgDA().get_member_ids(company_id, OrgDA().get_team_member_ids(user_id)))
        member_ids.discard(user_id)

        users = User.objects.filter(id__in=member_ids, is_active=True).order_by('first_name', 'last_name')
        if keyword:
            users = [u for u in users if keyword.strip().lower() in f'{u.first_name} {u.last_name}'.lower()]
        users = list(users)
        employee_ids = {u.id for u in users}

        members = [self.__member_status(user, data) for user, data in
                   zip(users, self.__day_data(company_id, employee_ids, work_date, users))]
        members = [m for m in members if m]
        counts = {status: sum(1 for m in members if m['status'] == status) for status in FILTERS.values() if status}

        if filter_status:
            members = [m for m in members if m['status'] == filter_status]
        start = (page - 1) * PAGE_SIZE
        return {
            'status': 200,
            'error': None,
            'date': work_date.isoformat(),
            'present_count': counts[IN_OFFICE],
            'wfh_count': counts[WFH],
            'leave_count': counts[LEAVE],
            'not_punched_count': counts[NOT_PUNCHED],
            'holiday_count': counts[HOLIDAY],
            'weekly_off_count': counts[WEEKLY_OFF],
            'total_count': len(members),
            'team_members': members[start:start + PAGE_SIZE],
            'requests': self.__requests(user_id),
        }

    def __day_data(self, company_id, employee_ids, work_date, users):
        """ Per user (in order): (daily row, punches, approved WFH, leave, plan). """
        daily = {row.employee_id: row for row in
                 DailyDA().get_daily_list(company_id, employee_ids, work_date, work_date)}
        punches = {}
        for event in PunchDA().get_events(company_id, employee_ids, work_date, work_date, include_void=False):
            punches.setdefault(event.employee_id, []).append(event)
        approved_wfh = OrgDA().get_approved_wfh_employee_ids(employee_ids, work_date)
        leave_statuses = (settings.LEAVE_REQUEST_STATUS['Requested'], settings.LEAVE_REQUEST_STATUS['Approved'])
        on_leave = OrgDA().get_employees_on_leave(employee_ids, work_date, leave_statuses)
        excluded = {str(e.emp_code) for e in Employee().get_att_exclude_employees_code(company_id)}
        photos = dict(UserProfile.objects.filter(user_id__in=employee_ids).values_list('user_id', 'profile_photo'))
        company = OrgDA().get_company(company_id)
        for user in users:
            row, events = daily.get(user.id), punches.get(user.id, [])
            plan = None
            if row is None and not events and user.id not in on_leave:
                plan = AttendanceProcessorBL(company).planner(user.id, work_date, work_date).plan(work_date)
            yield {'row': row, 'events': events, 'wfh': user.id in approved_wfh, 'leave': on_leave.get(user.id),
                   'plan': plan, 'excluded': str(user.username) in excluded, 'photo': photos.get(user.id)}

    def __member_status(self, user, data):
        row, events = data['row'], data['events']
        entry = {
            'emp_id': user.id,
            'emp_name': f'{user.first_name} {user.last_name}',
            'emp_image': f"{settings.DEFAULT_SITE_MEDIA_URL}{data['photo']}" if data['photo'] else '',
            'status': NOT_PUNCHED,
            'work_hours': 0,
            'first_punch_in': '-',
            'last_punch_out': '-',
        }
        worked = bool(events) or (row is not None and row.status in WORKED_STATUSES)
        if worked:
            remote = any(e.source in SELF_CHECKIN_DEVICE_TYPES for e in events)
            entry['status'] = WFH if remote else IN_OFFICE
            first_in = row.first_in if row and row.first_in else \
                min((e.event_time for e in events if e.event_type == PUNCH_IN), default=None)
            last_out = row.last_out if row and row.last_out else \
                max((e.event_time for e in events if e.event_type == PUNCH_OUT), default=None)
            if first_in:
                entry['first_punch_in'] = first_in.strftime('%I:%M %p')
            if last_out:
                entry['last_punch_out'] = last_out.strftime('%I:%M %p')
            if first_in and last_out and last_out > first_in:
                entry['work_hours'] = int((last_out - first_in).total_seconds())
            return entry

        if data['excluded']:
            return None  # attendance-exempt employees (attendance_exclude_employee): listed only when they punch
        status = row.status if row else None
        plan = data['plan']
        if status == STATUS_HOLIDAY or (plan and plan.day_type == DAY_HOLIDAY):
            entry['status'] = HOLIDAY
        elif status == STATUS_WEEKLY_OFF or (plan and plan.day_type == DAY_WEEKLY_OFF):
            entry['status'] = WEEKLY_OFF
        elif status == STATUS_LEAVE or data['leave'] is not None or (plan and plan.leave_portion == LEAVE_FULL):
            entry['status'] = LEAVE
        return entry

    def __requests(self, user_id):
        counts = UserManagementBL_V1().get_pending_leave_and_wfh_count(user_id)
        return {'leave_requests': counts.get('team_leave_requests', 0),
                'wfh_requests': counts.get('team_wfh_requests', 0)}
