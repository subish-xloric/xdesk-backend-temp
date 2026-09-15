import os
from  datetime import datetime, date, timedelta
from celery import shared_task as task
import math
import random
from PIL import Image

from io import BytesIO
from pTracker.celery import app

from django.conf import settings
from types import SimpleNamespace
from django.template import loader
from django.template.loader import get_template
# from pTracker.attendance.daily_work_hours_report import DailyWorkHoursReportBL
# from pTracker.attendance.daily_att_report import DailyAttendanceReportBL
from pTracker.common.utility import Utility
from pTracker.user_management.employee import Employee
from pTracker.notification_center.email_engine import Email
from pTracker.dataaccess.ptracker_access.user_da import UserDA
from pTracker.common.exception_handler import ExceptionHandler
from pTracker.common.logs import Logs

from pTracker.dataaccess.ptracker_access.holiday_da import HolidayDA



def new_dto():
    dto = SimpleNamespace()
    return dto



def generate_email_message( report_name):
    str_html = """
    <p>Hello,</p>
    <p>Please find attached {0}</p>
    <br>
    <p>Regards,</p>
    <p>Team EasyDesk<br>
    </p><br>""".format(report_name)
    return str_html


@app.task(bind=True)
def send_daily_work_hours_report(self, file_path, str_date):

    #file_path = settings.UPLOAD_PATH['DAILY_WORK_HOUR_REPORT'] + file_name
    f = open(file_path, "rb")
    content = f.read()
    f.close()
    try:
        file_name = file_path.split("/")[-1]

        to_emails = Employee().get_all_email_recipient('daily_work_hour')
        subject = "Work Hour Report for {0}.".format(str_date)

        for to_email in to_emails:
            mail_dto = new_dto()
            mail_dto.subject = subject
            mail_dto.from_address = settings.EMAIL_ADDRESS['donotreply']['name']
            mail_dto.body = generate_email_message(subject)
            mail_dto.file_content = content
            mail_dto.file_name = "work_hours_report_" + file_name
            mail_dto.to_addresses = [to_email]
            mail_dto.smtp_username = settings.EMAIL_ADDRESS['donotreply']['mailID']
            mail_dto.smtp_password = settings.EMAIL_ADDRESS['donotreply']['password']
            Email().send_attachment(mail_dto)
            del mail_dto

    except Exception as e:
        msg = "Error in the job send_daily_work_hours_report, Error is : {0} ".format(str(e))
        Utility().log(msg)

@app.task(bind=True)
def send_daily_att_report(self, file_path, str_date):
    f = open(file_path, "rb")
    content = f.read()
    f.close()
    try:
        file_name = file_path.split("/")[-1]
        to_emails = Employee().get_att_email_recipient('daily_work_hour')
        if file_name.startswith('DM'):
            subject = "Digitalmesh Attendance Report for {0}.".format(str_date)
        else:
            subject = "EM Softech Attendance Report for {0}.".format(str_date)

        for to_email in to_emails:
            mail_dto = new_dto()
            mail_dto.subject = subject
            mail_dto.from_address = settings.EMAIL_ADDRESS['donotreply']['name']
            mail_dto.body = generate_email_message(subject)
            mail_dto.file_content = content
            mail_dto.file_name = "Attendance_report_" + file_name
            mail_dto.to_addresses = [to_email]
            mail_dto.smtp_username = settings.EMAIL_ADDRESS['donotreply']['mailID']
            mail_dto.smtp_password = settings.EMAIL_ADDRESS['donotreply']['password']
            Email().send_attachment(mail_dto)
            del mail_dto

    except Exception as e:
        msg = "Error in the job send_daily_att_report, Error is : {0} ".format(str(e))
        Utility().log(msg)

