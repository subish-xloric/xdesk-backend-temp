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
        
        
    def generate_ticket_create_email_messages(self, email_dto):
        email_template = 'ticket_create_message_email.html'
        context = {
            "heading": email_dto.heading,
            # "ticket_id": email_dto.ticket_id,
            "emp_name": email_dto.emp_name,
            "assigned_to": email_dto.assigned_to,
            "priority": email_dto.priority,
            "subject": email_dto.subject,
            "created_by": email_dto.created_by,
            "description": email_dto.description,
            "project_name": email_dto.project_name,
            "deadline": email_dto.deadline,
            "category": email_dto.category,
            "ticket_type": email_dto.ticket_type,
        }
        html_email = loader.render_to_string(email_template, context)
        return html_email
    
    def generate_ticket_update_email_messages(self, email_dto):
        email_template = 'ticket_update_email.html'
        context = {
            "ticket_id": email_dto.ticket_id,
            "heading": email_dto.heading,
            "emp_name": email_dto.emp_name,
            "assigned_to": email_dto.assigned_to,
            "priority": email_dto.priority,
            "subject": email_dto.subject,
            "created_by": email_dto.created_by,
            "description": email_dto.description,
            "ticket_changes": email_dto.ticket_changes,
            "project_name": email_dto.project_name,
            "deadline": email_dto.deadline,
            "category": email_dto.category,
            "ticket_type": email_dto.ticket_type,
            # "image_url" : email_dto.image_url
        }
        html_email = loader.render_to_string(email_template, context)
        return html_email
    

    def generate_ticket_repo_email_messages(self, email_dto):
        email_template = 'ticket_repo_mail.html'
        context = {
            "heading": email_dto.heading,
            "ticket_id": email_dto.ticket_id,
            "project_name": email_dto.project_name,
            "message": email_dto.message if email_dto.message else None,
            "error": email_dto.error if email_dto.error else None,
        }

        html_email = loader.render_to_string(email_template, context)
        return html_email


    def send_ticket_mail(self, message, emp_name, to_email, subject, cc_addresses=[]):
        #TODO - Confirmation   ccaddress - team@digitalmesh.com
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

