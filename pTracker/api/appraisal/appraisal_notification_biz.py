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


class AppraisalNotificationBL():
    def __init__(self):
        self.__log = Logs()
        self.__exception = ExceptionHandler()
        self.__utility = Utility()

    def generate_appraisal_issue_email_message(self, email_dto):
        email_template = 'appraisal_issue_mail.html'
        context = {
            "heading": email_dto.heading,
            "emp_name": email_dto.emp_name,
            "date": email_dto.date,
            "link": email_dto.link,
            "hr_name": email_dto.hr_name,
            "year": email_dto.year,
            "appraiser_expiry_date": email_dto.appraiser_expiry_date,
            "reviewer_expiry_date": email_dto.reviewer_expiry_date,
            "employee_expiry_date": email_dto.employee_expiry_date
        }
        html_email = loader.render_to_string(email_template, context)
        return html_email

    def send_appraisal_notification(self, message, emp_name, to_email, subject, cc_addresses=[]):
        mail_dto = {}
        mail_dto["subject"] = "{0} - {1}.".format(emp_name, subject)
        mail_dto["from_address"] = settings.EMAIL_ADDRESS['do_not_reply']['name']
        mail_dto["body"] = message
        mail_dto["to_addresses"] = [to_email]
        mail_dto["cc_addresses"] = cc_addresses
        mail_dto["smtp_username"] = settings.EMAIL_ADDRESS['do_not_reply']['mailID']
        mail_dto["smtp_password"] = settings.EMAIL_ADDRESS['do_not_reply']['password']
        send_email_notification.apply_async(
            [mail_dto, 1], queue=settings.CELERY_QUEUE['mail_sender'])

    def generate_appraisal_update_notification(self, email_dto):
        email_template = 'appraisal_update_notification.html'
        context = {
            "heading": email_dto.heading,
            "reciever_name": email_dto.reciever_name,
            "message": email_dto.message,
            "link": email_dto.link,
        }
        html_email = loader.render_to_string(email_template, context)
        return html_email
    
    def send_appraisal_summary_notification(self, message, to_email, subject, publish_dict={}, cc_addresses=[]):
        mail_dto = {}
        mail_dto["subject"] = subject
        mail_dto["from_address"] = settings.EMAIL_ADDRESS['do_not_reply']['name']
        mail_dto["body"] = message
        mail_dto["to_addresses"] = [to_email]
        mail_dto["cc_addresses"] = cc_addresses
        mail_dto["smtp_username"] = settings.EMAIL_ADDRESS['do_not_reply']['mailID']
        mail_dto["smtp_password"] = settings.EMAIL_ADDRESS['do_not_reply']['password']
        if publish_dict:
            mail_dto["file_name"] = publish_dict['file_name']
            mail_dto["file_path"] = publish_dict['file_path']
        send_email_notification.apply_async(
            [mail_dto, 1], queue=settings.CELERY_QUEUE['mail_sender'])

    def generate_appraisal_normalization_summary(self, email_dto):
        email_template = 'appraisal_normalization_result_summary.html'
        context = {
            "heading": email_dto.heading,
            "summary": email_dto.summary
        }
        html_email = loader.render_to_string(email_template, context)
        return html_email
