import json
from types import SimpleNamespace
from datetime import datetime, date, timedelta
# import datetime

from django.conf import settings

from pTracker.common.utility import Utility
from pTracker.common.company_authorization import oversees_employee
from pTracker.common.company_authorization import users_with_capability
from pTracker.common.exception_handler import ExceptionHandler
from pTracker.common.logs import Logs

from pTracker.dataaccess.ptracker_access.leave_da import LeaveDA
from pTracker.dataaccess.ptracker_access.user_da import UserDA
from pTracker.api.leave.leave_biz import LeaveBL
from pTracker.api.leave.leave_helper import LeaveHelperBL
from pTracker.dataaccess.attendance_v2_access.org_da import OrgDA
from pTracker.common.company_context import get_active_company_id
from pTracker.user_management.holiday_da import HolidayDA
from pTracker.common.company_authorization import data_scope, SCOPE_ALL, SCOPE_TEAM



def new_dto():
    dto = SimpleNamespace()
    return dto

class LeaveBL_V1():
    def __init__(self):
        self.__log = Logs()
        self.__exception = ExceptionHandler()
        self.__utility = Utility()

    def format_leave_request_response(self, result):
        if result.get("error"):
            result = {"error": result.get("error")}
        elif result.get("status"):
            result = {"message": result.get("status")}
        return result

    MY_REQUESTS_PAGE_SIZE = 10

    def get_my_leave_requests(self, user_id, page=1, emp_id=None):
        """ Leave requests of an employee (default: the caller) in the active
        company's current leave period, newest first, 10 per page (0 = all).
        Others' requests: their mapped lead or leave.view_all; employees outside
        the active company are "Employee not found". Pending requests list who
        can approve them (pending_approvers). """
        try:
            page = int(page)
            emp_id = int(emp_id) if emp_id else user_id
            if page < 0:
                raise ValueError
        except (TypeError, ValueError):
            return {"error": "Invalid page or employee", "status": 400}
        try:
            company_id = get_active_company_id()
            if company_id is None or not OrgDA().is_company_member(company_id, emp_id):
                return {"error": "Employee not found", "status": 404}
            if emp_id != user_id and not oversees_employee(user_id, emp_id, module='leave'):
                return {"error": "You have no permission.", "status": 403}

            period = LeaveDA().get_leave_period_by_date(date.today(), company_id)
            if not period:
                return {"leaves": [], "status": 200}
            requests = LeaveDA().get_leave_requests_by_user_id(emp_id, period.leave_period_id)
            if page:
                start = (page - 1) * self.MY_REQUESTS_PAGE_SIZE
                requests = requests[start:start + self.MY_REQUESTS_PAGE_SIZE]
            requests = list(requests)

            day_types = LeaveDA().get_leave_day_types([r.request_id for r in requests])
            requested = settings.LEAVE_REQUEST_STATUS['Requested']
            # who can act on a pending request without a lead: the company's leave approvers
            fallback_approvers = []
            if any(r.status == requested and not int(r.approver or 0) for r in requests):
                fallback_approvers = [uid for uid in users_with_capability('leave.approve') if uid != emp_id]
            people = {int(r.approver) for r in requests if int(r.approver or 0)} | set(fallback_approvers)
            names = {u.id: f"{u.first_name} {u.last_name}" for u in UserDA().get_all_users().filter(id__in=people)}
            fallback = [{"id": uid, "name": names.get(uid, "")} for uid in fallback_approvers if uid in names]
            mobile_status = settings.MOBILE_LEAVE_REQUEST_STATUS

            leaves = []
            for r in requests:
                approver_id = int(r.approver or 0)
                day_type = day_types.get(r.request_id)
                pending = []
                if r.status == requested:
                    pending = [{"id": approver_id, "name": names.get(approver_id, "")}] if approver_id else fallback
                leaves.append({
                    "leave_request_id": r.request_id,
                    "leave_type_id": int(r.type_id),
                    "start_date": r.start_date,
                    "end_date": r.end_date,
                    "no_of_days": r.length_days,
                    "duration": day_type,
                    "leave_section": {2: "(AM)", 3: "(PM)"}.get(day_type, ""),
                    "status": mobile_status.get(r.status),
                    "reason": r.reason,
                    "comment": r.comment,
                    "approver_id": approver_id,
                    "approver_name": names.get(approver_id) if approver_id
                                     else ", ".join(p["name"] for p in pending) or None,
                    "pending_approvers": pending,
                    "notify_list": self.convert_to_list(r.notify),
                })
            return {"leaves": leaves, "status": 200}
        except Exception:
            return {"error": "Leave requests failed. LogID: {0}".format(
                self.__log.error(self.__exception.get_exception())), "status": 499}

    def convert_to_list(self, data):
        li = []
        if data:
            li = list((data).split(','))
            li = [int(x) for x in li]
        return li

    def format_cancel_leave_request(self, data, type=0):
        """ Mobile body -> update_leave_status input. type=1: approve / reject
        ({leave_request_id, action: APPROVED|REJECTED, comment}); otherwise cancel. """
        leave_request_id = data.get("leave_request_id")
        if not leave_request_id:
            return {"error": "leave_request_id is required", "status": 400}
        if type:
            status = {"APPROVED": 2, "REJECTED": 4}.get(str(data.get("action", "")).upper())
            if status is None:
                return {"error": "action must be APPROVED or REJECTED", "status": 400}
            return {"req_id": leave_request_id, "status": status, "comment": data.get("comment", '')}
        return {"req_id": leave_request_id, "status": 3, "comment": data.get("comment", '')}

    def get_team_leave_requests(self, user_id, page=1, status='pending', direct_reporting='false'):
        """ Leave requests of the people the caller manages in the active company,
        in its current leave period, newest start date first. status: pending
        (Requested) or verified (Approved / Cancelled / Rejected). Everyone else in
        the company with leave.view_all, the lead-mapped team with leave.view_team;
        direct_reporting=true limits it to the lead-mapped team. """
        try:
            page = int(page)
            if page < 0:
                raise ValueError
        except (TypeError, ValueError):
            return {"error": "Invalid page", "status": 400}
        statuses = self.TEAM_REQUEST_STATUSES.get(str(status).lower())
        if statuses is None:
            return {"error": "status must be pending or verified", "status": 400}
        if str(direct_reporting).lower() not in ('true', 'false'):
            return {"error": "includeOnlyDirectReporting must be true or false", "status": 400}
        try:
            scope = data_scope(user_id, 'leave')
            if scope not in (SCOPE_ALL, SCOPE_TEAM):
                return {"error": settings.ERROR_MSG.get('access_denied'), "status": 403}
            company_id = get_active_company_id()
            if company_id is None:
                return {"leaves": [], "status": 200}
            if scope == SCOPE_ALL and str(direct_reporting).lower() == 'false':
                member_ids = OrgDA().get_member_ids(company_id)
            else:
                member_ids = OrgDA().get_member_ids(company_id, OrgDA().get_team_member_ids(user_id))
            member_ids.discard(user_id)
            period = LeaveDA().get_leave_period_by_date(date.today(), company_id)
            if not period or not member_ids:
                return {"leaves": [], "status": 200}

            requests = LeaveDA().get_team_leave_requests(period.leave_period_id, member_ids, statuses)
            if page:
                start = (page - 1) * self.TEAM_REQUESTS_PAGE_SIZE
                requests = requests[start:start + self.TEAM_REQUESTS_PAGE_SIZE]
            requests = list(requests)
            day_types = LeaveDA().get_leave_day_types([r.request_id for r in requests])
            people = {r.employee_id for r in requests} | {int(r.approver) for r in requests if r.approver}
            names = {u.id: f"{u.first_name} {u.last_name}" for u in UserDA().get_all_users().filter(id__in=people)}
            photos = UserDA().get_profile_photos({r.employee_id for r in requests})
            mobile_status = settings.MOBILE_LEAVE_REQUEST_STATUS
            leaves = []
            for row in requests:
                day_type = day_types.get(row.request_id)
                leaves.append({
                    "leave_request_id": row.request_id,
                    "emp_id": row.employee_id,
                    "emp_name": names.get(row.employee_id, ""),
                    "emp_image": f"{settings.DEFAULT_SITE_MEDIA_URL}{photos[row.employee_id]}"
                                 if photos.get(row.employee_id) else "",
                    "leave_type_id": int(row.type_id),
                    "start_date": row.start_date,
                    "end_date": row.end_date,
                    "no_of_days": row.length_days,
                    "duration": day_type,
                    "leave_section": {2: "(AM)", 3: "(PM)"}.get(day_type, ""),
                    "status": mobile_status.get(row.status),
                    "reason": row.reason,
                    "comment": row.comment,
                    "approver_id": int(row.approver) if row.approver else 0,
                    "approver_name": names.get(int(row.approver), "") if row.approver else "",
                    "notify_list": self.convert_to_list(row.notify),
                })
            return {"leaves": leaves, "status": 200}
        except Exception:
            return {"error": "Team leave requests failed. LogID: {0}".format(
                self.__log.error(self.__exception.get_exception())), "status": 499}

    def format_date_validation(self, start_date, end_date):
        return {'start_date':start_date, 'end_date':end_date}
    
    def leave_date_validation(self, data , user_id):
        """ Mobile validate-date: exactly the rules used when the request is
        submitted (LeaveHelperBL.validate_leave_dates). """
        try:
            message = LeaveHelperBL().validate_leave_dates(data, user_id)
        except Exception:
            return {"error": "Leave validation failed. LogID: {0}".format(
                self.__log.error(self.__exception.get_exception())), "status": 499}
        if message:
            return {"msg": message, "is_valid": False, "status": 400}
        return {"msg": "", "is_valid": True, "status": 200}

    def format_notfy_list(self, notify):
        res = []
        if notify:
            for each in notify:
                res.append({"id":each})
        return res

    def get_user_leave_summary_by_emp_id(self, user_id, emp_id=None):
        """ Leave balances of an employee in the active company for the leave
        period covering today: one entry per enabled leave type of the company
        (zeros where the employee has no quota). Allowed: yourself, your team
        (lead mapping) or anyone with leave.view_all. Employees outside the
        active company are "Employee not found" (404). """
        try:
            emp_id = int(emp_id) if emp_id else user_id
            company_id = get_active_company_id()
            if company_id is None or not OrgDA().is_company_member(company_id, emp_id):
                return {"error": "Employee not found", "status": 404}
            if emp_id != user_id and data_scope(user_id, 'leave') != SCOPE_ALL \
                    and not UserDA().is_team_member(emp_id, user_id):
                return {"error": settings.ERROR_MSG.get('access_denied'), "status": 403}

            leave_period = LeaveDA().get_leave_period_by_date(date.today(), company_id)
            quotas = {}
            if leave_period:
                quotas = {item['leave_type_id']: item for item in
                          LeaveHelperBL().leave_summary_by_type(emp_id, leave_period.leave_period_id)}
            leave_types = []
            for leave_type in LeaveDA().get_all_leave_types(company_id).order_by('leave_type_name'):
                item = quotas.get(leave_type.leave_type_id, {})
                leave_types.append({
                    'leave_type_id': leave_type.leave_type_id,
                    'leave_type': leave_type.leave_type_name,
                    'code': leave_type.code,
                    'total': item.get('total', 0.0),
                    'taken': item.get('taken', 0.0),
                    'scheduled': item.get('scheduled', 0.0),
                    'balance': item.get('balance', 0.0),
                })
            return {"error": '', "leave_period_id": leave_period.leave_period_id if leave_period else None,
                    "leave_types": leave_types, "status": 200}
        except (TypeError, ValueError):
            return {"error": "Invalid employee id", "status": 400}
        except Exception:
            return {"error": "Leave summary failed. LogID: {0}".format(
                self.__log.error(self.__exception.get_exception())), "status": 499}

    def is_start_date_or_end_date_in_holiday(self, start_date, end_date):
        in_holiday = False
        date_list = [start_date, end_date ]
        holidays = HolidayDA().get_holidays_in_date_list(date_list)
        if holidays:
            in_holiday = True
        return in_holiday