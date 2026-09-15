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


    def generate_email_messages(self, email_dto):
        email_template = 'career_opening.html'
        context = {
            "heading": email_dto.heading,
            "postion_name": email_dto.postion_name,
            "ref_no": email_dto.ref_no,
            "comment": email_dto.comment,
            "emp_name": email_dto.emp_name,
            "emp_designation": email_dto.emp_designation,
            "emp_email": email_dto.emp_email
        }
        html_email = loader.render_to_string(email_template, context)
        return html_email

    def send_opening_notification(self, message, emp_name, to_email, subject, cc_addresses=[]):
        #TODO - Confirmation   ccaddress - team@mydomain.com
        mail_dto = {}
        mail_dto["subject"] = "{0} ".format(subject)
        mail_dto["from_address"] = settings.EMAIL_ADDRESS['do_not_reply']['name']
        mail_dto["body"] = message
        mail_dto["to_addresses"] = [to_email]
        # mail_dto["cc_addresses"] = cc_addresses
        mail_dto["bcc_address"] = cc_addresses

        mail_dto["smtp_username"] = settings.EMAIL_ADDRESS['do_not_reply']['mailID']
        mail_dto["smtp_password"] = settings.EMAIL_ADDRESS['do_not_reply']['password']
        # un comment to send mail TODO
        send_email_notification.apply_async([mail_dto, 1], queue=settings.CELERY_QUEUE['mail_sender'])


    def generate_career_open_email_message(self, email_dict):
        email_template = 'career_open_email.html'
        context = {
            "heading": email_dict['heading'],
            "position_name": email_dict['position_name'],
            "ref_no": email_dict['ref_no'],
            "required_experience" : email_dict['required_experience'],
            "required_qualification" : email_dict['required_qualification'],
            "soft_skills" : email_dict['soft_skills'],
            "technical_skills" : email_dict['technical_skills'],
            "number_of_opening" : email_dict['number_of_opening'],
            "emp_name": email_dict['emp_name'],
            "number_of_opening":email_dict['number_of_opening'],
            "empDesignation":email_dict['emp_designation'],
            "empEmail":email_dict['empEmail'],
            "years_of_exp_required" : email_dict['years_of_exp_required'],
            "jobDescription" : email_dict['jobDescription']
        }
        html_email = loader.render_to_string(email_template, context)
        return html_email

    def send_mail(self, user, data):
        response = {'error' : '', 'status' : 200}
        candidate_name = ''
        try:
            user_id = user.id

            subject = data.get('subject')
            # content = data.get('content')
            to_mail = data.get('toMail')
            interview_id = data.get('interviewID')
            behalfOf = data.get('behalfOf')
            if behalfOf and behalfOf not in ('', '0', 0, None):
                user_id = int(behalfOf)

            user = UserDA().get_user_by_id(user_id)
            interview = InterviewDA().get_interview(interview_id)
            if interview:
                candidate_id = interview.candidate_id
                candidate = InterviewDA().get_candidate_by_id(candidate_id)
                if candidate:
                    candidate_name = (candidate.first_name).strip().upper()+ ' ' + (candidate.last_name).strip().upper()


            email_dto = new_dto()
            date_time = interview.date_and_time.strftime('at %I:%M %p on %d/%m/%Y')
            email_dto.subject = f"Interview Meeting Link for {candidate_name} {date_time}"
            email_dto.company_name = settings.COMPANY_NAME_FOR_INTERVIEW_MAIL
            email_dto.designation = self.__get_user_job_title(user_id)
            email_dto.content = subject
            email_dto.heading = f"Interview Meeting Link for {candidate_name} {date_time}"
            email_dto.candidate_name = candidate_name
            emp_name = user.first_name+ ' ' + user.last_name
            email_dto.emp_name = emp_name
            email_dto.emp_email = user.email
            email_dto.date_time = date_time
            email_msg = self.generate_email_message(email_dto)
            cc_adress = [settings.INTERVIEW_DEFAULT_MAIL]

            notify = str(interview.interviewer).split(',')
            interviewerLst = []
            for eachRow in notify:
                interviewerLst.append(int(eachRow))
            interviewerCC =  UserDA().get_user_name_by_id(interviewerLst)
            for each in interviewerCC:
                cc_adress.append(each.email)
            if user.email not in cc_adress:
                cc_adress.append(user.email)
            self.send_opening_notification(email_msg,emp_name,to_mail,email_dto.subject,cc_adress)
            response['success'] = "Mail send successfully ."

            is_interview_link_saved = InterviewDA().update_interview_link(interview_id, subject)
            if not is_interview_link_saved:
                response['error'] = 'Interview Link updation failed'
                return response
            
        except Exception as error:
            response["error"] = settings.ERROR_MSG['application_error']\
                .format(error, self.__log.error(self.__exception.get_exception()))
            response['status'] = 499
        return response

    def generate_email_message(self, email_dto):
        email_template = 'interview_meeting_link_mail.html'
        context = {
            "heading": email_dto.heading,
            "company_name": email_dto.company_name,
            "emp_name": email_dto.emp_name,
            "subject": email_dto.subject,
            "candidate_name": email_dto.candidate_name,
            "emp_email": email_dto.emp_email,
            "designation" : email_dto.designation,
            "content" : email_dto.content,
            "date_time": email_dto.date_time
        }
        html_email = loader.render_to_string(email_template, context)
        return html_email

    def __get_user_job_title(self, user_id):
        user_profile = UserDA().get_user_profile_by_id(user_id)
        job_title = UserDA().get_job_title_by_id(user_profile.job_title)
        job_title = job_title.job_title
        return job_title


