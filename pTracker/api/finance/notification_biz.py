import json
from types import SimpleNamespace
from datetime import datetime, date, timedelta

from django.conf import settings
from django.db import  DatabaseError, transaction
from django.http import response
from django.template import loader


from pTracker.common.utility import Utility
from pTracker.common.exception_handler import ExceptionHandler
from pTracker.common.logs import Logs

from pTracker.notification_center.email_engine import Email
from pTracker.cronjobs.email_sender import send_email_notification
from pTracker.dataaccess.ptracker_access.user_da import UserDA
from pTracker.dataaccess.ptracker_access.interview_da import InterviewDA

def new_dto():
    dto = SimpleNamespace()
    return dto


class NotificationBL():
    def __init__(self):
        self.__log = Logs()
        self.__exception = ExceptionHandler()
        self.__utility = Utility()


    def generate_email_for_claim_approval_rejection(self, email_dto):
        email_template = email_dto.page
        context = {
            "heading": email_dto.heading,
            "comment": email_dto.comment,
            "initiator_name": email_dto.initiator_name,
            "initiator_designation": email_dto.initiator_designation,
            "initiator_email": email_dto.initiator_email,
            "emp_name": email_dto.emp_name,
            "deadline_date": email_dto.deadline_date,
            "section": email_dto.section,
            "category": email_dto.category,
            "submitted_date": email_dto.submitted_date,
            "claim_amount":email_dto.claim_amount,
            "is_receipt":email_dto.is_receipt,
        }
        html_email = loader.render_to_string(email_template, context)
        return html_email
    
    
    def generate_email_for_sugesstion_message(self, email_dto):
        email_template = email_dto.page
        context = {
            "heading": email_dto.heading,
            "message": email_dto.message,
            "initiator_name": email_dto.initiator_name,
            "initiator_designation": email_dto.initiator_designation,
            "initiator_email": email_dto.initiator_email,
            "emp_name": email_dto.emp_name,
        }
        html_email = loader.render_to_string(email_template, context)
        return html_email

    def generate_email_for_tax_deduction_reminder(self, email_dto):
        email_template = email_dto.page
        context = {
            "claimed_amount": email_dto.claimed_amount,
            "round_submit_percentage": email_dto.round_submit_percentage,
            "estimated_amount": email_dto.estimated_amount,
            "heading": email_dto.heading,
            "initiator_name": email_dto.initiator_name,
            "initiator_designation": email_dto.initiator_designation,
            "initiator_email": email_dto.initiator_email,
            "emp_name": email_dto.emp_name,
        }
        html_email = loader.render_to_string(email_template, context)
        return html_email


    def generate_initiate_email_messages(self, email_dto):
        email_template = 'send_initiate_claim_email.html'
        context = {
            "heading": email_dto.heading,
            "comment": email_dto.comment,
            "emp_name": email_dto.emp_name,
            "emp_designation": email_dto.emp_designation,
            "emp_email": email_dto.emp_email,
            "last_date_of_declaration": email_dto.last_date_of_declaration,
        }
        html_email = loader.render_to_string(email_template, context)
        return html_email

    def generate_initiate_employee_email_messages(self, email_dto):
        email_template = 'send_initiate_claim_an_employee_email.html'
        context = {
            "heading": email_dto.heading,
            "emp_name": email_dto.emp_name,
            "initiator_name": email_dto.initiator_name,
            "emp_designation": email_dto.emp_designation,
            "emp_email": email_dto.emp_email,
            "last_date_of_declaration": email_dto.last_date_of_declaration,
        }
        html_email = loader.render_to_string(email_template, context)
        return html_email

    def send_finance_mail(self, message, emp_name, to_email, subject, cc_addresses=[]):
        #TODO - Confirmation   ccaddress - team@mydomain.com
        mail_dto = {}
        mail_dto["subject"] = "{0} ".format(subject)
        mail_dto["from_address"] = settings.EMAIL_ADDRESS['do_not_reply']['name']
        mail_dto["body"] = message
        mail_dto["to_addresses"] = to_email
        # mail_dto["cc_addresses"] = cc_addresses
        mail_dto["bcc_address"] = cc_addresses

        mail_dto["smtp_username"] = settings.EMAIL_ADDRESS['do_not_reply']['mailID']
        mail_dto["smtp_password"] = settings.EMAIL_ADDRESS['do_not_reply']['password']
        # un comment to send mail TODO
        send_email_notification.apply_async([mail_dto, 1], queue=settings.CELERY_QUEUE['mail_sender'])

