from hashlib import new
import json
import time
from types import SimpleNamespace
from datetime import date, datetime
import io
import os
import zipfile

from django.conf import settings
from django.db import  transaction
from django.http import HttpResponse

from celery.result import AsyncResult
from cryptography.fernet import Fernet

from pTracker.common.logs import Logs
from pTracker.common.utility import Utility
from pTracker.common.exception_handler import ExceptionHandler
from pTracker.common.file_manager import FileManager
from pTracker.dataaccess.ptracker_access.user_da import UserDA
from pTracker.dataaccess.ptracker_access.appraisal_da import AppraisalDA
from pTracker.cronjobs.generate_appraisal_form import generate_appraisal_forms
from pTracker.api.appraisal.appraisal_notification_biz import AppraisalNotificationBL
from pTracker.dataaccess.ptracker_access.appraisal_models import AppraisalBatches
#from pTracker.dataaccess.ptracker_access.appraisal_da import AppraisalDA


def new_dto():
    dto = SimpleNamespace()
    return dto


class AppraisalBL():
    def __init__(self):
        self.__log = Logs()
        self.__exception = ExceptionHandler()
        self.__utility = Utility()
        self.__file_manager = FileManager()

    def __get_eligible_doj(self, doj):
        try:
            return datetime.strptime(doj, "%Y-%m-%d")
        except:
            return None

    def __get_org_unit_id(self, org_id):
        try:
            return int(org_id)
        except:
            return None

    def __user_profile_dict(self):
        profile_dict = {}
        profiles = UserDA().get_all_user_profiles()
        for profile in profiles:
            profile_dict[profile.user_id] = profile #int(profile.company_id)
        return profile_dict

    def __get_lead_dict(self):
        lead_dict = {}
        all_emp_lead_mapping = UserDA().get_all_employee_lead_mapping()
        if all_emp_lead_mapping:
            for emp_lead in all_emp_lead_mapping:
                lead_dict[emp_lead.emp_id] = emp_lead.lead_id
        return lead_dict

    def __get_years_of_experience(self, date_joined):
        try:
            months_of_service = datetime.now().month\
                - date_joined.month + 12 * \
                    (datetime.now().year - date_joined.year)
            years, months = divmod(months_of_service, 12)
            return str(years) + ' Years ' + str(months) + ' Months'
        except:
            return "--"

    def __get_active_emp_dict(self):
        emp_dict = {}
        users = UserDA().get_all_active_users()
        for user in users:
            emp_dict[user.id] = user
        return emp_dict

    def __get_all_emp_dict(self):
        emp_dict = {}
        users = UserDA().get_all_users()
        for user in users:
            emp_dict[user.id] = user
        return emp_dict

    def __get_clean_integer(self, app_year):
        try:
            return int(app_year)
        except:
            return None

    def __get_emp_name(self, emp):
        if emp:
            return emp.first_name + ' ' + emp.last_name
        else:
            return ''

    def get_all_eligible_employees(self, user_id, year, org_id, doj):
        result = {
            "status": 200,
            "error": '',
            "data": [],
            "appraisers": [],
            "reviewers": []
        }
        result_list = []
        try:
            role_id, role_name = UserDA().get_user_role_by_id(user_id)
            if role_id not in (2, '2',):
                result['error'] = settings.ERROR_MSG['access_denied']
                result['status'] = 403
                return result
            eligible_doj = self.__get_eligible_doj(doj)
            if not eligible_doj:
                result['error'] = "Invalied Appraisal Eligibility DOJ."
                result['status'] = 499
                return result
            org_id = self.__get_org_unit_id(org_id)
            if not org_id:
                result['error'] = "Invalied Organization."
                result['status'] = 499
                return result

            profile_dict =  self.__user_profile_dict()
            lead_dict = self.__get_lead_dict()
            emp_dict = self.__get_active_emp_dict()
            appraisal_excluded_employees = settings.APPRAISAL_EXCLUDED_EMPLOYESS
            eligible_employees = UserDA().get_all_employees_by_doj(eligible_doj)
            eligible_employees = eligible_employees.exclude(id__in=appraisal_excluded_employees)
            # profile = profile_dict.get(employee.id, 0)
            # company_id = 0
            # if profile:
            #     company_id = int(profile.company_id)

            for employee in eligible_employees:
                profile = profile_dict.get(employee.id, 0)
                company_id = 0
                if profile:
                    company_id = int(profile.company_id)

                if org_id != company_id:
                    continue

                temp = {
                    'appraiser_id': 0,
                    'appraiser_name': '--',
                    'reviewer_id': 0,
                    'reviewer_name': '--'
                }
                temp['emp_code'] = employee.username
                temp['emp_id'] = employee.id
                temp['emp_name'] = employee.first_name + ' ' + employee.last_name
                lead_id = lead_dict.get(employee.id, 0)
                lead = emp_dict.get(lead_id, None)
                if lead:
                    temp['appraiser_id'] = lead.id
                    temp['appraiser_name'] = lead.first_name + ' ' + lead.last_name
                reviewer_id = lead_dict.get(lead_id, 0)
                reviewer = emp_dict.get(reviewer_id, None)
                if reviewer:
                    temp['reviewer_id'] = reviewer.id
                    temp['reviewer_name'] = reviewer.first_name + ' ' + reviewer.last_name
                temp['years_of_service'] = self.__get_years_of_experience(employee.date_joined)
                result_list.append(temp)
                del temp

            result['data'] = result_list
            all_leads, err = UserDA().get_all_leads()
            for each in all_leads:
                temp = {}
                temp['appraiser_name'] = each[0] + ' ' + each[1]
                temp['appraiser_id'] = each[2]
                result['appraisers'].append(temp)

            all_managers, err = UserDA().get_all_managers()
            for each in all_managers:
                temp = {}
                temp['reviewer_name'] = each[0] + ' ' + each[1]
                temp['reviewer_id'] = each[2]
                result['reviewers'].append(temp)
                # temp = {}
                # temp['appraiser_name'] = each[0] + ' '+each[1]
                # temp['appraiser_id'] = each[2]
                # result['appraisers'].append(temp)

        except Exception as err:
            result["error"] = settings.ERROR_MSG['application_error']\
                .format(err, self.__log.error(self.__exception.get_exception()))
            result['status'] = 499
        return result

    def initiate_appraisal(self, user_id, data):
        result = {
            "status": 200,
            "error": '',
            "message": '',
            "data": ''
        }
        try:
            role_id, role_name = UserDA().get_user_role_by_id(user_id)
            if role_id not in (2, '2',):
                result['error'] = settings.ERROR_MSG['access_denied']
                result['status'] = 403
                return result

            emp_data = data.get('data', [])
            is_overwrite = data.get('overwrite', 0)
            appraisal_year = data.get('year', 0)
            batch_id = data.get('batch_id', 0)

            task_details = generate_appraisal_forms.apply_async(
                [user_id, emp_data, is_overwrite, appraisal_year, batch_id],
                queue=settings.CELERY_QUEUE['appraisal_form']
            )
            task_id = task_details.task_id
            is_job_complete = False
            loop_count = 0
            while not is_job_complete:
                job_result = AsyncResult(task_id)
                if job_result:
                    state = job_result.state
                    if str(state).upper() == 'SUCCESS':
                        is_job_complete = True
                    elif loop_count >= 18:
                        result['error'] = 'The job with ID %s is timeout and generate_appraisal_forms job is failed.' % task_id
                        break
                    else:
                        loop_count += 1
                        time.sleep(10)
                else:
                    loop_count += 1
                    time.sleep(10)

            if is_job_complete:
                appraisal_job_log = AppraisalDA().get_all_appraisal_celery_job_log()
                result['data'] = json.loads(appraisal_job_log[0].message)['job_status']

            result["message"] = "Appraisal Initiated Successfully"

        except Exception as err:
            result["error"] = settings.ERROR_MSG['application_error']\
                .format(err, self.__log.error(self.__exception.get_exception()))
        return result

    def get_appraisal_form_by_appraisal_token(self, user_id, token):
        result = {
            "error": "",
            "data": [],
            "permission": ""
        }
        try:
            app_form = AppraisalDA().get_appraisal_form_by_token(token)
            if not app_form:
                result['error'] = "Invalid appraisal token provided."
                return result

            role_id, role_name = UserDA().get_user_role_by_id(user_id)

            if role_id in (1,2):
                is_permitted = True
                is_view_enabled = True
            else:
                is_permitted = self.__is_access_permission(user_id, app_form)
                is_view_enabled, message = self.__is_view_permission(user_id, app_form)

            if app_form.appraiser_id==user_id or app_form.reviewer_id==user_id:
                is_view_enabled, message = self.__is_view_permission(user_id, app_form)

            if not is_permitted:
                result['error'] = settings.ERROR_MSG['access_denied']
                result['permission'] = False
                return result

            if not is_view_enabled:
                result['error'] = message
                result['permission'] = False
                return result

            temp = {}
            temp['emp_id'] = app_form.employee_id
            temp['appraiser_id'] = app_form.appraiser_id
            temp['reviewer_id'] = app_form.reviewer_id
            temp['appraiser_expiry_date'] = datetime.strftime(
                app_form.appraiser_expiry_date, '%d/%m/%Y')
            temp['reviewer_expiry_date'] = datetime.strftime(
                app_form.reviewer_expiry_date, '%d/%m/%Y')
            temp['employee_expiry_date'] = datetime.strftime(
                app_form.employee_expiry_date, '%d/%m/%Y')
            temp['appraiser_submitted'] = app_form.appraiser_submitted
            temp['reviewer_submitted'] = app_form.reviewer_submitted
            temp['employee_submitted'] = app_form.employee_submitted
            temp['organization_id'] = app_form.organization_id
            temp['appraisal_form'] = json.loads(app_form.appraisal_data)
            appraisal_period = AppraisalDA().get_appraisal_period_by_id(app_form.period_id)
            temp['appraisal_period'] = str(
                appraisal_period.period_start_date.year) + '-'+str(appraisal_period.period_end_date.year)
            temp['status'] = app_form.status

            if(app_form.appraiser_expiry_date >= datetime.now().date()):
                temp['appraiser_exp_status'] = True
            else:
                temp['appraiser_exp_status'] = False
            if (app_form.reviewer_id == 0):
                if(app_form.reviewer_expiry_date >= datetime.now().date()):
                    temp['appraiser_exp_status'] = True
            if(app_form.employee_expiry_date >= datetime.now().date()):
                temp['employee_exp_status'] = True
            else:
                temp['employee_exp_status'] = False
            if(app_form.reviewer_expiry_date >= datetime.now().date()):
                temp['reviewer_exp_status'] = True
            else:
                temp['reviewer_exp_status'] = False
            result['data'].append(temp)
            result['permission'] = True

        except Exception as err:
            result["error"] = settings.ERROR_MSG['application_error']\
                .format(err, self.__log.error(self.__exception.get_exception()))
        return result

    def __is_access_permission(self, user_id, appraisal_form):
        permission = False
        permitted_ids = []
        try:
            permitted_ids.append(self.__get_clean_integer(appraisal_form.employee_id))
            permitted_ids.append(self.__get_clean_integer(appraisal_form.appraiser_id))
            permitted_ids.append(self.__get_clean_integer(appraisal_form.reviewer_id))
            user_grops, err = UserDA().get_user_group_mapping_by_group_id(group_id=2) #HR Role
            if user_grops:
                for each_item in user_grops:
                    try:
                        permitted_ids.append(int(each_item[0]))
                    except Exception as err:
                        continue

            if int(user_id) in permitted_ids:
                permission = True
        except Exception as err:
            permission = False
        return permission

    def __generate_email_msg_for_appraiser(self, emp_name, str_time, str_due_date):
        msg = """
        {0} has completed his self assessment on {1}.
        Right now it is waiting for your review (Review with Appraiser),  Please do the needful.
        Due Date: {2}
        """.format(emp_name, str_time, str_due_date)
        return msg

    def __generate_email_msg_for_reviewer(self, emp_name, str_time, str_due_date, app_name):
        msg = """
        {0} has completed {3}'s assessment on {1}
        Right now it is waiting for your review (Review with Reviewer),  Please do the needful.
        Due Date: {2}
        """.format(emp_name, str_time, str_due_date, app_name)
        return msg


    def update_appraisal_form(self, user_id, data):
        result = {
            "error": '',
            "message": ''
        }
        try:
            token = data.get('token')
            form_data = data.get('form_data')
            updater_role = data.get('updater_role')
            update_type = data.get('update_type')
            reviewer = None
            reviewer_name = '-'
            to_email = ''
            appraisal_form = AppraisalDA().get_appraisal_form_by_token(token)
            if not appraisal_form:
                result['error'] = "Invalid appraisal token provided."
                return result

            active_users = self.__get_active_emp_dict()
            updating_user = active_users.get(user_id, None)
            if not updating_user:
                result['error'] = settings.ERROR_MSG['access_denied']
                return result
            role_id, role_name = UserDA().get_user_role_by_id(user_id)
            expiry_date, expiry_status = self.appraisal_form_access_expiry_check(user_id, role_id, appraisal_form)
            if expiry_status:
                result['error'] = f"Your acess to this appraisal form expired on %s " %(expiry_date.strftime("%d/%m/%Y"))
                result['permission'] = False
                return result

            if appraisal_form.reviewer_id:
                reviewer = active_users.get(appraisal_form.reviewer_id, None)
                reviewer_name = self.__get_emp_name(reviewer)
            appraiser = active_users.get(appraisal_form.appraiser_id, None)
            appraisee = active_users.get(appraisal_form.employee_id, None)
            appraiser_name = self.__get_emp_name(appraiser)
            appraisee_name = self.__get_emp_name(appraisee)
            updating_emp_name = self.__get_emp_name(updating_user)
            #if appraisal_form:
            is_permitted = self.__is_access_permission(user_id, appraisal_form)
            if not is_permitted:
                result['error'] = settings.ERROR_MSG['access_denied']
                result['permission'] = False
                return result

            update_permission = self.get_permission_for_update_appraisal_form(appraisal_form, updater_role)
            if not update_permission:
                result['error'] = settings.ERROR_MSG['access_denied']
                return result

            update_data = {}
            update_data['appraisal_data'] = json.dumps(form_data)
            if update_type.upper() == "SAVE":
                action = settings.APPRAISAL_LOG[3].format(updating_emp_name, datetime.now().strftime("%d/%m/%Y %I:%M %p"))
                result['message'] = "Self Assesment Saved Successfully."
            if update_type.upper() == "SUBMIT":
                email_dto = new_dto()
                if updater_role.upper() == "EMPLOYEE":
                    msg = self.__generate_email_msg_for_appraiser(
                        updating_emp_name,
                        datetime.now().strftime("%d/%m/%Y %I:%M %p"),
                        appraisal_form.appraiser_expiry_date.strftime("%d/%m/%Y")
                        )
                    email_dto.message = msg
                    email_dto.reciever_name = appraiser_name
                    email_dto.heading = appraisee_name + " - Annual Performance Appraisal"
                    email_subject = "Completed Self Assessment"

                    update_data['employee_submitted'] = 1
                    # appraisee submitted
                    update_data['status'] = settings.APPRAISAL_STATUS["APPRAISEE_SUBMITTED"]
                    result['message'] = "Your Self Assessment Completed Successfully."
                    to_email = appraiser.email

                if updater_role.upper() == "APPRAISER":
                    update_data['appraiser_submitted'] = 1
                    update_data['status'] = settings.APPRAISAL_STATUS["APPRAISER_SUBMITTED"]
                    result['message'] = appraisee_name + "'s Review Completed Successfully."
                    if reviewer:
                        to_email = reviewer.email
                        msg = self.__generate_email_msg_for_reviewer(
                            updating_emp_name,
                            datetime.now().strftime("%d/%m/%Y %I:%M %p"),
                            appraisal_form.appraiser_expiry_date.strftime("%d/%m/%Y"),
                            appraisee_name)
                        email_dto.message = msg
                        email_dto.reciever_name = reviewer_name
                        email_dto.heading = appraisee_name +" - Annual Performance Appraisal"
                        email_subject = "Completed {0}'s  Assessment".format(appraisee_name)
                    else:
                        update_data['status'] = settings.APPRAISAL_STATUS["REVIEWER_SUBMITTED"]
                        result['message'] = appraisee_name + "'s Review Completed Successfully."
                if updater_role.upper() == "REVIEWER":
                    update_data['reviewer_submitted'] = 1
                    update_data['status'] = settings.APPRAISAL_STATUS["REVIEWER_SUBMITTED"]
                    result['message'] = appraisee_name + "'s Review Completed Successfully."
                if updater_role.upper() == "HR":
                    result['message'] = "Appraisal Form Updated Successfully"


                action = settings.APPRAISAL_LOG[2].format(updating_emp_name, datetime.now().strftime("%d/%m/%Y %I:%M %p"))
            if form_data['form_type'] == "Lead":
                rating = form_data['personal_appraisal']['competancy_assessment']['overall_rating']['total_overall_rating']['value']
                if rating:
                    update_data['rating'] = rating
            else:
                for each in form_data['personal_appraisal']['overall_rating']['values']:
                    if (each['label'] == "RATING"):
                        rating = each['value']
                        if rating:
                            update_data['rating'] = rating

            with transaction.atomic():
                AppraisalDA().update_appraisal_form(appraisal_form.appraisal_id, update_data)
                log_data = {
                    'appraisal_id': appraisal_form.appraisal_id,
                    'action': action,
                    'employee_id': updating_user.id
                }
                AppraisalDA().create_appraisal_log(log_data)

            if updater_role.upper() in ['EMPLOYEE', 'APPRAISER', 'REVIEWER']:
                if to_email:
                    email_dto.link = f"{settings.BASE_URL}assessment/model/{appraisal_form.appraisal_token}"
                    email_msg = AppraisalNotificationBL().generate_appraisal_update_notification(email_dto)
                    AppraisalNotificationBL().send_appraisal_notification(
                        email_msg,
                        appraisee_name,
                        to_email,
                        email_subject)



        except Exception as err:

            print(err)
            result["error"] = settings.ERROR_MSG['application_error']\
                .format(err, self.__log.error(self.__exception.get_exception()))
        return result

    def get_permission_for_update_appraisal_form(self, appraisal_form, user_role):
        permission = False
        if user_role.upper() == "EMPLOYEE":
            if (appraisal_form.status == settings.APPRAISAL_STATUS['APPRAISAL_ISSUED']):
                permission = True
        elif user_role.upper() == "APPRAISER":
            if (appraisal_form.status == settings.APPRAISAL_STATUS['APPRAISEE_SUBMITTED']):
                permission = True
        elif user_role.upper() == "REVIEWER":
            if (appraisal_form.status == settings.APPRAISAL_STATUS['APPRAISER_SUBMITTED']):
                permission = True
        elif user_role.upper() == "HR":
            permission = True
        return permission

    def __is_view_permission(self, user_id, appraisal_form):
        permission = False
        message = ''
        if appraisal_form.employee_id == user_id:
            permission = True
            if appraisal_form.status != settings.APPRAISAL_STATUS['APPRAISAL_ISSUED']:
                permission = False
                message = "You don't have access permission to your submitted form."
                return permission, message
        elif appraisal_form.appraiser_id == user_id:
            if appraisal_form.status != settings.APPRAISAL_STATUS['APPRAISAL_ISSUED']:
                permission = True
            else:
                message = "Appraisee is not completed his/her self assessment yet. You can assess only after their self assessment. Please wait, Thank you for your patience."

        elif appraisal_form.reviewer_id == user_id:
            if appraisal_form.status in (settings.APPRAISAL_STATUS['APPRAISER_SUBMITTED'], settings.APPRAISAL_STATUS['REVIEWER_SUBMITTED']):
                permission = True
            else:
                message = "Appraiser is not completed the review with  appraisee yet. You can assess only after their assessment. Please wait, Thank you for your patience."
        # if appraisal_form.status == settings.APPRAISAL_STATUS['REVIEWER_SUBMITTED']:
        #     permission = True
        #     message = ''

        return permission, message




    def get_all_appraisal(self, user_id, year, organization, batch_id):
        result = {
            "data": [],
            "error": ''
        }
        try:
            batch_id = self.__get_clean_integer(batch_id)
            batch = AppraisalDA().get_appraisal_batch_by_id(batch_id)

            if not batch:
                result['error'] = "Invalid Batch"
                result['status'] = 499
                return result
            year = self.__get_clean_integer(year)
            if not year:
                result['error'] = "Invalid Year."
                result['status'] = 499
                return result

            appraisal_period = AppraisalDA().get_appraisal_period_by_date(year)
            if not appraisal_period:
                result['error'] = "No appraisal period recoreded in system for the year " + str(year)
                result['status'] = 499
                return result


            organization = self.__get_clean_integer(organization)
            role_id, role_name = UserDA().get_user_role_by_id(user_id)
            forms = AppraisalDA().get_all_my_appraisal_forms_by_appraisal_period(user_id, appraisal_period.period_id, role_id)
            profile_dict =  self.__user_profile_dict()
            emp_dict = self.__get_all_emp_dict()
            all_appraisal_log = AppraisalDA().get_all_appraisal_log()

            lead_ids = UserDA().get_emps_with_role()

            for each in forms:
                temp = {}
                log = []
                log_list = all_appraisal_log.filter(appraisal_id=each.appraisal_id)
                for each_log in log_list:
                    log.append(each_log.action)
                if each.batch_id == batch_id:

                    company_id = 0
                    publish_access = False

                    if role_id in (1,2):
                        publish_access = True
                    elif each.appraiser_id==user_id or each.reviewer_id==user_id:
                        publish_access = True

                    if each.employee_id in lead_ids:
                        publish_access = False
                        if role_id in (1, '1', 2, '2', 3, '3'):
                            publish_access = True

                    user_profile = profile_dict.get(each.employee_id, None)
                    if user_profile:
                        company_id = user_profile.company_id

                    if company_id == organization or organization == 0:
                        user = emp_dict.get(each.employee_id, None)
                        appraiser = emp_dict.get(each.appraiser_id, None)
                        if each.reviewer_id:
                            reviewer = emp_dict.get(each.reviewer_id, None)
                            temp['reviewer'] = self.__get_emp_name(reviewer)
                        else:
                            temp['reviewer'] = '-'
                        temp['organization'] = company_id
                        temp['appraiser'] = self.__get_emp_name(appraiser)
                        temp['employee'] =  self.__get_emp_name(user)
                        temp['status'] = each.status
                        temp['appraisal_token'] = each.appraisal_token
                        temp['rating'] = "N.A"
                        if role_id in (1,2) and each.status in (4,6):
                            if each.rating is not None and each.rating !=0 :
                                temp['rating'] = settings.PERSONAL_APPRAISAL_RATINGS[each.rating]
                            else:
                                temp['rating'] = "N.A"

                        elif each.is_published:
                            if each.rating is not None and each.rating !=0 :
                                temp['rating'] = settings.PERSONAL_APPRAISAL_RATINGS[each.rating]
                            else:
                                temp['rating'] = "N.A"
                        else:
                            temp['rating'] = "N.A"
                        temp['assessment_file'] = ''
                        if each.assessment_file:
                            temp['assessment_file'] = each.assessment_file

                        temp['log_list'] = log
                        temp['appraiser_exp_date'] = datetime.strftime(
                            each.appraiser_expiry_date, "%d/%m/%Y")
                        temp['employee_exp_date'] = datetime.strftime(
                            each.employee_expiry_date, "%d/%m/%Y")
                        temp['reviewer_exp_date'] = datetime.strftime(
                            each.reviewer_expiry_date, "%d/%m/%Y")
                        temp['is_selfassessment_completed'] = each.employee_submitted
                        temp['employee_id'] = each.employee_id
                        temp['publish_access'] = publish_access
                        result['data'].append(temp)

        except Exception as err:
            print(err)
            result["error"] = settings.ERROR_MSG['application_error']\
                .format(err, self.__log.error(self.__exception.get_exception()))
        return result

    def get_appraisal_batches(self):
        result = {"batches":[], "error": '', "status": 200}
        try:
            batches = AppraisalDA().get_all_appraisal_batches()
            batch_list = []
            for batch in batches:
                temp={}
                temp['id'] = batch.batch_id
                temp['batch_name'] = batch.batch_name
                batch_list.append(temp)
            result['batches'] = batch_list


        except Exception as err:
            result["error"] = settings.ERROR_MSG['application_error']\
                .format(err, self.__log.error(self.__exception.get_exception()))
        return result

    def publish_appraisal_normalization_result(self, user_id, user_email, year, organization, batch_id, file=None):
        result = {"message": '', "error": '', "status": 200}
        user_dict = {}
        file_dict = {}
        try:

            users = UserDA().get_all_active_users()
            for each_user in users:
                user_dict[each_user.id] = each_user
            batch_id = self.__get_clean_integer(batch_id)
            batch = AppraisalDA().get_appraisal_batch_by_id(batch_id)

            if not batch:
                result['error'] = "Invalid batch provided."
                result['status'] = 499
                return result

            year = self.__get_clean_integer(year)
            if not year:
                result['error'] = "Invalid year provided."
                result['status'] = 499
                return result

            appraisal_period = AppraisalDA().get_appraisal_period_by_date(year)
            if not appraisal_period:
                result['error'] = "No appraisal period recoreded in system for the year " + str(year)
                result['status'] = 499
                return result

            organization = self.__get_clean_integer(organization)

            role_id, role_name = UserDA().get_user_role_by_id(user_id)
            if role_id != 2:
                result['error'] = settings.ERROR_MSG['access_denied']
                result['status'] = 403
                return result

            appraisal_forms = AppraisalDA().get_all_appraisal_forms_by_appraisal_period_batch_id_and_organization(
                appraisal_period.period_id, batch_id, organization)

            if not appraisal_forms:
                result['error'] = "There are no records to publish."
                return result

            files = self.download_extract_zip(file)
            for each in files:
                try:
                    file_names = each[0].split("/")
                    file_name = file_names[1]
                    if file_name:
                        emp_code = file_name.split('.pdf')[0]
                        file_name = f"{emp_code}_Annual_Performance_Assesment_{year}.pdf"
                        file_dict[emp_code] = {'file_name': file_name, 'file_content': each[1]}
                except Exception as err:
                    self.__log.error(err)
                    continue
            with transaction.atomic():
                log_summary = []
                for appraisal_form in appraisal_forms:
                    if appraisal_form.employee_id not in user_dict.keys():
                        continue
                    #if appraisal_form.status != 1:
                    # if appraisal_form.employee_id == 124:
                    #     self.__log.error('I am in if')
                    file_name = ''
                    file_obj = file_dict.get(str(user_dict[appraisal_form.employee_id].username), None)
                    if file_obj:
                        # if appraisal_form.employee_id == 124:
                        #     self.__log.error('I am in if 1')
                        file_name = file_obj.get('file_name', '')
                        file_path = f"{settings.CONFIDENTIAL_DOCS}assessment_files/{file_name}"
                        self.__file_manager.upload_encrypted_file(file_path, file_obj['file_content'])
                        if appraisal_form.status == 4:
                            final_status = 6
                        else:
                            final_status= appraisal_form.status

                        update_data = {"status": final_status, 'assessment_file': file_name}
                        AppraisalDA().publish_appraisal_normalization_result\
                            (appraisal_period.period_id, batch_id,\
                            organization, update_data, appraisal_form.employee_id)
                    else:
                        full_name = user_dict[appraisal_form.employee_id].first_name+' '+user_dict[appraisal_form.employee_id].last_name
                        log_summary.append(f'Annual Performance Assessment Letter not found for the employee {full_name}')
                if len(log_summary)>0:
                    self.__send_summary(user_email, log_summary)
                result['message'] = "Normalization Result Published Successfully"


        except Exception as err:
            result["error"] = settings.ERROR_MSG['application_error']\
                .format(err, self.__log.error(self.__exception.get_exception()))
        return result

    def appraisal_form_access_expiry_check(self, user_id, role_id, appraisal_form):

        expiry_status = False
        employee_exp_date = appraisal_form.employee_expiry_date
        appraiser_exp_date = appraisal_form.appraiser_expiry_date
        reviewer_exp_date = appraisal_form.reviewer_expiry_date
        expiry_date = None

        if role_id in [1, '1', 2, '2']:
            return expiry_date, expiry_status

        elif appraisal_form.employee_id == user_id:
            expiry_date = employee_exp_date

        elif appraisal_form.appraiser_id == user_id:
            if appraisal_form.reviewer_id == 0:
                expiry_date = reviewer_exp_date
            else:
                expiry_date = appraiser_exp_date

        elif appraisal_form.reviewer_id == user_id:
            expiry_date = reviewer_exp_date

        if expiry_date:
            if expiry_date < datetime.now().date():
                expiry_status = True

        return expiry_date, expiry_status

    def download_extract_zip(self, zip_file):
        """
        Download a ZIP file and extract its contents in memory
        yields (filename, file-like object) pairs
        """
        with zipfile.ZipFile(io.BytesIO(zip_file.read())) as thezip:
            for zipinfo in thezip.infolist():
                with thezip.open(zipinfo) as thefile:
                    yield zipinfo.filename, thefile.read()

    def __is_download_performance_assesment_letter(self, login_user_id, login_emp_code, filename):
        is_permitted = False
        role_id, role_name = UserDA().get_user_role_by_id(login_user_id)
        if role_id in (1,2,3):
            return True
        emp_code = filename.split('_')[0]
        emp_obj = UserDA().get_user_by_emp_id(emp_code)
        if emp_obj:
            is_member = UserDA().is_team_member(emp_obj.id, login_user_id)
            if is_member and login_user_id in settings.APPRISAL_LEADS:
                return True
        if str(login_emp_code) == str(emp_code):
            return True
        else:
            return False


    def download_performance_assesment_letter(self, request, filename):
        result = {}
        is_permitted = False
        try:
            is_permitted = self.__is_download_performance_assesment_letter(request.user.id, request.user.username, filename)
            if not is_permitted:
                result['error'] = settings.ERROR_MSG['access_denied']
                return result
            file_path = f"{settings.CONFIDENTIAL_DOCS}assessment_files/{filename}"
            decrypted_content = self.__file_manager.read_encrypted_file(file_path)
            if decrypted_content:
                result = HttpResponse(content_type='application/pdf')
                result['Content-Disposition'] = f'attachment; filename="{filename}"'
                result.write(decrypted_content)
                return result
            else:
                result['error'] = 'File not found'
                return result
        except Exception as err:
            result["error"] = settings.ERROR_MSG['application_error']\
                .format(err, self.__log.error(self.__exception.get_exception()))
        return result

    def __send_summary(self, to_email, log_summary=[]):
        try:
            subject = 'Annual Performance Assessment Summary'
            email_dto = new_dto()
            email_dto.heading = subject
            email_dto.summary = log_summary
            email_conetent = AppraisalNotificationBL().generate_appraisal_normalization_summary(
                email_dto
            )
            AppraisalNotificationBL().send_appraisal_summary_notification(
                        email_conetent,
                        to_email,
                        subject)
        except Exception as err:
            settings.ERROR_MSG['application_error']\
                .format(err, self.__log.error(self.__exception.get_exception()))
        return None


    def __is_permission_to_publish_performance_letter(self, login_user_id, filename):
        role_id, role_name = UserDA().get_user_role_by_id(login_user_id)
        if role_id in (1,2):
            return True
        emp_code = filename.split('_')[0]
        emp_obj = UserDA().get_user_by_emp_id(emp_code)
        if emp_obj:
            is_member = UserDA().is_team_member(emp_obj.id, login_user_id)
            if is_member and login_user_id in settings.APPRISAL_LEADS:
                return True
        return False


    def publish_performance_assesment_letter(self, request, filename, token):
        result = {'error':'', 'message':''}
        is_permitted = False
        context = {}
        try:
            user_id = request.user.id
            username = request.user.first_name+' '+request.user.last_name
            try:
                user_profile = UserDA().get_user_profile_by_id(user_id)
                designation = UserDA().get_job_title_by_id(user_profile.job_title).job_title
            except:
                designation = ''
            is_permitted = is_permitted = self.__is_permission_to_publish_performance_letter(request.user.id, filename)
            if not is_permitted:
                result['error'] = settings.ERROR_MSG['access_denied']
                return result

            assessment_form = AppraisalDA().get_appraisal_form_by_token(token)
            if assessment_form:
                employee = UserDA().get_user_by_emp_id(filename.split("_")[0])
                subject = 'Annual Performance Assessment Letter 2022-23'
                context['file_name'] = filename
                context['file_path'] = settings.CONFIDENTIAL_DOCS+'assessment_files/'
                email_content = '''Hello {0} {1}.<br><br>
                    I hope this everything is well for you. Please find attached the assessment letter for your reference. It is my pleasure to publish this letter and share the results of the assessment with you.<br><br>
                    I thank you for your participation in the assessment process. Please do not hesitate to contact me,  if you have any questions or concerns. I am committed to helping you grow and succeed in your role.<br><br>
                    Thank you for your hard work and dedication to our organisation.
                    <br><br>
                    Regards,<br>
                    {2}<br>
                    {3}.
                '''.format(employee.first_name, employee.last_name, username, designation)
                to_email = employee.email
                update_data = {"status": 5, 'is_published': 1}
                AppraisalDA().update_appraisal_form(assessment_form.appraisal_id, update_data)
                AppraisalNotificationBL().send_appraisal_summary_notification(
                            email_content,
                            to_email,
                            subject,
                            publish_dict=context)
                result['message'] = 'Annual Performance Assessment Letter published succesfully'
        except Exception as err:
            result["error"] = settings.ERROR_MSG['application_error']\
                .format(err, self.__log.error(self.__exception.get_exception()))
        return result

