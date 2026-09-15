from datetime import date, datetime, timedelta
from types import SimpleNamespace

from celery import shared_task as task
from django.conf import settings

from django.db import  transaction

from pTracker.celery import app
from pTracker.common.utility import Utility

from pTracker.dataaccess.ptracker_access.user_da import UserDA
from pTracker.dataaccess.ptracker_access.appraisal_da import AppraisalDA
from pTracker.api.appraisal.appraisal_notification_biz import AppraisalNotificationBL

import uuid
import json

from pTracker.dataaccess.ptracker_access.appraisal_models import AppraisalLog


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




@app.task(bind=True)
def generate_appraisal_forms(self, user_id, emp_data, overwrite, year, batch_id):
    try:
        AppraisalDA().delete_all_appraisal_celery_job_log()
        email_content_dto = new_dto()
        emp_dict = get_active_emp_dict()
        profile_dict = get_user_profile_dict()
        job_title_dict = get_job_title_dict()
        appraising_period = AppraisalDA().get_appraisal_period_by_date(year)
        all_existing_appraisals = AppraisalDA().get_appraisal_entry_by_period(appraising_period.period_id)
        users_with_group_id = UserDA().get_users_with_group_id()
        user = emp_dict.get(user_id, None)
        current_user_name = ''
        if user:
            current_user_name = user.first_name + ' ' + user.last_name
        today = datetime.now()
        appraisal_log = {}
        job_status = []
        action = settings.APPRAISAL_LOG[1]\
            .format(current_user_name,datetime.now().strftime("%d/%m/%Y %I:%M %p"))

        for emp in emp_data:
            emp_id = emp.get('emp_id')
            employee = emp_dict.get(emp_id, None)
            if not employee:
                continue

            employee_name = employee.first_name + ' ' + employee.last_name
            emp_job_status = {'error': ''}
            emp_job_status['emp_code'] = employee.username
            emp_job_status['emp_name'] = employee_name

            try:
                appraisal_data = {}
                appraiser_id = emp.get('appriser_id')
                reviewer_id = emp.get('reviewer_id')
                employee_expiry_date = emp.get('employee_expiry_date')
                appraiser_expiry_date = emp.get('appraiser_expiry_date')
                reviewer_expiry_date = emp.get('reviewer_expiry_date')
                # batch_id =  emp.get('batch_id')
                # print(batch_id,"...................")

                job_title_id = 0
                company_id = 0
                user_profile = profile_dict.get(emp_id, None)
                if not user_profile:
                    emp_job_status['status'] = False
                    emp_job_status['error'] = "User profile for employee is missing"
                    job_status.append(emp_job_status)
                    continue

                # try:
                #     appraiser_profile = all_active_user_profiles.get(user_id=appraiser_id)
                #     appraiser_job_title = all_job_titles.get(id=appraiser_profile.job_title).job_title
                # except:
                #     appraiser_profile = None
                #     appraiser_job_title = None

                # try:
                #     reviewer_profile = all_active_user_profiles.get(user_id=reviewer_id)
                #     reviewer_job_title = all_job_titles.get(id=reviewer_profile.job_title).job_title
                # except:
                #     reviewer_profile = None
                #     reviewer_job_title = None

                #if user_profile:
                job_title_id = user_profile.job_title
                company_id = user_profile.company_id
                job_title = job_title_dict.get(int(job_title_id), '')

                appraiser_name = ''
                appraiser_email = ''
                appraiser_job_title = ''
                appraiser = emp_dict.get(appraiser_id, None)
                if appraiser:
                    appraiser_name = appraiser.first_name + ' ' + appraiser.last_name
                    appraiser_email = appraiser.email
                    appraiser_id = appraiser.id

                    appraiser_profile = profile_dict.get(appraiser_id, None)
                    if appraiser_profile:
                        appraiser_job_title = job_title_dict.get(int(appraiser_profile.job_title), '')



                reviewer_name = ''
                reviewer_email = ''
                reviewer_job_title = ''
                if reviewer_id != 0:
                    reviewer = emp_dict.get(reviewer_id, None)
                    if reviewer:
                        reviewer_name = reviewer.first_name + ' ' + reviewer.last_name
                        reviewer_email = reviewer.email
                        reviewer_profile = profile_dict.get(reviewer_id, None)
                        if reviewer_profile:
                            reviewer_job_title = job_title_dict.get(int(reviewer_profile.job_title), '')

                try:
                    existing_appraisal = all_existing_appraisals.get(employee_id=emp_id)
                except:
                    existing_appraisal = None

                with transaction.atomic():
                    if existing_appraisal:
                        if overwrite:
                            AppraisalDA().delete_appraisal_form_by_id(existing_appraisal.appraisal_id)
                        else:
                            continue

                    role_id = users_with_group_id.get(emp_id, 5)
                    if role_id == 5:
                        if emp_id in settings.SEO_EMPLOYESS:
                            form_data = open(settings.JSON_TEMPLATE_PATH + 'seo_employee_appraisal_form.json')

                        elif emp_id in settings.PROCESS_ASSOCIATE_EMPLOYEES:
                            form_data = open(settings.JSON_TEMPLATE_PATH + 'process_associate_appraisal_form.json')

                        else:
                            form_data = open(settings.JSON_TEMPLATE_PATH + 'employee_appraisal_form_v2.json')
                    else:
                        form_data = open(settings.JSON_TEMPLATE_PATH + 'lead_appraisal_form.json')
                    data = json.load(form_data)

                    data['employee']['name_of_the_employee']['value'] = employee_name
                    data['employee']['employee_id'] = emp_id
                    data['employee']['designation']['value'] = job_title
                    data['employee']['date_of_joining']['value'] = datetime.strftime(employee.date_joined, '%d/%m/%Y')
                    data['employee']['employee_code'] = str(employee.username)

                    data['employee']['total_years_in_Service']['value'] = get_years_service(employee.date_joined)
                    data['employee']['period_assessment']['value'] = appraising_period.period_id
                    data['appraiser']['name_of_the_employee'] = appraiser_name
                    data['appraiser']['employee_id'] = appraiser_id
                    data['reviewer']['name_of_the_employee'] = reviewer_name
                    data['reviewer']['employee_id'] = reviewer_id

                    data['self_assessment_form']['appraisee_details']['value'] = employee_name
                    data['appraiser_details']['employee_id'] = appraiser_id
                    data['appraiser_details']['section_header']['value'] = appraiser_name

                    #data['self_assessment_form']['appraisee_details']['value'] = emp.first_name + ''+emp.last_name
                    data['self_assessment_form']['designation']['value'] = job_title
                    #data['appraiser_details']['employee_id'] = appraiser.id
                    data['appraiser_details']['section_header']['value'] = appraiser.first_name + ' ' + appraiser.last_name
                    data['appraiser_details']['designation']['value'] = appraiser_job_title
                    data['reviewer_details']['employee_id'] = reviewer_id
                    data['reviewer_details']['section_header']['value'] = reviewer_name
                    data['reviewer_details']['designation']['value'] = reviewer_job_title

                    appraisal_data['period_id'] = appraising_period.period_id
                    appraisal_data['employee_id'] = emp_id
                    appraisal_data['appraisal_token'] = str(uuid.uuid4())
                    appraisal_data['appraisal_data'] = json.dumps(data)
                    appraisal_data['status'] = settings.APPRAISAL_STATUS['APPRAISAL_ISSUED']
                    appraisal_data['organization_id'] = user_profile.company_id
                    appraisal_data['appraiser_id'] = appraiser_id
                    appraisal_data['reviewer_id'] = reviewer_id
                    appraisal_data['appraiser_expiry_date'] = appraiser_expiry_date
                    appraisal_data['reviewer_expiry_date'] = reviewer_expiry_date
                    appraisal_data['employee_expiry_date'] = employee_expiry_date
                    appraisal_data['appraiser_submitted'] = 0
                    appraisal_data['reviewer_submitted'] = 0
                    appraisal_data['employee_submitted'] = 0
                    appraisal_data['batch_id'] = batch_id

                    appraisal = AppraisalDA().create_appraisal_form(appraisal_data)
                    log_data = {
                        'appraisal_id': appraisal.appraisal_id,
                        'action': action,
                        'employee_id': user.id}
                    AppraisalDA().create_appraisal_log(log_data)
                    emp_job_status['status'] = True
                    appraisal_year = str(appraising_period.period_start_date.year) + '-'+str(appraising_period.period_end_date.year)

                    email_content_dto.heading = "Annual Performance Appraisal " + appraisal_year
                    email_content_dto.emp_name = employee_name
                    email_content_dto.date = today
                    email_content_dto.link = f"{settings.BASE_URL}assessment/model/{appraisal_data['appraisal_token']}"
                    email_content_dto.hr_name = current_user_name
                    email_content_dto.year = appraisal_year
                    email_content_dto.appraiser_expiry_date = datetime.strptime(appraiser_expiry_date, '%Y-%m-%d').strftime("%d/%m/%Y")
                    email_content_dto.reviewer_expiry_date = datetime.strptime(reviewer_expiry_date, '%Y-%m-%d').strftime("%d/%m/%Y")
                    email_content_dto.employee_expiry_date = datetime.strptime(employee_expiry_date, '%Y-%m-%d').strftime("%d/%m/%Y")

                    to_email = employee.email
                    # cc_addresses = [appraiser.email, reviewer_email]

                    email_msg = AppraisalNotificationBL().generate_appraisal_issue_email_message(email_content_dto)
                    AppraisalNotificationBL().send_appraisal_notification(email_msg, employee_name, to_email, 'Annual Performance Appraisal ' + appraisal_year)
            except Exception as err:
                emp_job_status['status'] = False
            job_status.append(emp_job_status)
        appraisal_job_status = {"job_status": job_status}
        celery_job_data = {"message": json.dumps(appraisal_job_status)}

        AppraisalDA().create_appraisal_celery_job(celery_job_data)

    except Exception as e:
        msg = "Error in the job generate_appraisal_forms, Error is : {0} ".format(str(e))
        Utility().log(msg)
