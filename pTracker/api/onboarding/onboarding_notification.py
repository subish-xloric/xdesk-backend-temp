from types import SimpleNamespace

from django.conf import settings
from django.template import loader

from pTracker.common.utility import Utility
from pTracker.common.exception_handler import ExceptionHandler
from pTracker.common.logs import Logs

from pTracker.cronjobs.email_sender import send_email_notification


def new_dto():
    dto = SimpleNamespace()
    return dto


class OnBoardingNotificationBL():
    def __init__(self):
        self.__log = Logs()
        self.__exception = ExceptionHandler()
        self.__utility = Utility()

    def generate_on_boarding_email_message(self, email_dto):
        email_template = 'pre_employment_notification.html'
        context = {
            "heading": email_dto.heading,
            "hr_name": email_dto.hr_name,
            "candidate_name": email_dto.candidate_name,
            "link": email_dto.link,
            "designation": email_dto.designation,
            "company_name": email_dto.company_name,
            "company_name_short" : email_dto.company_name_short
        }
        html_email = loader.render_to_string(email_template, context)
        return html_email

    def send_on_boarding_request_notification(self, message, candidate_name, to_email, subject, cc_addresses=[]):
        mail_dto = {}
        mail_dto["subject"] = "{0} ".format(subject)
        mail_dto["from_address"] = settings.EMAIL_ADDRESS['do_not_reply']['name']
        mail_dto["body"] = message
        mail_dto["to_addresses"] = [to_email]
        mail_dto["cc_addresses"] =  cc_addresses
        mail_dto["smtp_username"] = settings.EMAIL_ADDRESS['do_not_reply']['mailID']
        mail_dto["smtp_password"] = settings.EMAIL_ADDRESS['do_not_reply']['password']
        send_email_notification.apply_async(
            [mail_dto, 1], queue=settings.CELERY_QUEUE['mail_sender'])