from types import SimpleNamespace

from django.conf import settings

from pTracker.common.logs import Logs
from pTracker.notification_center.email_engine import Email
from pTracker.dataaccess.ptracker_access.user_da import UserDA
from pTracker.common.exception_handler import ExceptionHandler
from pTracker.dataaccess.ptracker_access.attendance import AttendanceDA
from pTracker.api.leave.leave_biz import LeaveBL

from datetime import date,datetime

from pTracker.api.leave.leave_helper import LeaveHelperBL
from pTracker.common.utility import Utility
from pTracker.api.leave.leave_notification_biz import LeaveNotificationBL
from pTracker.common.company_authorization import data_scope, SCOPE_ALL, SCOPE_TEAM
from pTracker.common.company_authorization import users_with_capability
from pTracker.common.company_authorization import oversees_employee
from pTracker.common.company_context import get_active_company_id

def new_dto():
    dto = SimpleNamespace()
    return dto

class WorkFromHomeBL():

    def __init__(self):
        self.__logs = Logs()
        self.__exception = ExceptionHandler()
        self.__utility = Utility()

    def get_all_wfh_requests(self, user_id):
        result = {"error": None, "my_wfh_requests": [], "team_wfh_requests": []}
        try:

            emps = UserDA().get_all_active_users()
            emp_dict = {}
            if emps:
                temp_list = []
                for emp in emps:
                    emp_dict[emp.id] = emp.first_name + " " + emp.last_name

            temp_res = self.get_all_my_wfh_requests(user_id, emp_dict)
            result['my_wfh_requests'] = temp_res['wfh_requests']
            if temp_res['error']:
                result['error'] = temp_res['error']

            temp_res = self.get_all_my_team_wfh_requests(user_id, emp_dict)
            result['team_wfh_requests'] = temp_res['wfh_requests']
            if temp_res['error']:
                result['error'] = temp_res['error']

        except Exception as err:
            result["error"] = settings.ERROR_MSG['application_error']\
                .format(err, self.__logs.error(self.__exception.get_exception()))
        finally:
            return result

    def get_all_my_wfh_requests(self, user_id, emp_dict):
        result = {"error": None, "wfh_requests": []}
        wfh_request_list = []
        try:
            wfh_requests = AttendanceDA().get_all_wfh_requests_by_user_id(user_id)
            if wfh_requests:
                for wfh_request in wfh_requests:
                    date_range = Utility().get_date_range(wfh_request.start_date,wfh_request.end_date)
                    no_of_days = len(date_range)
                    temp = {
                        'wfh_id': wfh_request.wfh_id,
                        'start_date': wfh_request.start_date,
                        'end_date': wfh_request.end_date,
                        'emp_name': emp_dict.get(wfh_request.emp_id, ''),
                        'emp_id': wfh_request.emp_id,
                        'approver': emp_dict.get(wfh_request.approver_id, ''),
                        'status': settings.WFH_REQUEST_STATUS[wfh_request.status],
                        'reason': wfh_request.reason,
                        'comment': wfh_request.comment,
                        'created_date': wfh_request.created_date,
                        "no_of_days": no_of_days
                    }
                    wfh_request_list.append(temp)
                    del temp
                result['wfh_requests'] = wfh_request_list

        except Exception as err:
            result["error"] = settings.ERROR_MSG['application_error']\
                .format(err, self.__logs.error(self.__exception.get_exception()))
        finally:
            return result

    def __is_access_to_team_wfh_request(self, scope):
        return scope is not None


    def get_all_my_team_wfh_requests(self, user_id, emp_dict):
        result = {"error": None, "wfh_requests": []}
        wfh_request_list = []
        user_da = UserDA()
        try:
            scope = data_scope(user_id, 'attendance')
            if not self.__is_access_to_team_wfh_request(scope):
                return result

            if scope == SCOPE_TEAM:
                team_member_list = user_da.get_current_team_members_by_lead_id(user_id)
            else:
                team_member_list = user_da.get_all_active_users()
            team = []
            for each in team_member_list:
                team.append(each.id)
            try:
                team.remove(user_id)
            except:
                pass
            today = datetime.now()
            wfh_requests = AttendanceDA().get_all_wfh_requests() #'Requested'
            if wfh_requests:
                for wfh_request in wfh_requests:
                    if wfh_request.emp_id not in team:
                        continue
                    date_range = Utility().get_date_range(wfh_request.start_date,wfh_request.end_date)
                    no_of_days = len(date_range)
                    temp = {
                        'wfh_id': wfh_request.wfh_id,
                        'start_date': wfh_request.start_date,
                        'end_date': wfh_request.end_date,
                        'emp_name': emp_dict.get(wfh_request.emp_id, ''),
                        'emp_id': wfh_request.emp_id,
                        'approver': emp_dict.get(wfh_request.approver_id, ''),
                        'status': settings.WFH_REQUEST_STATUS[wfh_request.status],
                        'reason': wfh_request.reason,
                        'comment': wfh_request.comment,
                        'created_date': wfh_request.created_date,
                        'no_of_days': no_of_days,
                        'is_cancel' : 0
                    }
                    if wfh_request.start_date > today.date():
                        temp['is_cancel'] = 1
                    wfh_request_list.append(temp)
                    del temp
                result['wfh_requests'] = wfh_request_list

        except Exception as err:
            result["error"] = settings.ERROR_MSG['application_error']\
                .format(err, self.__logs.error(self.__exception.get_exception()))
        finally:
            return result

    def create_wfh_request(self, data, user_id, is_mobile=0):
        """ Creates a pending WFH request for the caller in their company. The
        approver is their reporting lead; without one the company's attendance
        approvers (attendance.view_all) are notified instead. """
        result = {"error": "", "success": "", "status": 200}
        message = 'WFH Request'
        try:
            validation = self.wfh_date_validation(data.get('start_date'), data.get('end_date'), user_id)
            if validation['message'] or validation['error']:
                result['error'] = validation['message'] or validation['error']
                result['status'] = 400 if validation['message'] else 499
                return result
            notify_ids, notify_error = self.__notify_ids(user_id, data.get('notify'))
            if notify_error:
                result['error'] = notify_error
                result['status'] = 400
                return result

            emp = UserDA().get_user_by_id(user_id)
            emp_name = f"{emp.first_name} {emp.last_name}" if emp else ''
            lead_user = UserDA().get_my_lead(user_id)
            lead = UserDA().get_user_by_id(lead_user.lead_id) if lead_user else None
            approver_id = lead.id if lead else 0
            recipients = [lead] if lead else [u for u in UserDA().get_all_active_users().filter(
                id__in=list(users_with_capability('attendance.view_all'))) if u.id != user_id]

            wfh_request = AttendanceDA().create_wfh_request({
                "start_date": data.get('start_date'),
                "end_date": data.get('end_date'),
                "emp_id": user_id,
                "approver_id": approver_id,
                "status": 1,  # Requested
                "reason": data.get('reason') or '',
                "notify": ','.join(str(n) for n in notify_ids),
                "company_id": UserDA().get_user_organization(user_id),
            })
            result['success'] = "WFH request created successfully"

            # notification mail: to the lead (or the first company approver), others in cc
            start = datetime.strptime(wfh_request.start_date, "%Y-%m-%d")
            end = datetime.strptime(wfh_request.end_date, "%Y-%m-%d")
            no_of_days = (end - start).days + 1
            email_content_dto = new_dto()
            email_content_dto.heading = "Work From Home Request"
            email_content_dto.lead_name = recipients[0].first_name if recipients else ''
            if start == end:
                email_content_dto.request = "Please  grant me WFH on {0} ".format(start.strftime("%d/%m/%Y"))
            else:
                email_content_dto.request = "Please  grant me WFH  from {0} to {1} ".format(
                    start.strftime("%d/%m/%Y"), end.strftime("%d/%m/%Y"))
            email_content_dto.no_of_days = no_of_days
            email_content_dto.emp_name = emp_name
            email_content_dto.submitted_date = date.today().strftime("%d/%m/%Y")
            email_content_dto.status = 'Requested'
            email_content_dto.reason = wfh_request.reason
            email_content_dto.category = 'WFH'
            email_content_dto.start_date = start.strftime("%d/%m/%Y")
            email_content_dto.end_date = end.strftime("%d/%m/%Y")
            email_content_dto.link = f"{settings.BASE_URL}attendance/wfh"
            email_content_dto.message = message
            if recipients:
                email_msg = LeaveNotificationBL().generate_leave_email_message(email_content_dto)
                LeaveNotificationBL().send_leave_request_notification(
                    email_msg, emp_name, recipients[0].email, message, [u.email for u in recipients[1:]])

            if is_mobile and approver_id:
                user_profile = UserDA().get_user_profile_by_id(wfh_request.emp_id)
                emp_image = f"{settings.DEFAULT_SITE_MEDIA_URL}{user_profile.profile_photo}" if user_profile else ''
                title = "Notification from DM Desk"
                msg = emp_name + " has requested work from home for " + str(no_of_days) + \
                    (" days." if no_of_days > 1 else " day.")
                push_data = {
                    "notificationType": "WFH_REQUEST",
                    "notificationInfo": {
                        "wfh_id": wfh_request.wfh_id,
                        "start_date": start.strftime("%Y-%m-%d"),
                        "end_date": end.strftime("%Y-%m-%d"),
                        "emp_name": emp_name,
                        "emp_id": user_id,
                        "approver": f"{lead.first_name} {lead.last_name}",
                        "status": "Requested",
                        "reason": wfh_request.reason,
                        "comment": "",
                        "created_date": date.today().strftime("%Y-%m-%d"),
                        "no_of_days": no_of_days,
                        "is_cancel": 0,
                        "approver_id": approver_id,
                        "emp_image": emp_image
                    }
                }
                LeaveNotificationBL().send_single_push_notification(approver_id, title, msg, sound="default",
                                                                    extra_kwargs=push_data)
        except Exception:
            result['status'] = 499
            result["error"] = "WFH request failed. LogID: {0}".format(
                self.__logs.error(self.__exception.get_exception()))
        return result

    def __notify_wfh_cancelled(self, wfh_request, user, comment, message):
        """ Cancelled by the employee -> tell the approver (else their lead, else
        the company's attendance approvers); cancelled by an approver -> tell the
        employee. """
        employee = UserDA().get_user_by_id(wfh_request.emp_id)
        if user.id == wfh_request.emp_id:
            approver_id = wfh_request.approver_id or UserDA().get_lead_id_by_user(wfh_request.emp_id)
            recipient_ids = [approver_id] if approver_id else \
                [uid for uid in users_with_capability('attendance.view_all') if uid != wfh_request.emp_id]
        else:
            recipient_ids = [wfh_request.emp_id]
        recipients = list(UserDA().get_all_active_users().filter(id__in=recipient_ids))
        if not recipients or not employee:
            return
        days = (wfh_request.end_date - wfh_request.start_date).days + 1
        dto = new_dto()
        dto.heading = 'WFH Request Cancelled'
        dto.status = 'cancelled'
        dto.lead_name = f"{user.first_name} {user.last_name}"
        dto.emp_name = f"{employee.first_name} {employee.last_name}"
        dto.start_date = wfh_request.start_date.strftime("%d/%m/%Y")
        dto.no_of_days = '1 day' if days == 1 else f'{days} days'
        dto.comment = comment
        dto.message = message
        email_msg = LeaveNotificationBL().generate_email_message(dto)
        LeaveNotificationBL().send_leave_request_update_notification(
            email_msg, dto.lead_name, recipients[0].email, dto.heading, [r.email for r in recipients[1:]])

    def __company_wfh_request(self, wfh_id):
        """ The WFH request if it belongs to the active company, else None. """
        wfh_request = AttendanceDA().get_wfh_request_by_id(wfh_id)
        if not wfh_request or wfh_request.company_id != get_active_company_id():
            return None
        return wfh_request

    def __notify_ids(self, user_id, notify):
        """ notify as a list or comma separated ids -> (ids, error). Only active
        employees of the caller's company may be notified. """
        if notify in (None, '', []):
            return [], None
        items = notify if isinstance(notify, list) else str(notify).split(',')
        ids = []
        for item in items:
            try:
                ids.append(int(item['id'] if isinstance(item, dict) else str(item).strip()))
            except (TypeError, ValueError, KeyError):
                return [], 'Invalid notify list'
        if LeaveHelperBL().invalid_notify_ids(user_id, ids):
            return [], 'Notify list can only contain active employees of your company'
        return ids, None

    def update_wfh_request(self, data, user, is_mobile= 0):
        result = {"error": "", "success": "", "status": 200}
        email_content_dto = new_dto()
        to_email = ''
        message = 'WFH Request'
        try:

            #Aprove or Reject
            #input wfh_data = {"req_type": "APPROVE", "wfh_id": "","status": "","emp_id": 0,"comment": ''}

            #Cancel Request
            #input wfh_data = {"req_type": "CANECL", "wfh_id": "", "comment": ''}

            #Edit Request
            #input :  wfh_data = {"req_type": "EDIT", "wfh_id": "", "start_date": "",  "end_date": "", "reason": ""},
            user_id = user.id
            req_type = data.get('req_type', '')
            wfh_id = data.get('wfh_id', 0)

            #APPROVE
            if req_type.upper() == 'APPROVE':
                comment = data.get('comment', '')
                try:
                    status = int(data.get('status', 0))
                except (TypeError, ValueError):
                    status = 0
                if status not in (settings.WFH_REQUEST_STATUS_V1['Approved'], settings.WFH_REQUEST_STATUS_V1['Rejected']):
                    result['error'] = "status must be 2 (Approved) or 4 (Rejected)"
                    result['status'] = 400
                    return result
                wfh_request = self.__company_wfh_request(wfh_id)
                if not wfh_request:
                    result['error'] = "WFH request not found"
                    result['status'] = 404
                    return result
                emp_id = wfh_request.emp_id
                # the employee's lead, or a company-wide attendance approver - never yourself
                if emp_id == user_id or not (UserDA().is_team_member(emp_id, user_id)
                                             or data_scope(user_id, 'attendance') == SCOPE_ALL):
                    result["error"] = settings.ERROR_MSG['no_permission']
                    result['status'] = 403
                    return result
                if wfh_request.status == status:
                    result['success'] = "Nothing To Change."
                    result['status'] = 400
                    return result
                wfh_requests = AttendanceDA().\
                    update_wfh_request(wfh_id, {"status": status, "comment": comment, 'approver_id': user_id})
                wfh_request = AttendanceDA().get_wfh_request_by_id(wfh_id)
                result['success'] = "WFH request approved successfully"

                # send notification mail
                date_range = wfh_request.end_date - wfh_request.start_date
                if ( date_range.days + 1 ) == 1:
                    email_content_dto.no_of_days = '1 day'
                else:
                    email_content_dto.no_of_days = str(date_range.days + 1) + ' ' + 'days'
                employee = UserDA().get_user_by_id(emp_id)
                approver_name = user.first_name + ' ' + user.last_name
                email_content_dto.lead_name = approver_name
                email_content_dto.emp_name = employee.first_name + ' ' +employee.last_name
                email_content_dto.start_date = wfh_request.start_date.strftime("%d/%m/%Y")
                if settings.WFH_REQUEST_STATUS[int(status)] == 'Approved':
                    email_content_dto.heading = 'WFH Request Approved'
                    email_content_dto.status = 'approved'
                    notificationType = "WFH_APPROVED"
                    result['success'] = "WFH request approved successfully"
                if settings.WFH_REQUEST_STATUS[int(status)] == 'Rejected':
                    email_content_dto.heading = 'WFH Request Rejected'
                    email_content_dto.status = 'rejected'
                    notificationType = "WFH_REJECTED"
                    result['success'] = "WFH request rejected successfully"
                if comment:
                    email_content_dto.comment = comment
                else:
                    email_content_dto.comment = ''
                email_content_dto.message = message
                email_msg = LeaveNotificationBL().generate_email_message(email_content_dto)
                to_email = employee.email
                LeaveNotificationBL().send_leave_request_update_notification(email_msg, approver_name, to_email, email_content_dto.heading)

                if is_mobile:
                    emp_image = ''
                    user_profile = UserDA().get_user_profile_by_id(wfh_request.emp_id)
                    if user_profile:
                        emp_image =  f"{settings.DEFAULT_SITE_MEDIA_URL}{user_profile.profile_photo}"
                    title = "Notification from DM Desk"
                    msg = approver_name + " has "+ settings.WFH_REQUEST_STATUS[int(status)] +" your work from home for " + str(email_content_dto.no_of_days)
                    data= {
                        "notificationType" : notificationType,
                        "notificationInfo" : {
                            "wfh_id":  wfh_request.wfh_id,
                            "start_date": wfh_request.start_date.strftime("%Y-%m-%d"), # datetime.strptime(wfh_request.start_date, "%d/%m/%Y").strftime("%Y-%m-%d"),
                            "end_date": wfh_request.end_date.strftime("%Y-%m-%d"), # datetime.strptime(wfh_request.end_date, "%d/%m/%Y").strftime("%Y-%m-%d"),
                            "emp_name": employee.first_name + ' ' +employee.last_name,
                            "emp_id": wfh_request.emp_id,
                            "approver":approver_name,
                            "status": settings.WFH_REQUEST_STATUS[int(status)],
                            "reason": wfh_request.reason,
                            "comment": comment,
                            "created_date": wfh_request.created_date.strftime("%Y-%m-%d"),
                            "no_of_days": email_content_dto.no_of_days,
                            "is_cancel": 0,
                            "approver_id": user_id,
                            "emp_image": emp_image
                        }
                    }
                    LeaveNotificationBL().send_single_push_notification(wfh_request.emp_id, title, msg, sound="default",extra_kwargs=data)
            #CANCEL
            elif req_type.upper() == 'CANCEL':
                if not wfh_id:
                    result['error'] = "wfh_id is required"
                    result['status'] = 400
                    return result
                wfh_request = self.__company_wfh_request(wfh_id)
                if not wfh_request:
                    result['error'] = "WFH request not found"
                    result['status'] = 404
                    return result
                # the requester, or an approver: their lead or attendance.view_all
                if wfh_request.emp_id != user_id and \
                        not oversees_employee(user_id, wfh_request.emp_id, module='attendance'):
                    result["error"] = settings.ERROR_MSG['no_permission']
                    result['status'] = 403
                    return result
                if wfh_request.status == 3:
                    result['error'] = "WFH Request Already Cancelled, Not Able To Process."
                    result['status'] = 400
                    return result
                if wfh_request.status == 4 or (wfh_request.status == 2 and wfh_request.start_date <= date.today()):
                    result['error'] = "Only pending WFH, or approved WFH that has not started yet, can be cancelled"
                    result['status'] = 400
                    return result
                comment = data.get('comment', '') or ''
                AttendanceDA().update_wfh_request(wfh_id, {"status": 3, "comment": comment})
                result['success'] = "WFH request cancelled successfully"
                self.__notify_wfh_cancelled(wfh_request, user, comment, message)

            #EDIT
            elif req_type.upper() == 'EDIT':
                wfh_request = self.__company_wfh_request(wfh_id)
                if not wfh_request:
                    result['error'] = "WFH request not found"
                    result['status'] = 404
                    return result
                if wfh_request.emp_id != user_id:
                    result["error"] = settings.ERROR_MSG['no_permission']
                    result['status'] = 403
                    return result
                if wfh_request.status != settings.WFH_REQUEST_STATUS_V1['Requested']:
                    result['error'] = "Only pending WFH requests can be edited"
                    result['status'] = 400
                    return result
                wfh_data = {"start_date": "", "end_date": "", "reason": ""}
                wfh_data['start_date'] = data.get('start_date', None)
                wfh_data['end_date'] = data.get('end_date', None)
                wfh_data['reason'] = data.get('reason', None) or ''
                validation = self.wfh_date_validation(wfh_data['start_date'],wfh_data['end_date'],user_id,wfh_id)
                if validation['message'] or validation['error']:
                    result['error'] = validation['message'] or validation['error']
                    result['status'] = 400 if validation['message'] else 499
                    return result
                AttendanceDA().update_wfh_request(wfh_id, wfh_data, user_id)
                result['success'] = "WFH request edited successfully"

            # result["success"] = "Being Awesome!"

        except Exception:
            result['status'] = 499
            result["error"] = "WFH request update failed. LogID: {0}".format(
                self.__logs.error(self.__exception.get_exception()))
        return result


    def generate_email_message(self, lead_name, emp_name):
        str_html = """
        <p>Hello {0},</p>
        <p>Your team member {1}, has requested for work from home option,
        Please do the needful.</p>
        <br>
        <p>Regards,</p>
        <p>Team DM DESK<br>
        </p><br>""".format(lead_name, emp_name)
        return str_html

    def send_wfh_notification_to_lead(self, message, emp_name, to_email):
        mail_dto = new_dto()
        mail_dto.subject = "DM DESK: WFH Request By {0} !!!".format(emp_name)
        mail_dto.from_address = settings.EMAIL_ADDRESS['do_not_reply']['name']
        mail_dto.body = message
        mail_dto.to_addresses = [to_email]
        mail_dto.smtp_username = settings.EMAIL_ADDRESS['do_not_reply']['mailID']
        mail_dto.smtp_password = settings.EMAIL_ADDRESS['do_not_reply']['password']
        Email().send_html_mail(mail_dto)

    def wfh_date_validation(self,start_date,end_date,user_id,edit_id=0):
        result = {"is_valid": '',
                "error": '',
                "message" : ''
                }
        try:
            try:
                start = datetime.strptime(str(start_date), "%Y-%m-%d")
                end = datetime.strptime(str(end_date), "%Y-%m-%d")
            except ValueError:
                result['message'] = "Invalid start or end date."
                result['is_valid'] = 0
                return result
            if start > end:
                result['message'] = "The start date should be less than or equal to the end date."
                result['is_valid'] = 0
                return result

            if (start.year == end.year) and (start.month == end.month):
                pass
            else:
                result['message'] = "You cannot apply for WFH for overlapping months. If your date range spans multiple months, please submit separate WFH requests for each month."
                result['is_valid'] = 0
                return result

            wfh_requests = AttendanceDA().get_wfh_request_date_overlap(start,end,user_id)
            if wfh_requests:
                if edit_id:
                    # status = settings.WFH_REQUEST_STATUS['Cancelled']
                    edit_excluded_wfh = wfh_requests.exclude(wfh_id = edit_id)
                    if edit_excluded_wfh:
                        result['message'] = "WFH request dates overlapping with previous requests"
                        result['is_valid'] = 0
                        return result
                else:
                    result['message'] = "WFH request dates overlapping with previous requests"
                    result['is_valid'] = 0
                    return result
        except Exception as err:
            result["error"] = settings.ERROR_MSG['application_error']\
                .format(err, self.__logs.error(self.__exception.get_exception()))
        return result

    def get_filtered_team_wfh_requests(self, user_id, status=0, month=0, year=0, is_mobile=0, direct_reporting = 0):
        result = {"error": None, "wfh_requests": []}
        wfh_request_list = []
        user_da = UserDA()
        try:
            scope = data_scope(user_id, 'attendance')
            if not self.__is_access_to_team_wfh_request(scope):
                return result

            if scope == SCOPE_TEAM:
                team_member_list = user_da.get_current_team_members_by_lead_id(
                    user_id)
            else:
                team_member_list = user_da.get_all_active_users()
            if is_mobile and direct_reporting:
                team_member_list = user_da.get_current_team_members_by_lead_id(
                    user_id)
            team = []
            for each in team_member_list:
                team.append(each.id)
            try:
                team.remove(user_id)
            except:
                pass
            emps = user_da.get_all_active_users()
            emp_dict = {}
            if emps:
                temp_list = []
                for emp in emps:
                    emp_dict[emp.id] = emp.first_name + " " + emp.last_name

            if is_mobile:
                wfh_requests = AttendanceDA().get_team_wfh_requests_by_status_list(status)
            else:
                wfh_requests = AttendanceDA().get_team_wfh_requests_by_status(status)
            if year and month:
                wfh_requests1 = wfh_requests.filter(start_date__month=month, start_date__year = year)
                wfh_requests2 = wfh_requests.filter(end_date__month=month, end_date__year = year)
                wfh_requests = (wfh_requests1 | wfh_requests2).distinct()
            today = datetime.now()
            if wfh_requests:
                for wfh_request in wfh_requests:
                    if wfh_request.emp_id not in team:
                        continue
                    date_range = Utility().get_date_range(
                        wfh_request.start_date, wfh_request.end_date)
                    no_of_days = len(date_range)
                    temp = {
                        'wfh_id': wfh_request.wfh_id,
                        'start_date': wfh_request.start_date,
                        'end_date': wfh_request.end_date,
                        'emp_name': emp_dict.get(wfh_request.emp_id, ''),
                        'emp_id': wfh_request.emp_id,
                        'approver': emp_dict.get(wfh_request.approver_id, ''),
                        'status': settings.WFH_REQUEST_STATUS[wfh_request.status],
                        'reason': wfh_request.reason,
                        'comment': wfh_request.comment,
                        'created_date': wfh_request.created_date,
                        'no_of_days': no_of_days,
                        'is_cancel' : 0
                    }
                    if is_mobile:
                        temp["approver_id"] = wfh_request.approver_id
                    if wfh_request.start_date > today.date():
                        temp['is_cancel'] = 1
                    wfh_request_list.append(temp)
                    del temp
                result['wfh_requests'] = wfh_request_list
        except Exception as err:
            result["error"] = settings.ERROR_MSG['application_error']\
                .format(err, self.__logs.error(self.__exception.get_exception()))
        finally:
            return result

    def get_filtered_my_wfh_requests(self,user_id,status = 0,month = 0,year = 0, is_mobile=0):
        result = {"error": None, "wfh_requests": []}
        wfh_request_list = []
        try:
            emps = UserDA().get_all_active_users()
            emp_dict = {}
            if emps:
                temp_list = []
                for emp in emps:
                    emp_dict[emp.id] = emp.first_name + " " + emp.last_name
            wfh_requests = AttendanceDA().get_all_wfh_requests_by_user_id(user_id)
            if status:
                wfh_requests = wfh_requests.filter(status = status)
            if year and month:
                wfh_requests1 = wfh_requests.filter(start_date__month=month, start_date__year = year)
                wfh_requests2 = wfh_requests.filter(end_date__month=month, end_date__year = year)
                wfh_requests = (wfh_requests1 | wfh_requests2).distinct()
            if wfh_requests:
                for wfh_request in wfh_requests:
                    date_range = Utility().get_date_range(wfh_request.start_date,wfh_request.end_date)
                    no_of_days = len(date_range)
                    temp = {
                        'wfh_id': wfh_request.wfh_id,
                        'start_date': wfh_request.start_date,
                        'end_date': wfh_request.end_date,
                        'emp_name': emp_dict.get(wfh_request.emp_id, ''),
                        'emp_id': wfh_request.emp_id,
                        'approver': emp_dict.get(wfh_request.approver_id, ''),
                        'status': settings.WFH_REQUEST_STATUS[wfh_request.status],
                        'reason': wfh_request.reason,
                        'comment': wfh_request.comment,
                        'created_date': wfh_request.created_date,
                        "no_of_days": no_of_days
                    }
                    if is_mobile:
                        temp["approver_id"] = wfh_request.approver_id
                    wfh_request_list.append(temp)
                    del temp
                result['wfh_requests'] = wfh_request_list
        except Exception as err:
            result["error"] = settings.ERROR_MSG['application_error']\
                .format(err, self.__logs.error(self.__exception.get_exception()))
        finally:
            return result

    def get_all_wfh_request_by_month_and_status_filter(self,user_id,status,month,year):
        result = {"error": None, "my_wfh_requests": [], "team_wfh_requests": []}
        try:
            temp_res = self.get_filtered_my_wfh_requests( user_id, status, month, year)
            result['my_wfh_requests'] = temp_res['wfh_requests']
            if temp_res['error']:
                result['error'] = temp_res['error']
            temp_res = self.get_filtered_team_wfh_requests(user_id, status, month, year)
            result['team_wfh_requests'] = temp_res['wfh_requests']
            if temp_res['error']:
                result['error'] = temp_res['error']
        except Exception as err:
            result["error"] = settings.ERROR_MSG['application_error']\
                .format(err, self.__logs.error(self.__exception.get_exception()))
        finally:
            return result