@app.task(bind=True)
def send_daily_punch_in_report(self, file_path, str_date):
    f = open(file_path, "rb")
    content = f.read()
    f.close()
    try:
        file_name = file_path.split("/")[-1]
        to_emails = Employee().get_all_email_recipient('punch_in')
        subject = "Daily Punch In Report for {0}.".format(str_date)

        for to_email in to_emails:
            mail_dto = new_dto()
            mail_dto.subject = subject
            mail_dto.from_address = settings.EMAIL_ADDRESS['donotreply']['name']
            mail_dto.body = generate_email_message(subject)
            mail_dto.file_content = content
            mail_dto.file_name = "punch_in_report_" + file_name
            mail_dto.to_addresses = [to_email]
            mail_dto.smtp_username = settings.EMAIL_ADDRESS['donotreply']['mailID']
            mail_dto.smtp_password = settings.EMAIL_ADDRESS['donotreply']['password']
            Email().send_attachment(mail_dto)
            del mail_dto

    except Exception as e:
        msg = "Error in the job send_daily_att_report, Error is : {0} ".format(str(e))
        Utility().log(msg)


@app.task(bind=True)
def send_weekly_report(self, file_path, str_date):

    f = open(file_path, "rb")
    content = f.read()
    f.close()
    try:
        file_name = file_path.split("/")[-1]

        to_emails = Employee().get_all_email_recipient('daily_work_hour')
        subject = "Weekly Summary Report : {0}  ".format(str_date)

        for to_email in to_emails:
            mail_dto = new_dto()
            mail_dto.subject = subject
            mail_dto.from_address = settings.EMAIL_ADDRESS['donotreply']['name']
            mail_dto.body = generate_email_message(subject)
            mail_dto.file_content = content
            mail_dto.file_name = "weekly_summary_report_" + file_name
            mail_dto.to_addresses = [to_email]
            mail_dto.smtp_username = settings.EMAIL_ADDRESS['donotreply']['mailID']
            mail_dto.smtp_password = settings.EMAIL_ADDRESS['donotreply']['password']
            Email().send_attachment(mail_dto)
            del mail_dto

    except Exception as e:
        msg = "Error in the job send_weekly_report, Error is : {0} ".format(str(e))
        Utility().log(msg)

@app.task(bind=True)
def send_monthly_att_report(self, file_path, str_date, company_name):

    f = open(file_path, "rb")
    content = f.read()
    f.close()
    try:
        file_name = file_path.split("/")[-1]

        to_emails = Employee().get_att_email_recipient('daily_work_hour')
        subject = "{1} Monthly Attendance Report, {0}  ".format(str_date, company_name)

        for to_email in to_emails:
            mail_dto = new_dto()
            mail_dto.subject = subject
            mail_dto.from_address = settings.EMAIL_ADDRESS['donotreply']['name']
            mail_dto.body = generate_email_message(subject)
            mail_dto.file_content = content
            mail_dto.file_name = file_name
            mail_dto.to_addresses = [to_email]
            mail_dto.smtp_username = settings.EMAIL_ADDRESS['donotreply']['mailID']
            mail_dto.smtp_password = settings.EMAIL_ADDRESS['donotreply']['password']
            Email().send_attachment(mail_dto)
            del mail_dto

    except Exception as e:
        msg = "Error in the job send_monthly_att_report, Error is : {0} ".format(str(e))
        Utility().log(msg)

@app.task(bind=True)
def send_work_anniversary_email(self):
    image_list = []
    try:
        current_date = date.today()
        work_anniversaries = UserDA().get_current_day_work_anniversary(current_date)
        if work_anniversaries:
            for row in work_anniversaries:
                if row.date_joined.year == current_date.year:
                    continue
                organization = UserDA().get_user_organization(row.id)
                logo = Utility().get_organization_logo_as_image(organization)

                email_template = 'work_anniversary_template.html'
                years = current_date.year - row.date_joined.year
                context = {"username": row.first_name + ' ' + row.last_name,
                           "years": years, "organization": organization}
                html_email = loader.render_to_string(email_template, context)

                for i in range(1, settings.WORK_ANNIVERSARY_IMAGE):
                    image_list.append(i)
                image_id = random.choice(image_list)
                image_list.remove(image_id)

                wishes_image = BytesIO()
                wish_image = Image.open(os.path.join(
                    settings.MEDIA_ROOT, f'wrk_anvsry_images/{image_id}.jpeg'))
                wish_image.save(wishes_image, format='jpeg')

                mail_dto = new_dto()
                mail_dto.subject = 'Happy Work Anniversary'
                mail_dto.from_address = settings.EMAIL_ADDRESS['donotreply']['name']
                mail_dto.body = html_email
                mail_dto.to_addresses = [row.email]
                mail_dto.smtp_username = settings.EMAIL_ADDRESS['donotreply']['mailID']
                mail_dto.smtp_password = settings.EMAIL_ADDRESS['donotreply']['password']
                mail_dto.image = wishes_image.getvalue()
                mail_dto.logo = logo.getvalue()
                Email().send_html_mail_v2(mail_dto)
                del mail_dto
    except Exception as error:
        Logs().error(ExceptionHandler().get_exception())


