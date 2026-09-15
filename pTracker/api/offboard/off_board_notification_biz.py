from types import SimpleNamespace
from datetime import datetime, timedelta

from django.conf import settings
from django.template import loader

from pTracker.common.utility import Utility
from pTracker.common.exception_handler import ExceptionHandler
from pTracker.common.logs import Logs

from pTracker.cronjobs.email_sender import send_email_notification


def new_dto():
    dto = SimpleNamespace()
    return dto


class OffBoardNotificationBL():
    def __init__(self):
        self.__log = Logs()
        self.__exception = ExceptionHandler()
        self.__utility = Utility()

    def generate_off_board_email_message(self, email_dto):
        email_template = 'off_board_request.html'
        context = {
            "heading": email_dto.heading,
            "reason": email_dto.reason,
            "emp_name": email_dto.emp_name,
            "subject": email_dto.subject
        }
        html_email = loader.render_to_string(email_template, context)
        return html_email

    def send_off_board_request_notification(self, message, emp_name, to_email, subject, cc_addresses=[]):
        mail_dto = {}
        mail_dto["subject"] = "DM DESK: {0} ".format(subject)
        mail_dto["from_address"] = settings.EMAIL_ADDRESS['do_not_reply']['name']
        mail_dto["body"] = message
        mail_dto["to_addresses"] = [to_email]
        mail_dto["cc_addresses"] = cc_addresses
        mail_dto["smtp_username"] = settings.EMAIL_ADDRESS['do_not_reply']['mailID']
        mail_dto["smtp_password"] = settings.EMAIL_ADDRESS['do_not_reply']['password']
        send_email_notification.apply_async(
            [mail_dto, 1], queue=settings.CELERY_QUEUE['mail_sender'])

    def generate_off_board_update_email_message(self, email_dto):
        email_template = 'off_bord_request_update.html'
        context = {
            "heading": email_dto.heading,
            "lead_name": email_dto.lead_name,
            "request": email_dto.request,
            "emp_name": email_dto.emp_name,
            "relieving_date": email_dto.relieving_date,
            "action": email_dto.action,
            "comment": email_dto.comment
        }
        html_email = loader.render_to_string(email_template, context)
        return html_email

    def generate_exit_form_initaiated_email_message(self, email_dto):
        email_template = 'exit_form_initated_mail.html'
        context = {
            "heading": email_dto.heading,
            "emp_name": email_dto.emp_name,
            "date": email_dto.date,
            "link": email_dto.link,
            "hr_name": email_dto.hr_name
        }
        html_email = loader.render_to_string(email_template, context)
        return html_email

    def generate_exit_interview_email_message(self, email_dto):
        email_template = 'exit_interview_mail.html'
        context = {
            "heading": email_dto.heading,
            "emp_name": email_dto.emp_name,
            "date": email_dto.date,
            "link": email_dto.link,
            "hr_name": email_dto.hr_name
        }
        html_email = loader.render_to_string(email_template, context)
        return html_email

    def send_off_board_request_create_notification(self, message, emp_name, to_email, subject, cc_addresses=[]):

        mail_dto = {}
        mail_dto["subject"] = "DM DESK: {0} ".format(subject)
        mail_dto["from_address"] = settings.EMAIL_ADDRESS['do_not_reply']['name']
        mail_dto["body"] = message
        mail_dto["to_addresses"] = [to_email]
        mail_dto["cc_addresses"] = cc_addresses
        mail_dto["smtp_username"] = settings.EMAIL_ADDRESS['do_not_reply']['mailID']
        mail_dto["smtp_password"] = settings.EMAIL_ADDRESS['do_not_reply']['password']
        send_email_notification.apply_async(
            [mail_dto, 1], queue=settings.CELERY_QUEUE['mail_sender'])


    def generate_off_board_accept_email_message(self, email_dto):
        email_template = 'off_boarding_accepted.html'
        context = {
            "heading": email_dto.heading,
            "emp_name": email_dto.employee_name,
            "job_title": email_dto.job_title,
            "organization": email_dto.organization,
            "relieving_date": email_dto.relieving_date,
            "HR_name": email_dto.HR_name
        }
        html_email = loader.render_to_string(email_template, context)
        return html_email
    
    def generate_termination_message(self, email_dto):
        email_template = 'termination_letter.html'
        context = {
            "subject": email_dto.subject,
            "emp_name": email_dto.emp_name,
            "date": email_dto.date,
            "company_name": email_dto.company_name,
            "reason": email_dto.reason
        }
        html_email = loader.render_to_string(email_template, context)
        return html_email



    def generate_relieving_message(self, email_dto):
        email_template = 'relieving_letter.html'
        context = {
            "subject": email_dto.subject,
            "emp_name": email_dto.emp_name,
            "date": email_dto.date,
            "company_name": email_dto.company_name,
            "reason": email_dto.reason
        }
        html_email = loader.render_to_string(email_template, context)
        return html_email