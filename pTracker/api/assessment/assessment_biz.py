import random
import json
import math
from io import BytesIO
from django.http import HttpResponse
from types import SimpleNamespace
from datetime import datetime, date, timedelta

from reportlab.lib.pagesizes import A4
from reportlab.platypus import SimpleDocTemplate, Table, TableStyle, Spacer, Paragraph, KeepTogether
from reportlab.lib.styles import getSampleStyleSheet, ParagraphStyle
from reportlab.lib import colors
from reportlab.lib.units import inch

from django.conf import Settings, settings
from django.db import  DatabaseError, transaction
from django.http import response, HttpResponse
from django.template import loader


from pTracker.common.utility import Utility
from pTracker.common.exception_handler import ExceptionHandler
from pTracker.common.logs import Logs

from pTracker.dataaccess.ptracker_access.user_da import UserDA
from pTracker.dataaccess.ptracker_access.assessment_da import AssessmentDA
from pTracker.dataaccess.ptracker_access.holiday_da import HolidayDA

from pTracker.settings import constants

from pTracker.cronjobs.email_sender import send_email_notification



def new_dto():
    dto = SimpleNamespace()
    return dto

class AssessmentBL():
    def __init__(self):
        self.__log = Logs()
        self.__exception = ExceptionHandler()
        self.__utility = Utility()

    def get_dropdown_params(self, request):
        response = {"departments": [], "assessees": [], 'assessors': []}
        user_dict = {}
        user_ids = []
        try:
            user_id = request.user.id
            response["departments"] = settings.DEPARTMENTS
            is_permitted = True  # self.__utility.is_permitted(user_id, 'can_process_payslip') TODO
            if not is_permitted:
                response["error"] = settings.ERROR_MSG.get("access_denied")
                response["status"] = 403
                return response

            active_users = UserDA().get_all_active_users()
            for each_user in active_users:
                user_dict[each_user.id] = each_user
                user_ids.append(each_user.id)
            probation_employees = UserDA().get_user_profiles_by_employee_ids(user_ids, 1)  # 1 - Probation status
            if probation_employees:
                for each_employee in probation_employees:
                    user_obj = user_dict.get(each_employee.user_id)
                    emp_name = f"{user_obj.first_name} {user_obj.last_name}"
                    response['assessees'].append({'id': each_employee.user_id, 'emp_name': emp_name})
            lead_ids = UserDA().get_emps_with_role(group_ids="4")
            for each_lead in lead_ids:
                user_obj = user_dict.get(each_lead)
                emp_name = f"{user_obj.first_name} {user_obj.last_name}"
                response['assessors'].append({'id': each_lead, 'name': emp_name})
        except Exception as err:
            response["error"] = settings.ERROR_MSG['application_error'].format(
                str(err), self.__log.error(self.__exception.get_exception())
            )
        return response

    def create_assessment_v1(self, request):
        response = {"error": None, "success": False, "msg": ""}
        is_permitted = False
        res = False
        assessment_dates = []
        bcc_addresses = []
        try:
            user_id = request.user.id
            user_name = f"{request.user.first_name} {request.user.last_name}"
            role_id, role_name = UserDA().get_user_role_by_id(user_id)
            if role_id == 2:
                is_permitted = True

            if not is_permitted:
                response["error"] = settings.ERROR_MSG.get('access_denied')
                response['status'] = 403
                return response

            post_data = request.data
            total_assessment = json.loads(post_data.get('totalAssessment'))
            
            for each in range(len(total_assessment)):
                str_start_date = total_assessment[each]['startDate']
                start_date = datetime.strptime(str_start_date, "%Y-%m-%d")
                end_date = start_date + timedelta(days=365)
                
                holiday_list = HolidayDA().get_holidays(start_date, end_date).values_list('holiday_date', flat=True)

                # Iterate until a valid date_and_time is found
                if self.__is_weekend(start_date):
                    response["error"] = f'{start_date.strftime("%d/%m/%Y")} is a Weekend'
                    return response
                elif self.__is_holiday(start_date.date(), holiday_list):
                    response["error"] = f'{start_date.strftime("%d/%m/%Y")} is a Holiday'
                    return response

            with transaction.atomic():
                assessee_dict = {
                "emp_id": post_data.get('employee'),
                "status": 1,  # initiated
                "department": post_data.get('department'),
                "total_assessment": len(total_assessment),
                "created_by": user_id
                }
                res = AssessmentDA().create_assessee(assessee_dict)
                if res:
                    self.__create_log('initiated', res.emp_id, 0, user_id)

                    for each in range(len(total_assessment)):
                        
                        str_start_date = total_assessment[each]['startDate']
                        start_date = datetime.strptime(str_start_date, "%Y-%m-%d")
                        
                        start_date = start_date.replace(hour=14, minute=30, second=0)

                        assessors = total_assessment[each]['assessors']
                        bcc_addresses = self.__get_assessor_emails(assessors)

                        assessors = [str(i) for i in assessors]
                        
                        assessment_dict = {
                            'emp_id': res.emp_id,
                            'assessment_code': f"Assessment {each}",
                            "assessor": ','.join(assessors),
                            "date_and_time": start_date,
                            "created_by": user_id
                        }
                        res = AssessmentDA().create_assessment(assessment_dict)
                        assessment_dates.append({ each: start_date.strftime("%d/%m/%Y %I:%M %p")} )

                    try:
                        user_profile = UserDA().get_user_profile_by_id(user_id)
                        designation = UserDA().get_job_title_by_id(user_profile.job_title).job_title
                    except:
                        designation = ''

                    employee_profile = UserDA().get_user_profile_by_id(post_data.get('employee'))
                    employee = UserDA().get_user_by_id(post_data.get('employee'))

                    template_name = 'assessment_initiated.html'
                    organization = 'Digital Mesh' if employee_profile.company_id == 2 else 'EM Softech'
                    subject = "Assessment Notification"
                    mail_context = {}
                    mail_context['heading'] = subject
                    mail_context['emp_name'] = f"{employee.first_name} {employee.last_name}"
                    mail_context['organization'] = organization
                    mail_context['hr_name'] = user_name
                    mail_context['hr_position'] = designation
                    mail_context['hr_contact_info'] = request.user.email
                    mail_context['assessment_dates'] = assessment_dates
                    email_content = self.__generate_email_template(template_name, mail_context)

                    bcc_addresses = ['subish@digitalmesh.com']  # TODO remove this
                    # employee.email = 'subish@digitalmesh.com'  # TODO remove this
                    self.send_induction_email(subject, email_content, employee.email, bcc_address=bcc_addresses)
                if res:
                    response["success"] = True
    
        except Exception as err:
            response["error"] = settings.ERROR_MSG["application_error"].format(
                str(err), self.__log.error(self.__exception.get_exception())
            )
        return response

    def create_assessment(self, request):
        response = {"error": None, "success": False, "msg": ""}
        is_permitted = False
        res = False
        assessment_dates = []
        bcc_addresses = []
        assessment_intervel_days = 30
        try:
            user_id = request.user.id
            user_name = f"{request.user.first_name} {request.user.last_name}"
            role_id, role_name = UserDA().get_user_role_by_id(user_id)
            if role_id == 2:
                is_permitted = True

            if not is_permitted:
                response["error"] = settings.ERROR_MSG.get('access_denied')
                response['status'] = 403
                return response

            post_data = request.data
            total_assessment = int(post_data.get('totalAssessment'))

            with transaction.atomic():
                assessee_dict = {
                "emp_id": post_data.get('employee'),
                "status": 1,  # initiated
                "department": post_data.get('department'),
                "total_assessment": total_assessment,
                "created_by": user_id
                }
                res = AssessmentDA().create_assessee(assessee_dict)
                if res:
                    lead_id = UserDA().get_lead_id_by_user(res.emp_id)

                    str_start_date = post_data.get('startDate')
                    self.__create_log('initiated', res.emp_id, 0, user_id)

                    start_date = datetime.strptime(str_start_date, "%Y-%m-%d")
                    end_date = start_date + timedelta(days=120)

                    holiday_list = HolidayDA().get_holidays(start_date, end_date).values_list('holiday_date', flat=True)

                    for each in range(1, total_assessment + 1):

                        # Iterate until a valid date_and_time is found
                        while self.__is_weekend(start_date) or self.__is_holiday(start_date, holiday_list):
                            start_date += timedelta(days=1)
                        start_date = start_date.replace(hour=14, minute=30, second=0)
                        if each==3:
                            assessors = str(lead_id)
                        else:
                            assessors = self.__get_assessor(lead_id)
                        bcc_addresses = self.__get_assessor_emails(assessors)

                        assessment_dict = {
                            'emp_id': res.emp_id,
                            'assessment_code': f"Assessment {each}",
                            "assessor": assessors,
                            "date_and_time": start_date,
                            "created_by": user_id
                        }
                        res = AssessmentDA().create_assessment(assessment_dict)
                        assessment_dates.append({ each: start_date.strftime("%d/%m/%Y %I:%M %p")} )
                        start_date = start_date + timedelta(days=assessment_intervel_days)

                    try:
                        user_profile = UserDA().get_user_profile_by_id(user_id)
                        designation = UserDA().get_job_title_by_id(user_profile.job_title).job_title
                    except:
                        designation = ''

                    employee_profile = UserDA().get_user_profile_by_id(post_data.get('employee'))
                    employee = UserDA().get_user_by_id(post_data.get('employee'))

                    template_name = 'assessment_initiated.html'
                    organization = 'Digital Mesh' if employee_profile.company_id == 2 else 'EM Softech'
                    subject = "Assessment Notification"
                    mail_context = {}
                    mail_context['heading'] = subject
                    mail_context['emp_name'] = f"{employee.first_name} {employee.last_name}"
                    mail_context['organization'] = organization
                    mail_context['hr_name'] = user_name
                    mail_context['hr_position'] = designation
                    mail_context['hr_contact_info'] = request.user.email
                    mail_context['assessment_dates'] = assessment_dates
                    email_content = self.__generate_email_template(template_name, mail_context)

                    bcc_addresses = ['subish@digitalmesh.com']  # TODO remove this
                    employee.email = 'subish@digitalmesh.com'  # TODO remove this
                    self.send_induction_email(subject, email_content, employee.email, bcc_address=bcc_addresses)
                if res:
                    response["success"] = True

        except Exception as err:
            response["error"] = settings.ERROR_MSG["application_error"].format(
                str(err), self.__log.error(self.__exception.get_exception())
            )
        return response

    def update_assessment(self, request):
        response = {"error": None, "success": False}
        is_success = False
        try:
            user_id = request.user.id
            role_id, name = UserDA().get_user_role_by_id(user_id)
            is_permitted = True #TODO
            if not is_permitted:
                response["error"] = settings.ERROR_MSG.get('access_denied')
                response['status'] = 403
                return response

            request_data = request.data
            assessee_id = request_data.get('assessee_id')
            action = request_data.get('action')
            assessment_id = request_data.get('assessment_id', 0)

            if action=='cancel':
                res = AssessmentDA().update_assessee(assessee_id, {'status': 4})
                if res:is_success = AssessmentDA().delete_assessment(assessee_id)

            if is_success:
                self.__create_log(action, assessee_id, assessment_id, user_id)
                response['success'] = True

        except Exception as err:
            response["error"] = settings.ERROR_MSG["application_error"].format(
                str(err), self.__log.error(self.__exception.get_exception())
            )
        return response

    def cancel_assessment(self, request):
        response = {"error": None, "success": False}
        is_success = False
        try:
            user_id = request.user.id
            role_id, name = UserDA().get_user_role_by_id(user_id)
            is_permitted = True #TODO
            if not is_permitted:
                response["error"] = settings.ERROR_MSG.get('access_denied')
                response['status'] = 403
                return response

            request_data = request.data
            assessment_id = request_data.get('assessment_id', 0)

            is_success = AssessmentDA().delete_assessment_by_id(assessment_id)
            if is_success:
                response['success'] = True

        except Exception as err:
            response["error"] = settings.ERROR_MSG["application_error"].format(
                str(err), self.__log.error(self.__exception.get_exception())
            )
        return response

    def reschedule_assessment(self, request):
        response = {"error": None, "success": False}
        is_success = False
        is_valid = False
        try:
            user_id = request.user.id
            user_name = f"{request.user.first_name} {request.user.last_name}"
            role_id, name = UserDA().get_user_role_by_id(user_id)
            is_permitted = True #TODO
            if not is_permitted:
                response["error"] = settings.ERROR_MSG.get('access_denied')
                response['status'] = 403
                return response

            request_data = request.data
            date_and_time = request_data.get('date_and_time', 0)
            assessment_id = request_data.get('assessment_id', 0)
            assessee_id = request_data.get('assessee_id', 0)

            is_valid = self.__validate_date(date_and_time)
            if not is_valid:
                response["error"] = "Input date is not valid"
                response['status'] = 403
                return response
            is_valid = self.__check_assessment_date(datetime.strptime(date_and_time, '%Y-%m-%d %H:%M:%S'), assessee_id)
            if not is_valid:
                response["error"] = "Assessment already created this time"
                response['status'] = 403
                return response
            assessment = AssessmentDA().get_assessment_by_id(assessment_id).last()
            old_date = assessment.date_and_time.strftime("%d/%m/%Y")

            is_success = AssessmentDA().update_assessment(assessment_id, {'date_and_time': date_and_time})
            if is_success:
                new_date = datetime.strptime(date_and_time, '%Y-%m-%d %H:%M:%S').strftime("%d/%m/%y %I:%M %p")
                try:
                    user_profile = UserDA().get_user_profile_by_id(user_id)
                    designation = UserDA().get_job_title_by_id(user_profile.job_title).job_title
                except:
                    designation = ''
                bcc_addresses = self.__get_assessor_emails(assessment.assessor)
                employee_profile = UserDA().get_user_profile_by_id(assessee_id)
                employee = UserDA().get_user_by_id(assessee_id)
                template_name = "reschedule_assessment.html"
                organization = 'Digital Mesh' if employee_profile.company_id == 2 else 'EM Softech'
                subject = "Assessment Reschedule Notification"
                mail_context = {}
                mail_context['heading'] = subject
                mail_context['emp_name'] = f"{employee.first_name} {employee.last_name}"
                mail_context['organization'] = organization
                mail_context['hr_name'] = user_name
                mail_context['hr_position'] = designation
                mail_context['hr_contact_info'] = request.user.email
                mail_context['new_date'] = new_date
                mail_context['old_date'] = old_date
                email_content = self.__generate_email_template(template_name, mail_context)

                bcc_addresses = ['subish@digitalmesh.com']  # TODO remove this
                # employee.email = 'subish@digitalmesh.com'  # TODO remove this
                self.send_induction_email(subject, email_content, employee.email, bcc_address=bcc_addresses)
                self.__create_log('reschedule', assessee_id, assessment_id, user_id)
                response['success'] = True

        except Exception as err:
            response["error"] = settings.ERROR_MSG["application_error"].format(
                str(err), self.__log.error(self.__exception.get_exception())
            )
        return response

    def __check_assessment_date(self, assessment_date, assessee_id):
        is_valid = False
        try:
            assessments = AssessmentDA().get_assessment(assessee_id)
            if not assessments.filter(date_and_time=assessment_date).exists():
                is_valid = True
        except:
            pass
        return is_valid

    def manage_assessee(self, request, status):
        response = {"error": None, "success": False, "data": []}
        assessee_objects = None
        user_dict = {None: '-'}
        try:
            user_id = request.user.id
            role_id, name = UserDA().get_user_role_by_id(user_id)
            user_name = request.user.first_name+' '+request.user.last_name
            if role_id not in (1, 2, 3, 4):
                response["error"] = settings.ERROR_MSG.get('access_denied')
                response['status'] = 403
                return response


            if role_id in (1, 2, 3):
                assessee_objects = AssessmentDA().get_asessee()
            elif role_id==4:
                team_members = UserDA().get_current_team_members_by_lead_id(user_id)
                team_members_ids = [x.id for x in team_members]
                assessee_objects = AssessmentDA().get_asessee(emp_id=team_members_ids)

            active_users = UserDA().get_all_active_users()
            for each in active_users:
                user_dict[each.id] = each.first_name+' '+each.last_name

            if assessee_objects:
                if status=='1': #active
                    assessee_objects = assessee_objects.filter(status__in=[1, 2])
                elif status=='0': #completed
                    assessee_objects = assessee_objects.filter(status=3)
                elif status=='4':
                    assessee_objects = assessee_objects.filter(status=4)
                for each_assessee in assessee_objects:
                    lead_id = UserDA().get_lead_id_by_user(each_assessee.emp_id)
                    temp_dict = {}
                    temp_dict['id'] = each_assessee.emp_id
                    temp_dict['name'] = user_dict[each_assessee.emp_id]
                    temp_dict['status'] = each_assessee.status
                    temp_dict['reporting_to'] = user_dict[lead_id]
                    temp_dict['progress'] = self.__get_progress(each_assessee.emp_id)
                    temp_dict['logs'] = self.__get_logs(each_assessee.emp_id)
                    response["data"].append(temp_dict)

        except Exception as err:
            response["error"] = settings.ERROR_MSG["application_error"].format(
                str(err), self.__log.error(self.__exception.get_exception())
            )
        return response

    def my_assessment(self, request, status, year):
        response = {"error": None, "success": False, "data": []}
        assessment_objects = None
        user_dict = {None: '-'}
        try:
            user_id = request.user.id
            user_name = request.user.first_name+' '+request.user.last_name
            is_permitted = True #TODO
            if not is_permitted:
                response["error"] = settings.ERROR_MSG.get('access_denied')
                response['status'] = 403
                return response
            role_id, name = UserDA().get_user_role_by_id(user_id)

            if role_id in (1, 2, 3):
                assessment_objects = AssessmentDA().get_assessment()
            elif role_id==4:
                team_members = UserDA().get_current_team_members_by_lead_id(user_id)
                team_members_ids = [x.id for x in team_members]
                assessment_objects = AssessmentDA().get_assessment_by_team_ids(team_members_ids)

                assessments = AssessmentDA().get_assessment()
                for each in assessments:
                    is_assessor = self.__check_is_assessor(each.assessor, user_id)
                    if not is_assessor:
                        assessments = assessments.exclude(pk=each.pk)
                assessment_objects = assessment_objects|assessments
            else:
                assessment_objects = AssessmentDA().get_assessment(user_id)

            if assessment_objects:
                active_users = UserDA().get_all_active_users()
                for each in active_users:
                    user_dict[each.id] = each.first_name+' '+each.last_name
                if status == '1':
                    assessment_objects = assessment_objects.filter(assessment_status=status)
                elif status == '0':
                    assessment_objects = assessment_objects.filter(assessment_status=status)
                if year:
                    assessment_objects = assessment_objects.filter(created_date__year=year)
                assessee = AssessmentDA().get_asessee(assessment_objects.last().emp_id).last()
                for each_assessment in assessment_objects:
                    lead_id = UserDA().get_lead_id_by_user(each_assessment.emp_id)
                    temp_dict = {}
                    temp_dict['id'] = each_assessment.assessment_id
                    temp_dict['assessee_id'] = each_assessment.emp_id
                    temp_dict['name'] = user_dict[each_assessment.emp_id]
                    temp_dict['status'] = each_assessment.assessment_status
                    temp_dict['reporting_to'] = user_dict[lead_id]
                    temp_dict['assessee_status'] = assessee.status
                    temp_dict['date'] = each_assessment.date_and_time.strftime("%d/%m/%y %I:%M %p")
                    temp_dict['is_expired'] = not self.__validate_date(each_assessment.date_and_time)
                    temp_dict['assessor'] = self.__get_assessor_names(each_assessment.assessor)
                    temp_dict['round'] = each_assessment.assessment_code
                    temp_dict['is_assessor'] = self.__check_is_assessor(each_assessment.assessor, user_id)
                    response["data"].append(temp_dict)

        except Exception as err:
            response["error"] = settings.ERROR_MSG["application_error"].format(
                str(err), self.__log.error(self.__exception.get_exception())
            )
        return response

    def create_assessment_report(self, request):
        response = {"error": None, "success": False}
        is_permitted = True #TODO
        update_dict = {}
        try:
            user_id = request.user.id
            user_name = request.user.first_name+' '+request.user.last_name
            is_permitted = True #TODO
            if not is_permitted:
                response["error"] = settings.ERROR_MSG.get('access_denied')
                response['status'] = 403
                return response
            role_id, name = UserDA().get_user_role_by_id(user_id)
            request_data = request.data
            comment_list = json.loads(request_data.get('comments', ''))
            assessment_id = request_data.get('assessementID')
            assessee_id = request_data.get('assesseeID')
            update_dict['assessment_status'] = 1 #completed
            update_dict['summative_remark'] = request_data.get('summativeRemark')
            update_dict['time_taken'] = request_data.get('timeTaken')
            update_dict['score'] = request_data.get('score')
            round = request_data.get('round')
            with transaction.atomic():
                res = AssessmentDA().update_assessment(assessment_id, update_dict)
                if res:
                    assessments = AssessmentDA().get_assessment(assessee_id=assessee_id)
                    if assessments.filter(assessment_status=0).count()==0:
                        total_score = 0
                        for each_assessment in assessments:
                            total_score += each_assessment.score
                        update_dict = {'status': 3, 'score':total_score/assessments.count()}
                        AssessmentDA().update_assessee(assessee_id, update_dict)
                    else:
                        AssessmentDA().update_assessee(assessee_id, {'status': 2})#in progress
                    comment_list = json.loads(request_data.get('comments', ''))
                    if comment_list and len(comment_list)>0:
                        for each_comment in comment_list:
                            assessment_dict = {
                                'assessment_id': assessment_id,
                                'comment': each_comment.get('comment'),
                                'comment_type':each_comment.get('commentType'),
                                'is_private': each_comment.get('isPrivate'),
                                'created_by': user_id
                            }
                            AssessmentDA().create_assessment_comment(assessment_dict)

                    try:
                        user_profile = UserDA().get_user_profile_by_id(user_id)
                        designation = UserDA().get_job_title_by_id(user_profile.job_title).job_title
                    except:
                        designation = ''
                    bcc_addresses = self.__get_assessor_emails(assessments.last().assessor)
                    employee_profile = UserDA().get_user_profile_by_id(assessee_id)
                    employee = UserDA().get_user_by_id(assessee_id)
                    template_name = 'assessment_complete.html'
                    organization = 'Digital Mesh' if employee_profile.company_id == 2 else 'EM Softech'
                    subject = f"Assessment Completion Notification"
                    mail_context = {}
                    mail_context['heading'] = subject
                    mail_context['emp_name'] = f"{employee.first_name} {employee.last_name}"
                    mail_context['organization'] = organization
                    mail_context['hr_name'] = user_name
                    mail_context['hr_position'] = designation
                    mail_context['hr_contact_info'] = request.user.email
                    mail_context['assessment_code'] = round
                    email_content = self.__generate_email_template(template_name, mail_context)

                    bcc_addresses = ['subish@digitalmesh.com']  # TODO remove this
                    # employee.email = 'subish@digitalmesh.com'  # TODO remove this
                    self.send_induction_email(subject, email_content, employee.email, bcc_address=bcc_addresses)
                    self.__create_log('update', assessee_id, assessment_id, user_id)
                    response['success'] = True

        except Exception as err:
            response["error"] = settings.ERROR_MSG["application_error"].format(
                str(err), self.__log.error(self.__exception.get_exception())
            )
        return response

    def __get_value_by_rounding(self, key):
        result = '-'
        try:
            rounded_key = math.ceil(key)
            result = settings.PERFORMANCE_DICT.get(rounded_key, None)
        except:
            pass
        return result

    def view_assessment_report(self, request, assessment_id):
        response = {"error": None, "success": False, "report_data": [], "assessment_data": {}}
        user_dict = {None: '-'}
        try:
            user_id = request.user.id
            user_name = request.user.first_name+' '+request.user.last_name
            is_permitted = True #TODO
            if not is_permitted:
                response["error"] = settings.ERROR_MSG.get('access_denied')
                response['status'] = 403
                return response
            role_id, name = UserDA().get_user_role_by_id(user_id)
            assessment = AssessmentDA().get_assessment_by_id(assessment_id)
            if assessment:
                assessment=assessment.last()
                response['assessment_data']['assessment_code'] = assessment.assessment_code
                response['assessment_data']['assessor'] = self.__get_assessor_names(assessment.assessor)
                response['assessment_data']['date_and_time'] = assessment.date_and_time.strftime("%d/%m/%y %I:%M %p")
                response['assessment_data']['time_taken'] = self.__get_hours(assessment.time_taken)
                response['assessment_data']['summative_remark'] = assessment.summative_remark
                reports = AssessmentDA().get_assessment_comments(assessment_id)
                for each in reports:
                    temp_dict = {}
                    if each.is_private and role_id in (1, 2, 3, 4):
                        temp_dict['comment'] = each.comment
                        temp_dict['comment_type'] = each.comment_type
                        response['report_data'].append(temp_dict)
                    elif not each.is_private:
                        temp_dict['comment'] = each.comment
                        temp_dict['comment_type'] = each.comment_type
                        response['report_data'].append(temp_dict)
        except Exception as err:
            response["error"] = settings.ERROR_MSG["application_error"].format(
                str(err), self.__log.error(self.__exception.get_exception())
            )
        return response

    def view_assessee_report(self, request, assessee_id=0):
        response = {"error": None, "success": False, "assessment_data": [], 'assessee_data': {}}
        user_dict = {None: '-'}
        try:
            user_id = request.user.id
            user_name = request.user.first_name+' '+request.user.last_name
            is_permitted = True #TODO
            if not is_permitted:
                response["error"] = settings.ERROR_MSG.get('access_denied')
                response['status'] = 403
                return response
            role_id, name = UserDA().get_user_role_by_id(user_id)
            assessee_data = AssessmentDA().get_asessee(assessee_id).last()
            if assessee_data:
                employee = UserDA().get_user_by_id(assessee_id)
                lead_id = UserDA().get_lead_id_by_user(assessee_id)
                lead_obj = UserDA().get_user_by_id(lead_id)
                response['assessee_data']['name'] = employee.first_name+' '+employee.last_name
                response['assessee_data']['reporting_to'] = lead_obj.first_name+' '+lead_obj.last_name
                response['assessee_data']['status'] = assessee_data.status
                response['assessee_data']['progress'] = self.__get_progress(assessee_id)
                response['assessee_data']['overall'] = self.__get_value_by_rounding(assessee_data.score) if assessee_data.status==3 else '-'

            assessments = AssessmentDA().get_assessment(assessee_id)
            if assessments:
                for each_asssessmrnt in assessments.order_by('assessment_code'):
                    report_data = {'positive': [], 'negative': []}
                    temp_dict = {}
                    temp_dict['assessment_code'] = each_asssessmrnt.assessment_code
                    temp_dict['assessor'] = self.__get_assessor_names(each_asssessmrnt.assessor)
                    temp_dict['date_and_time'] = each_asssessmrnt.date_and_time.strftime("%d/%m/%y %I:%M %p")
                    temp_dict['time_taken'] = self.__get_hours(each_asssessmrnt.time_taken)
                    temp_dict['summative_remark'] = each_asssessmrnt.summative_remark if each_asssessmrnt.summative_remark else '-'
                    temp_dict['status'] = each_asssessmrnt.assessment_status
                    temp_dict['score'] = self.__get_value_by_rounding(each_asssessmrnt.score)
                    reports = AssessmentDA().get_assessment_comments(each_asssessmrnt.assessment_id)
                    for each in reports:
                        if each.is_private and role_id in (1, 2, 3, 4):
                            if each.comment_type==0:report_data['negative'].append(each.comment)
                            else:report_data['positive'].append(each.comment)
                        elif not each.is_private:
                            if each.comment_type==0:report_data['negative'].append(each.comment)
                            else:report_data['positive'].append(each.comment)

                    temp_dict['report_data'] = report_data
                    response['assessment_data'].append(temp_dict)
        except Exception as err:
            response["error"] = settings.ERROR_MSG["application_error"].format(
                str(err), self.__log.error(self.__exception.get_exception())
            )
        return response


    def __get_assessee_data(self, assessee_id):
        result = {}
        try:
            status_dict = {}
            assessee_data = AssessmentDA().get_asessee(assessee_id).last()
            if assessee_data:
                employee = UserDA().get_user_by_id(assessee_id)
                lead_id = UserDA().get_lead_id_by_user(assessee_id)
                lead_obj = UserDA().get_user_by_id(lead_id)
                result['name'] = employee.first_name+' '+employee.last_name
                result['reporting_to'] = lead_obj.first_name+' '+lead_obj.last_name
                result['status'] = "Completed" if assessee_data.status else "Pending"
                result['progress'] = self.__get_progress(assessee_id)
                result['overall'] = self.__get_value_by_rounding(assessee_data.score) if assessee_data.status==3 else '-'
        except:
            pass
        return result

    def __get_assessment_data(self, assessee_id, user_id):
        result = []
        try:
            role_id, name = UserDA().get_user_role_by_id(user_id)
            assessments = AssessmentDA().get_assessment(assessee_id)
            if assessments:
                for each_asssessmrnt in assessments.order_by('assessment_code'):
                    report_data = {'positive': [], 'negative': []}
                    temp_dict = {}
                    temp_dict['assessment_code'] = each_asssessmrnt.assessment_code
                    temp_dict['assessor'] = self.__get_assessor_names(each_asssessmrnt.assessor)
                    temp_dict['date_and_time'] = each_asssessmrnt.date_and_time.strftime("%d/%m/%y %I:%M %p")
                    temp_dict['time_taken'] = self.__get_hours(each_asssessmrnt.time_taken)
                    temp_dict['summative_remark'] = each_asssessmrnt.summative_remark if each_asssessmrnt.summative_remark else '-'
                    temp_dict['status'] =  settings.ASSESSMENT_STATUS[each_asssessmrnt.assessment_status]
                    temp_dict['score'] = self.__get_value_by_rounding(each_asssessmrnt.score)
                    reports = AssessmentDA().get_assessment_comments(each_asssessmrnt.assessment_id)
                    for each in reports:
                        if each.is_private and role_id in (1, 2, 3, 4):
                            if each.comment_type==0:report_data['negative'].append(each.comment)
                            else:report_data['positive'].append(each.comment)
                        elif not each.is_private:
                            if each.comment_type==0:report_data['negative'].append(each.comment)
                            else:report_data['positive'].append(each.comment)

                    temp_dict['report_data'] = report_data
                    result.append(temp_dict)
        except Exception as err:
            pass
        return result



    def download_report(self, request):
        from reportlab.lib.enums import TA_CENTER
        response = HttpResponse(content_type='application/pdf')
        response['Content-Disposition'] = 'attachment; filename="assessment_report.pdf"'

        try:
            user_id = request.user.id
            assessee_id = request.GET.get('assessee_id')

            # Create a new PDF document
            pdf = SimpleDocTemplate(response, pagesize=A4)

            # Get the assessee and assessment data
            assessee_data = self.__get_assessee_data(assessee_id)
            assessment_data = self.__get_assessment_data(assessee_id, user_id)

            # Set font styles
            styles = getSampleStyleSheet()
            normal_style = styles['Normal']
            title_style = ParagraphStyle(
                'title',
                parent=normal_style,
                fontName='Helvetica-Bold',
                fontSize=12,
                textColor='#333333',
                alignment=TA_CENTER,
                spaceAfter=12
            )

            subtitle_style = ParagraphStyle(
                'title',
                parent=normal_style,
                fontName='Helvetica-Bold',
                fontSize=11,
                spaceAfter=12
            )

            subtitle_style1 = ParagraphStyle(
                'title',
                parent=styles['Normal'],
                fontName='Helvetica-Bold',
                fontSize=11,
                spaceAfter=8,
                underline=1  # Add underline
            )

            heading_style = ParagraphStyle(
                'heading',
                parent=normal_style,
                fontName='Helvetica-Bold',
                fontSize=10
            )

            # Define table data
            data = [
                [
                    Paragraph("Name", heading_style),
                    Paragraph("Reporting To", heading_style),
                    Paragraph("Status:", heading_style),
                    Paragraph("Overall Performance", heading_style)
                ],
                [
                    Paragraph(assessee_data['name'], normal_style),
                    Paragraph(assessee_data['reporting_to'], normal_style),
                    Paragraph(assessee_data['status'], normal_style),
                    Paragraph(assessee_data['overall'], normal_style)
                ]
            ]


            # Define table style
            table_style = TableStyle([
                ('ALIGN', (0, 0), (-1, 0), 'CENTER'),  # Header row alignment
                ('FONTNAME', (0, 0), (-1, 0), 'Helvetica-Bold'),  # Header row font
                ('FONTSIZE', (0, 0), (-1, 0), 10),  # Header row font size (reduced to 10)
                ('BOTTOMPADDING', (0, 0), (-1, 0), 10),  # Header row bottom padding
                ('BACKGROUND', (0, 1), (-1, -1), colors.white),  # Data row background color
                ('FONTNAME', (0, 1), (-1, -1), 'Helvetica'),  # Data row font
                ('FONTSIZE', (0, 1), (-1, -1), 8),  # Data row font size
                ('VALIGN', (0, 0), (-1, -1), 'MIDDLE'),  # Vertical alignment for all cells
                ('TEXTCOLOR', (0, 1), (-1, -1), colors.black),  # Data row text color
                ('GRID', (0, 0), (-1, -1), 1, colors.black),  # Grid lines
            ])

            # Create the table
            col_widths = [1.50 * inch, 1.50 * inch, 1.25 * inch, 1.90 * inch]
            table = Table(data, colWidths=col_widths)
            table.setStyle(table_style)



            # Add the table to the PDF document
            elements = [
                Paragraph("Assessment Report", title_style),
                Spacer(1, 12),
                table,
                Spacer(1, 18)
            ]

            # Add the assessment data to the report
            for assessment in assessment_data:
                elements.append(KeepTogether([
                    Paragraph("<b>Assessment Round:</b> " + assessment['assessment_code'], subtitle_style1),
                    Spacer(1, 12),
                    Table([
                        [
                            Paragraph("Assessor", heading_style),
                            Paragraph("Date and Time", heading_style),
                            Paragraph("Time Taken", heading_style),
                            Paragraph("Status", heading_style),
                            Paragraph("Score", heading_style),
                        ],
                        [
                            Paragraph(assessment['assessor'], normal_style),
                            Paragraph(assessment['date_and_time'], normal_style),
                            Paragraph(assessment['time_taken'], normal_style),
                            Paragraph(assessment['status'], normal_style),
                            Paragraph(assessment['score'], normal_style)
                        ]
                    ], style=table_style),
                    Spacer(1, 5),
                    Paragraph("<b>Summative Remark:</b> " + assessment['summative_remark'], normal_style),
                    Spacer(1, 10)
                ]))

                elements.append(Spacer(1, 12))

            # Build the PDF document
            pdf.build(elements)

            return response
        except Exception as err:
            response["error"] = settings.ERROR_MSG["application_error"].format(
                str(err), self.__log.error(self.__exception.get_exception())
            )
        return response


    def __get_assessor_names(self, assessors):
        result = ''
        try:
            user_dict = {}
            active_users = UserDA().get_all_active_users()
            for each in active_users:
                user_dict[each.id] = each.first_name+' '+each.last_name
            values = assessors.split(",")
            for value in values:
                result+=f"{user_dict[int(value)]}, "
            result = result[:-2]
        except:
            pass
        return result

    def __check_is_assessor(self, assessors, user_id):
        result = [0]
        values = assessors.split(",")
        for value in values:
            result.append(int(value))
        if user_id in result:
            return True
        else :
            return False

    def __get_assessor_emails(self, assessors):
        result = []
        try:
            user_dict = {}
            active_users = UserDA().get_all_active_users()
            for each in active_users:
                user_dict[each.id] = each.email
            values = assessors.split(",")
            for value in values:
                result.append(user_dict[int(value)])
        except:
            pass
        return result


    def __validate_date(self, input_date):
        if isinstance(input_date, str):
            input_date = datetime.strptime(input_date, '%Y-%m-%d %H:%M:%S').date()
        elif isinstance(input_date, datetime):
            input_date = input_date.date()

        today = date.today()
        return input_date >= today


    def __get_hours(self, seconds):
        result = '00:00'
        try:
            hours, remaining_seconds = divmod(seconds, 3600)
            minutes = remaining_seconds // 60
            result = "{:02d}:{:02d}".format(hours, minutes)
        except:
            pass
        return result

    def __get_progress(self, assesse_id):
        result = '-/-'
        try:
            total_assessment = AssessmentDA().get_assessment(assesse_id)
            total = total_assessment.count()
            completed = total_assessment.filter(assessment_status=1).count()
            result = f'{completed}/{total}'
        except Exception as err:
            pass
        return result

    def __get_logs(self, assessee_id):
        result = []
        try:
            logs = AssessmentDA().get_assessment_logs(assessee_id)
            for each in logs:
                result.append(each.action)
        except:
            pass
        return result

    def __get_assessor(self, reporting_to):

        exclude_non_tech_leads = [1, 2, 3] #TODO add correct IDs
        lead_ids = UserDA().get_emps_with_role(group_ids="4")
        lead_ids = [x for x in lead_ids if x not in exclude_non_tech_leads]

        assessments = AssessmentDA().get_assessment()
        assessments = assessments[:5] if assessments else []

        assessment_leads = [int(x) for each in assessments for x in each.assessor.split(",")]
        final_lead_ids = [x for x in lead_ids if x not in assessment_leads]

        if len(final_lead_ids) == 1 and len(assessment_leads) > 0:
            assessor1 = final_lead_ids[0]
            assessor2 = random.choice(assessment_leads)
            while assessor2 in (assessor1, reporting_to):
                assessor2 = random.choice(assessment_leads)
            final_ids = [assessor1, assessor2]
        elif len(final_lead_ids)> 1:
            filtered_ids = [x for x in final_lead_ids if x != reporting_to]
            if len(filtered_ids) >= 2:
                final_ids = random.sample(filtered_ids, k=2)
            else:
                final_ids = random.sample([x for x in lead_ids if x not in assessment_leads and x != reporting_to], k=2)
        else:
            final_ids = random.sample([x for x in lead_ids if x not in assessment_leads and x != reporting_to], k=2)

        return ",".join(map(str, final_ids))

    def __is_weekend(self, date):
        return date.weekday() in [5, 6]  # Saturday is 5, Sunday is 6

    def __is_holiday(self, date, holiday_list):
        return date in holiday_list

    def __create_log(self, status, assessee_id=0, assessment_id=0, user_id=0):
        action = None
        try:
            log_dict = {}
            user = UserDA().get_user_by_id(user_id)
            user_name = user.first_name+' '+user.last_name
            current_datetime = datetime.now()
            formatted_datetime = current_datetime.strftime("%d/%m/%y %I:%M %p")
            log_dict['assessee_id'] = assessee_id
            log_dict['assessment_id'] = assessment_id

            if status=='initiated':
                action = log_dict['action'] = settings.ASSESSMENT_LOG[1].format(user_name, formatted_datetime)
            elif status=='update':
                action = log_dict['action'] = settings.ASSESSMENT_LOG[3].format(user_name, formatted_datetime)
            elif status=='cancel':
                action = log_dict['action'] = settings.ASSESSMENT_LOG[4].format(user_name, formatted_datetime)
            elif status=='reschedule':
                action = log_dict['action'] = settings.ASSESSMENT_LOG[2].format(user_name, formatted_datetime)
            if action:AssessmentDA().create_assessment_log(log_dict)
        except Exception as err:
            pass


    def send_induction_email(self, subject, content, to_email, cc_addresses=[], bcc_address=[]):
        mail_dto = {}
        mail_dto["subject"] = subject
        mail_dto["from_address"] = settings.EMAIL_ADDRESS['do_not_reply']['name']
        mail_dto["body"] = content
        mail_dto["to_addresses"] = [to_email]
        mail_dto["cc_addresses"] = cc_addresses
        mail_dto["bcc_address"] = bcc_address
        mail_dto["smtp_username"] = settings.EMAIL_ADDRESS['do_not_reply']['mailID']
        mail_dto["smtp_password"] = settings.EMAIL_ADDRESS['do_not_reply']['password']
        send_email_notification.apply_async(
            [mail_dto, 1], queue=settings.CELERY_QUEUE['mail_sender'])

    def __generate_email_template(self, email_template, context):
        html_email = loader.render_to_string(email_template, context)
        return html_email

    
    def __get_assessor_v1(self, reporting_to, exclude_leads=[]):

        selected_assessors = []
        user_dict = {}
        active_users = UserDA().get_all_active_users()
        for each_user in active_users:
            user_dict[each_user.id] = each_user

        exclude_non_tech_leads = [1, 2, 3] #TODO add correct IDs
        exclude_non_tech_leads.extend(exclude_leads)
        lead_ids = UserDA().get_emps_with_role(group_ids="4")
        lead_ids = [x for x in lead_ids if x not in exclude_non_tech_leads]

        assessments = AssessmentDA().get_assessment()
        assessments = assessments[:5] if assessments else []

        assessment_leads = [int(x) for each in assessments for x in each.assessor.split(",")]
        final_lead_ids = [x for x in lead_ids if x not in assessment_leads]

        if len(final_lead_ids) == 1 and len(assessment_leads) > 0:
            assessor1 = final_lead_ids[0]
            assessor2 = random.choice(assessment_leads)
            while assessor2 in (assessor1, reporting_to):
                assessor2 = random.choice(assessment_leads)
            final_ids = [assessor1, assessor2]
        elif len(final_lead_ids)> 1:
            filtered_ids = [x for x in final_lead_ids if x != reporting_to]
            if len(filtered_ids) >= 2:
                final_ids = random.sample(filtered_ids, k=2)
            else:
                final_ids = random.sample([x for x in lead_ids if x not in assessment_leads and x != reporting_to], k=2)
        else:
            final_ids = random.sample([x for x in lead_ids if x not in assessment_leads and x != reporting_to], k=2)
        
        for each_id in final_ids:
            user_obj = user_dict.get(each_id)
            emp_name = f"{user_obj.first_name} {user_obj.last_name}"
            selected_assessors.append({'id': each_id, 'name': emp_name})
            exclude_leads.append(each_id)

        return selected_assessors, exclude_leads


    
    def get_assessment_lead_ids(self, request, total_count, emp_id):
        response = {"error": None, "assessors": []}
        removed = []
        selected = []
        try:
            lead_id = UserDA().get_lead_id_by_user(emp_id)
            lead_obj = UserDA().get_user_by_id(lead_id)
            lead_name = f"{lead_obj.first_name} {lead_obj.last_name}"
            for each in range(0, total_count):
                if (each+1) == total_count:
                    response['assessors'].append([{'id': lead_id, 'name': lead_name}])
                    continue
                selected, removed = self.__get_assessor_v1(lead_id, removed)
                response['assessors'].append(selected)
        except Exception as err:
                response["error"] = settings.ERROR_MSG["application_error"].format(
                    str(err), self.__log.error(self.__exception.get_exception())
                )
        return response
        