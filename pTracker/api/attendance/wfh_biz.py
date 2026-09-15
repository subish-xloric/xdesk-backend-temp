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

    def __is_access_to_team_wfh_request(self, user_id, role_id):
        is_access = False
        if role_id in (1, 2, 3, 4, "1", "2", "3", "4"):
            is_access = True
        return is_access


    def get_all_my_team_wfh_requests(self, user_id, emp_dict):
        result = {"error": None, "wfh_requests": []}
        wfh_request_list = []
        user_da = UserDA()
        try:
            role_id, role_name = user_da.get_user_role_by_id(user_id)
            if not self.__is_access_to_team_wfh_request(user_id, role_id):
                return result

            if role_id == 4:
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
        result = {"error": "", "success": "", "status": 200}
        email_content_dto = new_dto()
        lead_name = ''
        emp_name = ''
        to_email = ''
        message = 'WFH Request'
        no_days = 1
        try:
            emp = UserDA().get_user_by_id(user_id)
            if emp:
                emp_name = emp.first_name + " " + emp.last_name

            wfh_data = {
                "start_date": "",
                "end_date": "",
                "emp_id": 0,
                "approver_id": 0,
                "status": 1,
                "reason": "",
                "notify": ""
            }


            lead_user = UserDA().get_my_lead(user_id)
            if lead_user:
                approver_id = lead_user.lead_id
                lead=UserDA().get_user_by_id(lead_user.lead_id)
                lead_name = lead.first_name
                to_email = lead.email
            else:
                approver_id = 0
            wfh_data['start_date'] = data.get('start_date', None)
            wfh_data['end_date'] = data.get('end_date', None)
            wfh_data['reason'] = data.get('reason', None)
            wfh_data['notify'] = data.get('notify', None)
            wfh_data['emp_id'] = user_id
            wfh_data['status'] = 1  #Requested'
            wfh_data['approver_id'] = approver_id
            validation = self.wfh_date_validation(wfh_data['start_date'],wfh_data['end_date'],user_id)
            if validation['message']:
                result['error'] = validation['message']
                result['status'] = 499
                return result
            wfh_request = AttendanceDA().create_wfh_request(wfh_data)
            result['success'] = "WFH request created successfully"

            # send notification mail
            email_content_dto.heading = "Work From Home Request"
            email_content_dto.lead_name = lead_name
            start_date = datetime.strptime(
                wfh_request.start_date, "%Y-%m-%d").strftime("%d/%m/%Y")
            end_date = datetime.strptime(
                wfh_request.end_date, "%Y-%m-%d").strftime("%d/%m/%Y")
            if wfh_request.start_date == wfh_request.end_date:
                email_content_dto.request = "Please  grant me WFH on {0} ".format(start_date)
            else:
                email_content_dto.request = "Please  grant me WFH  from {0} to {1} ".format(
                    start_date, end_date)
            date_range = datetime.strptime(wfh_request.end_date, "%Y-%m-%d") - \
                datetime.strptime(wfh_request.start_date, "%Y-%m-%d")
            if (date_range.days+1) == 1:
                email_content_dto.no_of_days = 1
            else:
                email_content_dto.no_of_days = date_range.days + 1

            email_content_dto.emp_name = emp_name
            email_content_dto.submitted_date = date.today().strftime("%d/%m/%Y")
            email_content_dto.status = 'Requested'
            email_content_dto.reason = wfh_request.reason
            email_content_dto.category = 'WFH'
            email_content_dto.start_date = start_date
            email_content_dto.end_date = end_date
            email_content_dto.link = f"{settings.BASE_URL}attendance/wfh"
            email_content_dto.message = message
            email_msg = LeaveNotificationBL().generate_leave_email_message(email_content_dto)
            LeaveNotificationBL().send_leave_request_notification(email_msg, emp_name, to_email, message) #TODO
            if is_mobile:
                approver_name = ''
                emp_image = ''
                approver_details = UserDA().get_user_by_id(approver_id)
                if approver_details:
                    approver_name = approver_details.first_name + " " + approver_details.last_name
                    user_profile = UserDA().get_user_profile_by_id(wfh_request.emp_id)
                if user_profile:
                    emp_image =  f"{settings.DEFAULT_SITE_MEDIA_URL}{user_profile.profile_photo}"
                title = "Notification from DM Desk"
                msg = emp_name + " has requested work from home for " + str(email_content_dto.no_of_days) + " day."
                if email_content_dto.no_of_days > 1:
                    msg = emp_name + " has requested work from home for " + str(email_content_dto.no_of_days) + " days."
                data= {
                    "notificationType" : "WFH_REQUEST",
                    "notificationInfo" : {
                        "wfh_id":  wfh_request.wfh_id,
                        "start_date":datetime.strptime(start_date, "%d/%m/%Y").strftime("%Y-%m-%d"),
                        "end_date": datetime.strptime(end_date, "%d/%m/%Y").strftime("%Y-%m-%d"),
                        "emp_name": emp_name,
                        "emp_id": user_id,
                        "approver":approver_name,
                        "status": "Requested",
                        "reason": wfh_request.reason,
                        "comment": "",
                        "created_date": date.today().strftime("%Y-%m-%d"),
                        "no_of_days": email_content_dto.no_of_days,
                        "is_cancel": 0,
                        "approver_id": approver_id,
                        "emp_image": emp_image
                    }
                }
                LeaveNotificationBL().send_single_push_notification(approver_id, title, msg, sound="default",extra_kwargs=data)


        except Exception as err:
            result['status'] = 499
            result["error"] = settings.ERROR_MSG['application_error']\
                .format(err, self.__logs.error(self.__exception.get_exception()))
        return result


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
                status = data.get('status', 0)
                emp_id = data.get('emp_id', 0)
                comment = data.get('comment', '')
                if not UserDA().is_team_member(emp_id, user_id):
                    result["error"] = settings.ERROR_MSG['no_permission']
                    result['status'] = 403
                    return result
                wfh_request = AttendanceDA().get_wfh_request_by_id(wfh_id)
                if wfh_request:
                    if wfh_request.status == status:
                        result['success'] = "Nothing To Change."
                        result['status'] = 499
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
                wfh_request = AttendanceDA().get_wfh_request_by_id(wfh_id)
                if wfh_request.status == 3:
                        result['success'] = "WFH Request Already Cancelled, Not Able To Process."
                        result['status'] = 499
                        return result
                comment = data.get('comment', '')
                AttendanceDA().update_wfh_request(wfh_id, {"status": 3, "comment": comment})
                result['success'] = "WFH request cancelled successfully"

            #EDIT
            elif req_type.upper() == 'EDIT':
                wfh_data = {"start_date": "", "end_date": "", "reason": ""}
                wfh_data['start_date'] = data.get('start_date', None)
                wfh_data['end_date'] = data.get('end_date', None)
                wfh_data['reason'] = data.get('reason', None)
                validation = self.wfh_date_validation(wfh_data['start_date'],wfh_data['end_date'],user_id,wfh_id)
                if validation['message']:
                    result['error'] = validation['message']
                    result['status'] = 499
                    return result
                AttendanceDA().update_wfh_request(wfh_id, wfh_data, user_id)
                result['success'] = "WFH request edited successfully"

            # result["success"] = "Being Awesome!"

        except Exception as err:
            result['status'] = 499
            result["error"] = settings.ERROR_MSG['application_error']\
                .format(err, self.__logs.error(self.__exception.get_exception()))
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
            start = datetime.strptime(start_date, "%Y-%m-%d")
            end = datetime.strptime(end_date, "%Y-%m-%d")
            duration = Utility().get_date_range(start, end)
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
            role_id, role_name = user_da.get_user_role_by_id(user_id)
            if not self.__is_access_to_team_wfh_request(user_id, role_id):
                return result

            if role_id == 4:
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


