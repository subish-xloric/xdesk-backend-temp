from types import SimpleNamespace
from django.conf import settings

from pTracker.common.utility import Utility
from pTracker.common.exception_handler import ExceptionHandler
from pTracker.common.logs import Logs
from pTracker.dataaccess.ptracker_access.user_da import UserDA
from pTracker.dataaccess.ptracker_access.tax_da import TaxDA
from pTracker.api.finance.notification_biz import NotificationBL
from pTracker.cronjobs.email_sender import send_email_notification

import locale


def new_dto():
    dto = SimpleNamespace()
    return dto

class TaxMailBL():
    
    def __init__(self):
        self.__log = Logs()
        self.__exception = ExceptionHandler()
        self.__utility = Utility()
    
    
    def send_reminder_all_not_completed_tax(self, request, period_id):
        result_dict = {}
        response = {"error": None, "success": False, "message":''}

        try:
            user_id = request.user.id
            
            threshold_value = request.GET.get('threshold_value')
            org_id = request.GET.get('org_id')
            
            if threshold_value not in ['undefined', None]:
                threshold_value = int(threshold_value)
            else:
                threshold_value = 100
            
            claim_declarations = TaxDA().get_claim_declarations_by_emp_id(tax_period_id=period_id)
            user_dict = self.__get_all_active_users_dict(False)
            
            user_ids = list(user_dict.keys())
            
            user_profiles = UserDA().get_all_user_profiles()
            user_profiles = user_profiles.filter(user_id__in = user_ids)
            
            org_user_ids = user_profiles.filter(company_id=org_id).values_list('user_id', flat=True)

            claim_declarations = claim_declarations.filter(user_id__in=org_user_ids)
            
            if claim_declarations:
                for declaration in claim_declarations:

                    claims = TaxDA().get_claims_by_declaration_id(declaration.id)

                    if declaration.user_id in result_dict.keys():
                        result_dict[declaration.user_id]['estimated_amount']+=declaration.amount
                        result_dict[declaration.user_id]['submitted_amount']+=sum(claims.exclude(status="Rejected").values_list('amount', flat=True))
                    else:
                        result_dict[declaration.user_id] = {
                        "emp_code" : user_dict.get(declaration.user_id)[1],
                        "emp_id": declaration.user_id,
                        "estimated_amount": declaration.amount,
                        "submitted_amount":sum(claims.exclude(status="Rejected").values_list('amount', flat=True)),
                        "submitted_percentage":0,
                    }
            
            claim_declarations_users = claim_declarations.values_list('user_id', flat=True)
            claim_declarations_users = set(list(claim_declarations_users))
            tax_batch_users = TaxDA().get_tax_batch_by_period(period_id).filter(user_id__in = org_user_ids)
            tax_batch_users = list(tax_batch_users.values_list('user_id', flat=True))
            
            not_declared_users = list(set(tax_batch_users) - set(claim_declarations_users))
            
            if not_declared_users:
                for not_declared_user in not_declared_users:
                    result_dict[not_declared_user] = {
                        "emp_code" : user_dict.get(not_declared_user)[1],
                        "emp_id": not_declared_user,
                        "estimated_amount": 0,
                        "submitted_amount": 0,
                        "submitted_percentage":0,
                    }
            
            locale.setlocale(locale.LC_MONETARY, 'en_IN')
            
            for key, entry in result_dict.items():
                estimated_amount = entry['estimated_amount']
                submitted_amount = entry['submitted_amount']
                emp_id = entry['emp_id']

                # Avoid division by zero
                if estimated_amount != 0:
                    emp_mail = []
                    submitted_percentage = (submitted_amount / estimated_amount) * 100
                    round_submit_percentage = round(submitted_percentage,2)
                    if round_submit_percentage < 100 and threshold_value > round_submit_percentage:
                        claim_user = UserDA().get_user_data_by_emp_id(emp_id)
                        emp_mail.append(UserDA().get_user_mail_from_user_id(emp_id))
                        
                        # #TODO
                        # emp_mail = []
                        # emp_mail.append('akhil.jose@digitalmesh.com')
                        # #TODO
                        
                        initiator_designation = self.__get_user_job_title(user_id)
                        initiator_name = request.user.first_name + " " + request.user.last_name
                        emp_name = claim_user.first_name + " " + claim_user.last_name
                        email_content_dto = new_dto()
                        email_content_dto.claimed_amount = locale.currency(submitted_amount, grouping=True)[1:]
                        email_content_dto.round_submit_percentage = round_submit_percentage
                        email_content_dto.estimated_amount = locale.currency(estimated_amount, grouping=True)[1:]
                        email_content_dto.initiator_name = initiator_name
                        email_content_dto.initiator_designation = initiator_designation
                        email_content_dto.initiator_email = request.user.email
                        email_content_dto.emp_name = emp_name
                        subject = 'Request for Submission of Missing Tax Deduction Data'
                        email_content_dto.heading = subject
                        email_content_dto.page = 'mail_reminder_missing_tax_deduction.html'
                        email_msg = NotificationBL().generate_email_for_tax_deduction_reminder(email_content_dto)
                        NotificationBL().send_finance_mail(email_msg, emp_name, emp_mail, subject)
                else:
                    emp_mail = []
                    submitted_percentage = 0
                    round_submit_percentage = 0
                    if round_submit_percentage < 100 and threshold_value > round_submit_percentage:
                        claim_user = UserDA().get_user_data_by_emp_id(emp_id)
                        emp_mail.append(UserDA().get_user_mail_from_user_id(emp_id))
                        
                        # #TODO
                        # emp_mail = []
                        # emp_mail.append('akhil.jose@digitalmesh.com')
                        # #TODO
                        
                        initiator_designation = self.__get_user_job_title(user_id)
                        initiator_name = request.user.first_name + " " + request.user.last_name
                        emp_name = claim_user.first_name + " " + claim_user.last_name
                        email_content_dto = new_dto()
                        email_content_dto.claimed_amount = locale.currency(submitted_amount, grouping=True)[1:]
                        email_content_dto.round_submit_percentage = round_submit_percentage
                        email_content_dto.estimated_amount = locale.currency(estimated_amount, grouping=True)[1:]
                        email_content_dto.initiator_name = initiator_name
                        email_content_dto.initiator_designation = initiator_designation
                        email_content_dto.initiator_email = request.user.email
                        email_content_dto.emp_name = emp_name
                        subject = 'Request for Submission of Missing Tax Deduction Data'
                        email_content_dto.heading = subject
                        email_content_dto.page = 'mail_remainder_missing_tax_deduction_not_declared.html'
                        email_msg = NotificationBL().generate_email_for_tax_deduction_reminder(email_content_dto)
                        NotificationBL().send_finance_mail(email_msg, emp_name, emp_mail, subject)

            response['message'] = f'Message delivered to the listed employees successfully'
            response['success'] = True
        except Exception as err:
            response["error"] = settings.ERROR_MSG['application_error'].format(
                str(err), self.__log.error(self.__exception.get_exception())
            )
        return response


    def send_reminder_one_employee_not_completed_tax(self, request, emp_id, tax_period_id):
        result_dict = {}
        response = {"error": None, "success": False, "message":''}

        try:
            user_id = request.user.id
            claim_declarations = TaxDA().get_all_emplyee_declarations(tax_period_id, emp_id)
            user_dict = self.__get_all_active_users_dict(False)
            if claim_declarations:
                for declaration in claim_declarations:

                    claims = TaxDA().get_claims_by_declaration_id(declaration.id)

                    if declaration.user_id in result_dict.keys():
                        result_dict[declaration.user_id]['estimated_amount']+=declaration.amount
                        result_dict[declaration.user_id]['submitted_amount']+=sum(claims.exclude(status="Rejected").values_list('amount', flat=True))
                    else:
                        result_dict[declaration.user_id] = {
                        "emp_code" : user_dict.get(declaration.user_id)[1],
                        "emp_id": declaration.user_id,
                        "estimated_amount": declaration.amount,
                        "submitted_amount":sum(claims.exclude(status="Rejected").values_list('amount', flat=True)),
                        "submitted_percentage":0,
                    }
            else:
                result_dict[emp_id] = {}
                result_dict[emp_id]['emp_code'] = user_dict.get(emp_id)[1]
                result_dict[emp_id]['emp_id'] = emp_id
                result_dict[emp_id]['estimated_amount'] = 0
                result_dict[emp_id]['submitted_amount'] = 0
                result_dict[emp_id]['submitted_percentage'] = 0
                
            if result_dict:
                key, entry = list(result_dict.items())[0]
                estimated_amount = entry['estimated_amount']
                submitted_amount = entry['submitted_amount']
                emp_id = entry['emp_id']

                # Avoid division by zero
                if estimated_amount != 0:
                    emp_mail = []
                    submitted_percentage = (submitted_amount / estimated_amount) * 100
                    round_submit_percentage = round(submitted_percentage,2)
                    if round_submit_percentage < 100:
                        claim_user = UserDA().get_user_data_by_emp_id(emp_id)
                        emp_mail.append(UserDA().get_user_mail_from_user_id(emp_id))
                        
                        # #TODO
                        # emp_mail = []
                        # emp_mail.append('akhil.jose@digitalmesh.com')
                        # #TODO
                        
                        initiator_designation = self.__get_user_job_title(user_id)
                        initiator_name = request.user.first_name + " " + request.user.last_name
                        emp_name = claim_user.first_name + " " + claim_user.last_name
                        email_content_dto = new_dto()
                        locale.setlocale(locale.LC_MONETARY, 'en_IN')
                        email_content_dto.claimed_amount = locale.currency(submitted_amount, grouping=True)[1:]
                        email_content_dto.round_submit_percentage = round_submit_percentage
                        email_content_dto.estimated_amount = locale.currency(estimated_amount, grouping=True)[1:]
                        email_content_dto.initiator_name = initiator_name
                        email_content_dto.initiator_designation = initiator_designation
                        email_content_dto.initiator_email = request.user.email
                        email_content_dto.emp_name = emp_name
                        subject = 'Request for Submission of Missing Tax Deduction Data'
                        email_content_dto.heading = subject
                        email_content_dto.page = 'mail_reminder_missing_tax_deduction.html'
                        email_msg = NotificationBL().generate_email_for_tax_deduction_reminder(email_content_dto)
                        NotificationBL().send_finance_mail(email_msg, emp_name, emp_mail, subject)

                        response['message'] = 'Message sent successful'
                        response['success'] = True
                    else:
                        response['success'] = False
                        response['error'] = 'Employee has claimed the declared amount'
                else:
                    emp_mail = []
                    submitted_percentage = 0
                    round_submit_percentage = 0
                    if round_submit_percentage < 100:
                        claim_user = UserDA().get_user_data_by_emp_id(emp_id)
                        emp_mail.append(UserDA().get_user_mail_from_user_id(emp_id))
                        
                        # #TODO
                        # emp_mail = []
                        # emp_mail.append('akhil.jose@digitalmesh.com')
                        # #TODO
                        
                        initiator_designation = self.__get_user_job_title(user_id)
                        initiator_name = request.user.first_name + " " + request.user.last_name
                        emp_name = claim_user.first_name + " " + claim_user.last_name
                        email_content_dto = new_dto()
                        locale.setlocale(locale.LC_MONETARY, 'en_IN')
                        email_content_dto.claimed_amount = locale.currency(submitted_amount, grouping=True)[1:]
                        email_content_dto.round_submit_percentage = round_submit_percentage
                        email_content_dto.estimated_amount = locale.currency(estimated_amount, grouping=True)[1:]
                        email_content_dto.initiator_name = initiator_name
                        email_content_dto.initiator_designation = initiator_designation
                        email_content_dto.initiator_email = request.user.email
                        email_content_dto.emp_name = emp_name
                        subject = 'Request for Submission of Missing Tax Deduction Data'
                        email_content_dto.heading = subject
                        email_content_dto.page = 'mail_remainder_missing_tax_deduction_not_declared.html'
                        email_msg = NotificationBL().generate_email_for_tax_deduction_reminder(email_content_dto)
                        NotificationBL().send_finance_mail(email_msg, emp_name, emp_mail, subject)

                        response['message'] = 'Message sent successful'
                        response['success'] = True
                    else:
                        response['success'] = False
                        response['error'] = 'Employee has claimed the declared amount'
                        
        except Exception as err:
            response["error"] = settings.ERROR_MSG['application_error'].format(
                str(err), self.__log.error(self.__exception.get_exception())
            )
        return response
    
    
    def __get_all_active_users_dict(self, is_active=True):
        user_dict = {}
        users = UserDA().get_all_users()
        for each in users:
            if is_active and not each.is_active:
                continue
            user_dict[each.id] = [each.first_name+' '+each.last_name, each.username]
        return user_dict
    
    
    def __get_user_job_title(self, user_id):
        user_profile = UserDA().get_user_profile_by_id(user_id)
        job_title = UserDA().get_job_title_by_id(user_profile.job_title)
        job_title = job_title.job_title
        return job_title