@app.task(bind=True)
def send_email_notification(self, mail_dto, is_convertion_need):
    try:
        if is_convertion_need:
            mail_host = mail_dto.get('mail_host', 'default')
        else:
            try:
                mail_host = mail_dto.mail_host
            except:
                mail_host = 'default'

        Email(mail_host=mail_host).send_html_mail_v1(mail_dto, is_convertion_need)
    except Exception as e:
        msg = "Error in the job send_email_notification, Error is : {0} ".format(
            str(e))
        Utility().log(msg)
        msg = ExceptionHandler().get_exception()
        Logs().error(msg)


@app.task(bind=True)
def send_birthday_wish_email(self):
    try:
        image_list = []
        used_image = []
        current_date = date.today()
        birthdays, err = UserDA().get_current_date_birthdays(current_date)
        if birthdays:
            for i in range(1, settings.BIRTHDAY_WISH_IMAGE):
                image_list.append(i)
            for row in birthdays:

                image_id = random.choice(image_list)
                image_list.remove(image_id)
                employe_name = str(row[1]) + ' ' + str(row[2])
                organization_id = row[4]
                logo_image = Utility().get_organization_logo_as_image(organization_id)

                wishes_image = BytesIO()
                wish_image = Image.open(os.path.join(
                    settings.MEDIA_ROOT, f'bday_images/{image_id}.jpeg'))
                wish_image.save(wishes_image, format='jpeg')
                context = {'employe_name': employe_name,
                           'organization': organization_id}

                message = get_template('birthday_wishes.html').render(context)
                mail_dto = new_dto()
                mail_dto.subject = "HAPPY BIRTHDAY - " + employe_name
                mail_dto.from_address = settings.EMAIL_ADDRESS['do_not_reply']['name']
                mail_dto.body = message
                mail_dto.to_addresses = [settings.HR_EMAIL]
                mail_dto.cc_addresses = []
                mail_dto.body = message
                mail_dto.smtp_username = settings.EMAIL_ADDRESS['do_not_reply']['mailID']
                mail_dto.smtp_password = settings.EMAIL_ADDRESS['do_not_reply']['password']
                mail_dto.image = wishes_image.getvalue()
                mail_dto.logo = logo_image.getvalue()
                Email().send_html_mail_v2(mail_dto)
            return (message)
    except Exception as error:
        Logs().error(ExceptionHandler().get_exception())


# @app.task(bind=True)
# def send_request_emails( message, emp_name, to_email,subject):
#     try:
#         mail_dto = new_dto()
#         mail_dto.subject = "DM DESK: {0} Request By {1} !!!".format(subject,emp_name)
#         mail_dto.from_address = settings.EMAIL_ADDRESS['do_not_reply']['name']
#         mail_dto.body = message
#         mail_dto.to_addresses = [to_email]
#         mail_dto.smtp_username = settings.EMAIL_ADDRESS['do_not_reply']['mailID']
#         mail_dto.smtp_password = settings.EMAIL_ADDRESS['do_not_reply']['password']
#         Email().send_html_mail(mail_dto)
#     except Exception as err:
#       print(err)
