from datetime import date, datetime, timedelta
from types import SimpleNamespace

from celery import shared_task as task
from django.conf import settings

from django.template import loader

from pTracker.celery import app
from pTracker.common.utility import Utility

from pTracker.dataaccess.ptracker_access.user_da import UserDA

from pTracker.cronjobs.email_sender import send_email_notification


@app.task(bind=True)
def collect_missing_details(self):
    try:
        subject = "Urgent: Please Update Employee Information"
        email_dto = new_dto()
        email_dto.hr_name = settings.HR_NAME
        email_dto.heading = subject
        email_dto.expiry_date = (datetime.now() + timedelta(days=7)).strftime('%d/%m/%Y')
        users_dict = get_active_emp_dict()
        user_profiles_dict = get_user_profile_dict()

        for user_id, each_user in users_dict.items():
            if str(each_user.username) in ('200', '201'):
                continue
            try:
                emp_name = f'{each_user.first_name} {each_user.last_name}'
                profile = user_profiles_dict.get(user_id, {})
                email_dto.emp_name = emp_name
                email_dto.link = f"{settings.BASE_URL}user/edit-user-v3/{profile.secret_key}"
            except Exception as e:
                continue
            email_message = missing_details_email_message(email_dto)
            send_notification(email_message, [each_user.email], subject)
    except Exception as e:
        msg = "Error in the job collect_missing_details, Error is : {0} ".format(str(e))
        Utility().log(msg)

def new_dto():
    dto = SimpleNamespace()
    return dto

def get_active_emp_dict():
    emp_dict = {}
    users = UserDA().get_all_active_users()
    for user in users:
        emp_dict[user.id] = user
    return emp_dict

def get_user_profile_dict():
    profile_dict = {}
    profiles = UserDA().get_all_user_profiles()
    for profile in profiles:
        profile_dict[profile.user_id] = profile
    return profile_dict

def get_job_title_dict():
    job_title_dict = {}
    job_titles = UserDA().get_all_job_titles()
    for job_title in job_titles:
        job_title_dict[job_title.id] = job_title.job_title
    return job_title_dict

def get_years_service(date_joined):
    total_years_in_service = ''
    try:
        months_of_service = datetime.now().month - date_joined.month + 12 * \
            (datetime.now().year - date_joined.year)
        years, months = divmod(months_of_service, 12)
        total_years_in_service = str(years) +' Years ' + str(months) +' Months'
    except:
        total_years_in_service = ''
    return total_years_in_service

def missing_details_email_message(email_dto):
    email_template = 'missing_details.html'
    context = {
        "heading": email_dto.heading,
        "emp_name": email_dto.emp_name,
        "link": email_dto.link,
        "hr_name": email_dto.hr_name,
        'expiry_date': email_dto.expiry_date
    }
    html_email = loader.render_to_string(email_template, context)
    return html_email

def send_notification(message, to_email, subject, cc_addresses=[]):
    mail_dto = {}
    mail_dto["subject"] = subject
    mail_dto["from_address"] = settings.EMAIL_ADDRESS['do_not_reply']['name']
    mail_dto["body"] = message
    mail_dto["to_addresses"] = to_email
    mail_dto["cc_addresses"] = cc_addresses
    mail_dto["smtp_username"] = settings.EMAIL_ADDRESS['do_not_reply']['mailID']
    mail_dto["smtp_password"] = settings.EMAIL_ADDRESS['do_not_reply']['password']
    send_email_notification.apply_async(
        [mail_dto, 1], queue=settings.CELERY_QUEUE['mail_sender'])
