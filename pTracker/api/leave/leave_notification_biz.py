import json
from types import SimpleNamespace
from datetime import datetime, date, timedelta

from django.conf import Settings, settings
from django.db import  DatabaseError, transaction
from django.http import response
from django.template import loader


from pTracker.common.utility import Utility
from pTracker.common.exception_handler import ExceptionHandler
from pTracker.common.logs import Logs

# from pTracker.api.leave.leave_helper import LeaveHelperBL
# from pTracker.api.leave.leave_reports_biz import LeaveReportsBL

from pTracker.dataaccess.ptracker_access.leave_da import LeaveDA
from pTracker.dataaccess.ptracker_access.user_da import UserDA
from pTracker.dataaccess.ptracker_access.holiday_da import HolidayDA

from pTracker.notification_center.email_engine import Email
from pTracker.cronjobs.email_sender import send_email_notification
from pTracker.notification_center.push_notification_engine import PushNotification



def new_dto():
    dto = SimpleNamespace()
    return dto


class LeaveNotificationBL():
    def __init__(self):
        self.__log = Logs()
        self.__exception = ExceptionHandler()
        self.__utility = Utility()

    def generate_leave_email_message(self, email_dto):
        email_template = 'leave_request_template.html'
        context = {
            "heading": email_dto.heading,
            "lead_name": email_dto.lead_name,
            "request": email_dto.request,
            "reason": email_dto.reason,
            "emp_name": email_dto.emp_name,
            "submitted_date": email_dto.submitted_date,
            "status": email_dto.status,
            "category": email_dto.category,
            "start_date": email_dto.start_date,
            "end_date": email_dto.end_date,
            "link": email_dto.link,
            "no_of_days": email_dto.no_of_days
        }
        html_email = loader.render_to_string(email_template, context)
        return html_email

    def generate_email_message(self, email_dto):
        email_template = 'leave_approve_template.html'
        context = {
            "heading": email_dto.heading,
            "lead_name": email_dto.lead_name,
            "emp_name": email_dto.emp_name,
            "start_date": email_dto.start_date,
            "status": email_dto.status,
            "message": email_dto.message,
            "comment" : email_dto.comment,
            "no_of_days": email_dto.no_of_days
        }
        html_email = loader.render_to_string(email_template, context)
        return html_email

    def send_leave_request_notification(self, message, emp_name, to_email, subject, cc_addresses=[]):
        mail_dto = {}
        if cc_addresses == []:
            cc_addresses = [settings.LEAVE_DEFAULT_NOTIFOCATION_EMAIL]
        else:
            cc_addresses.append(settings.LEAVE_DEFAULT_NOTIFOCATION_EMAIL)
        mail_dto["subject"] = "DM DESK: {0} By {1}.".format(subject, emp_name)
        mail_dto["from_address"] = settings.EMAIL_ADDRESS['do_not_reply']['name']
        mail_dto["body"] = message
        mail_dto["to_addresses"] = [to_email]
        mail_dto["cc_addresses"] =  cc_addresses
        mail_dto["smtp_username"] = settings.EMAIL_ADDRESS['do_not_reply']['mailID']
        mail_dto["smtp_password"] = settings.EMAIL_ADDRESS['do_not_reply']['password']
        # uncomment to send mail TODO
        send_email_notification.apply_async([mail_dto, 1], queue=settings.CELERY_QUEUE['mail_sender'])

    def send_leave_request_update_notification(self, message, emp_name, to_email, subject, cc_addresses=[]):
        if cc_addresses == []:
            cc_addresses = [settings.LEAVE_DEFAULT_NOTIFOCATION_EMAIL]
        else:
            cc_addresses.append(settings.LEAVE_DEFAULT_NOTIFOCATION_EMAIL)
        mail_dto = {}
        mail_dto["subject"] = "DM DESK: {0} ".format(subject)
        mail_dto["from_address"] = settings.EMAIL_ADDRESS['do_not_reply']['name']
        mail_dto["body"] = message
        mail_dto["to_addresses"] = [to_email]
        mail_dto["cc_addresses"] = cc_addresses
        mail_dto["smtp_username"] = settings.EMAIL_ADDRESS['do_not_reply']['mailID']
        mail_dto["smtp_password"] = settings.EMAIL_ADDRESS['do_not_reply']['password']
        # un comment to send mail TODO
        send_email_notification.apply_async([mail_dto, 1], queue=settings.CELERY_QUEUE['mail_sender'])

    def setup_leave_request_email_content(self, user_id, leave_types, start_date, end_date, dt_start, dt_end, user_name, leave_request_data, notify, no_of_days = 1):
        email_content_dto = new_dto()
        lead_user = UserDA().get_my_lead(user_id)
        if lead_user:
            lead = UserDA().get_user_by_id(lead_user.lead_id)
            lead_name = lead.first_name
            to_email = lead.email
        #leave_types = helper.get_leave_type_dict()
        email_content_dto.heading = "Leave Request"
        if start_date == end_date:
            email_content_dto.request = "Please  grant me leave on {0} ".format(dt_start.strftime("%d/%m/%Y"))
        else:
            email_content_dto.request = "Please  grant me leave from {0} to {1} ".format(dt_start.strftime("%d/%m/%Y"), dt_end.strftime("%d/%m/%Y"))
        email_content_dto.emp_name = user_name
        email_content_dto.submitted_date = date.today().strftime("%d/%m/%Y")
        email_content_dto.status = 'Requested'
        email_content_dto.reason = leave_request_data['reason']
        email_content_dto.category = leave_types.get(int(leave_request_data['type_id']), '')
        email_content_dto.start_date = dt_start.strftime("%d/%m/%Y")
        email_content_dto.end_date = dt_end.strftime("%d/%m/%Y")
        email_content_dto.link = f"{settings.BASE_URL}leave/team-leave-summary"
        email_content_dto.no_of_days = no_of_days
        users = UserDA().get_all_active_users()
        cc_addresses = []
        if notify:
            for each in notify:
                if each['id'] != lead.id:
                    selected_user = users.get(id=each['id'])
                    if selected_user:
                        cc_addresses.append(selected_user.email)
        email_content_dto.lead_name = lead_name
        return email_content_dto, cc_addresses, to_email

    def send_single_push_notification(self, approver, title, body, sound = None, extra_kwargs=None):
        res = None
        device_info = UserDA().get_mobile_device_info_by_user_id(approver)
        if device_info:
            if device_info.device_identifier:
                res = PushNotification().notify_single_device(title=title, msg=body, \
                    registration_id=device_info.device_identifier, sound=sound, extra_kwargs=extra_kwargs)
        return res

    def generate_debit_leave_content(self, mail_dto):
        email_template = 'debit_leave_notofication.html'
        context = {
            "emp_name": mail_dto.emp_name,
            "dates": mail_dto.dates,
            'sender':mail_dto.sender,
            "designation":mail_dto.designation,
            "contact":mail_dto.contact

        }
        html_email = loader.render_to_string(email_template, context)
        return html_email

    def send_debit_leave_notification(self, to_email, subject, message ):
        cc_addresses = [settings.LEAVE_DEFAULT_NOTIFOCATION_EMAIL]
        mail_dto = {}
        mail_dto["subject"] = "DM DESK: {0} ".format(subject)
        mail_dto["from_address"] = settings.EMAIL_ADDRESS['do_not_reply']['name']
        mail_dto["body"] = message
        mail_dto["to_addresses"] = [to_email]
        mail_dto["cc_addresses"] = cc_addresses
        mail_dto["smtp_username"] = settings.EMAIL_ADDRESS['do_not_reply']['mailID']
        mail_dto["smtp_password"] = settings.EMAIL_ADDRESS['do_not_reply']['password']
        # un comment to send mail TODO
        send_email_notification.apply_async([mail_dto, 1], queue=settings.CELERY_QUEUE['mail_sender'])
