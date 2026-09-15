
import uuid
import json
from datetime import datetime
from types import SimpleNamespace

from django.http import HttpResponse
from django.conf import settings
from django.db import  transaction


from pTracker.common.utility import Utility
from pTracker.common.exception_handler import ExceptionHandler
from pTracker.common.logs import Logs
from pTracker.common.file_manager import FileManager

from pTracker.dataaccess.ptracker_access.user_da import UserDA
from pTracker.dataaccess.ptracker_access.finance_da import FinanaceDA
from pTracker.dataaccess.ptracker_access.tax_da import TaxDA

from pTracker.api.finance.notification_biz import NotificationBL

from pTracker.settings import constants
from pTracker.cronjobs.email_sender import send_email_notification

from cryptography.fernet import Fernet
from django.db.models import Q


import os
import re


def new_dto():
    dto = SimpleNamespace()
    return dto

class TaxBL():
    def __init__(self):
        self.__log = Logs()
        self.__exception = ExceptionHandler()
        self.__utility = Utility()


    def get_or_create_chat(self, request):
        response = {"success": ''}

        try:
            user_id = request.user.id
            role_id, name = UserDA().get_user_role_by_id(user_id)

            request_data = request.data
            emp_id = int(request_data.get('emp_id'))

            if user_id == emp_id:
                response["error"] = settings.ERROR_MSG.get("access_denied")
                response["status"] = 403
                return response

            is_chat_exist = TaxDA().get_chat_from_users_id(user_id, emp_id)

            if is_chat_exist:
                response['success'] = True
                response['chat_id'] = is_chat_exist.chat_id
                return response

            if not is_chat_exist and role_id != 3:
                response["error"] = settings.ERROR_MSG.get("access_denied")
                response["status"] = 403
                return response

            with transaction.atomic():

                is_chat_created = TaxDA().create_chat_data(user_id, emp_id)

                if not is_chat_created:
                    response["error"] = settings.ERROR_MSG.get("access_denied")
                    response["status"] = 403
                    return response

                response['success'] = True
                response['chat_id'] = is_chat_created.chat_id

        except Exception as err:
            response["error"] = settings.ERROR_MSG['application_error'].format(
                str(err), self.__log.error(self.__exception.get_exception())
            )
        return response


    def get_chat_history(self, request, chat_id, tax_period_id):
        response = {"messages":[]}

        try:
            user_id = request.user.id
            is_permitted_to_view_chat = TaxDA().is_permitted_to_view_chat(chat_id, user_id)
            if not is_permitted_to_view_chat:
                response["error"] = settings.ERROR_MSG.get("access_denied")
                response["status"] = 403
                return response

            active_users = UserDA().get_all_active_users()
            users = { user.id : {"name": user.first_name + " " + user.last_name} for user in active_users }

            chat = TaxDA().get_chat_from_chat_id(chat_id)

            messages = TaxDA().get_chats_from_chat_id_and_tax_period_id(chat_id, tax_period_id).order_by('created_on')

            for message in messages:
                message_data = {}
                message_data['content'] = message.content
                message_data['sent_by'] = message.created_by
                message_data['sender_name'] = users[message.created_by]['name']
                message_data['created_at'] = message.created_on.strftime("on %A %d %B at %H:%M %p")
                response["messages"].append(message_data)
                del message_data

            if chat.user_1 == user_id:
                other_user = chat.user_2
            else:
                other_user = chat.user_1

            other_user_name = users[other_user]['name']

            response['current_user'] = user_id
            response['other_user_name'] = other_user_name
            response['employee_id'] = other_user
            response['success'] = True

        except Exception as err:
            response["error"] = settings.ERROR_MSG['application_error'].format(
                str(err), self.__log.error(self.__exception.get_exception())
            )
        return response


    def approve_claim(self, request, claim_id):
        response = {"approved":False}
        is_completed = False

        try:
            user_id = request.user.id
            is_permitted = self.__utility.is_permitted(user_id, 'can_approve_claim')
            if not is_permitted:
                response["error"] = settings.ERROR_MSG.get("access_denied")
                response["status"] = 403
                return response

            request_data = request.data
            status = request_data.get('status')
            comment = request_data.get('comment')
            is_receipt = True

            claim = TaxDA().get_claim_by_id(claim_id)
            claim_user = UserDA().get_user_data_by_emp_id(claim.user_id)

            hra_details = TaxDA().get_hra_details_from_claim_id(claim_id)
            if hra_details:
                is_receipt = True if hra_details.proof_type == 'Receipt' else False

            data = {"status":status, "reject_reason":comment}

            with transaction.atomic():
                TaxDA().update_claim(data, claim_id)

                # if not is_updated:
                #     response['success'] = False
                #     response['error'] = 'Claim Data is not updated'
                #     return response

                emp_mail = []
                emp_mail.append(UserDA().get_user_mail_from_user_id(claim.user_id))

                # #TODO
                # emp_mail = []
                # emp_mail.append('akhil.jose@mydomain.com')
                # #TODO

                initiator_designation = self.__get_user_job_title(user_id)

                initiator_name = request.user.first_name + " " + request.user.last_name

                emp_name = claim_user.first_name + " " + claim_user.last_name

                tax_period = TaxDA().get_tax_period_from_tax_period_id(claim.tax_period_id)

                deadline_date = tax_period.claim_entry_last_date.strftime("%d/%m/%Y")

                email_content_dto = new_dto()
                email_content_dto.is_receipt = is_receipt
                email_content_dto.comment = comment
                email_content_dto.initiator_name = initiator_name
                email_content_dto.initiator_designation = initiator_designation
                email_content_dto.initiator_email = request.user.email
                email_content_dto.emp_name = emp_name
                email_content_dto.submitted_date = claim.created_on.strftime("%d/%m/%Y")
                email_content_dto.claim_amount = claim.amount
                email_content_dto.section, email_content_dto.category = TaxDA().get_section_and_category_from_cat_id(claim.cat_id)

                if status == 'Approved':
                    subject = 'Approval of Income Tax Assessment Claim'
                    email_content_dto.heading = subject
                    email_content_dto.comment = comment
                    email_content_dto.page = 'claim_approval_mail.html'
                    email_content_dto.deadline_date = deadline_date
                    response['message'] = 'Claim Approved Successfully'
                else:
                    subject = 'Rejection of Income Tax Assessment Claim'
                    email_content_dto.heading = subject
                    email_content_dto.comment = comment
                    email_content_dto.page = 'claim_rejection_mail.html'
                    email_content_dto.deadline_date = deadline_date
                    response['message'] = 'Claim Rejected'

                email_msg = NotificationBL().generate_email_for_claim_approval_rejection(email_content_dto)

                NotificationBL().send_finance_mail(email_msg, emp_name, emp_mail, subject)

                response['success'] = True

                is_completed = True

            if not is_completed:
                response['success'] = False
                response['error'] = 'Process Incomplete'

        except Exception as err:
            response["error"] = settings.ERROR_MSG['application_error'].format(
                str(err), self.__log.error(self.__exception.get_exception())
            )
        return response


    def get_tax_period_data(self, request, tax_period_id):
        response = {"tax_period_data": {}, 'user_data': [], 'eligible_employees': []}
        eligible_employees = {}
        total_count = 0

        try:
            tax_batch_user_ids = list()
            user_id = request.user.id

            is_permitted = self.__utility.is_permitted(user_id, 'can_view_assessment_period')
            if not is_permitted:
                response["error"] = settings.ERROR_MSG.get("access_denied")
                response["status"] = 403
                return response

            if tax_period_id in (0, '0', None):
                current_date = datetime.now()
                current_fyd = FinanaceDA().get_financial_year_by_date(current_date)
                tax_period = TaxDA().get_assessment_period_by_fin_year_id(current_fyd.financial_year_id)
            else:
                tax_period = TaxDA().get_tax_period_from_tax_period_id(tax_period_id)

            # tax_period = TaxDA().get_tax_period_from_tax_period_id(tax_period_id)
            tax_period_id = tax_period.id

            tax_batch_users = TaxDA().get_tax_batch_by_period(tax_period.id)
            active_users = self.__get_all_active_users_dict(False)

            user_ids = list(active_users.keys())

            user_profiles = UserDA().get_all_user_profiles()
            user_profiles = user_profiles.filter(user_id__in = user_ids)

            user_org_ids = { profile.user_id : profile.company_id for profile in user_profiles }

            for emp_id, emp_name in active_users.items():
                eligible_employees[emp_id] = {'id': emp_id, 'name': emp_name[0], 'org_id': user_org_ids[emp_id] if emp_id in user_org_ids.keys() else 0}

            claims_data = TaxDA().get_all_claims_by_period_id(tax_period_id, status='Under Review')
            claims_count_dict = {}
            for each in claims_data:
                if each.user_id in claims_count_dict.keys():
                    claims_count_dict[each.user_id] += 1
                else:
                    claims_count_dict[each.user_id] = 1

            all_declarations = TaxDA().get_all_declarations_from_period_id(tax_period_id)
            is_declared_data = { declaration.user_id: True for declaration in all_declarations }

            for tax_batch in tax_batch_users:
                emp_name = active_users.get(tax_batch.user_id, [])[0]
                emp_code = active_users.get(tax_batch.user_id, [])[1]
                emp_firstname = active_users.get(tax_batch.user_id, [])[2]
                approval_awating = claims_data.count()
                eligible_employees.pop(tax_batch.user_id, None)
                count = claims_count_dict.get(tax_batch.user_id) if claims_count_dict.get(tax_batch.user_id) else 0
                is_declared = is_declared_data.get(tax_batch.user_id, False)
                temp_dict = {
                    'id': tax_batch.id,
                    'user_id':tax_batch.user_id,
                    'emp_name':emp_name,
                    'emp_code':emp_code,
                    'emp_firstname':emp_firstname,
                    'tax_period_id':tax_batch.tax_period_id, #zzzzzzz
                    'tax_plan':settings.REGIME_TYPE_MAPPING.get(tax_batch.regime_type, "-"),
                    'last_date_of_declaration':tax_batch.last_date_of_declaration.strftime("%d/%m/%Y"),
                    'last_date_of_claim_entry': tax_batch.last_date_of_claim_entry.strftime("%d/%m/%Y"),
                    'approval_awaiting_count': count,
                    'regime_type': tax_batch.regime_type,
                    'is_declared': True if is_declared else False,
                    'org_id': user_org_ids[tax_batch.user_id] if tax_batch.user_id in user_org_ids.keys() else 0,
                }
                tax_batch_user_ids.append(tax_batch.user_id)
                response["user_data"].append(temp_dict)
                response['eligible_employees']=list(eligible_employees.values())
                total_count+=count

            tax_period_data = {
                'id': tax_period.id,
                'fin_year_id': tax_period.fin_year_id,
                'claim_entry_last_date': tax_period.claim_entry_last_date.strftime("%d/%m/%Y"),
                'claim_declaration_last_date': tax_period.claim_declaration_last_date.strftime("%d/%m/%Y")
                }

            response["tax_period_data"] = tax_period_data
            response['total_count'] = total_count


        except Exception as err:
            response["error"] = settings.ERROR_MSG['application_error'].format(
                str(err), self.__log.error(self.__exception.get_exception())
            )
        return response


    def get_tax_periods(self, request):
        response = {"tax_periods": {}}
        data_list = []
        try:
            user_id = request.user.id
            # is_permitted = self.__utility.is_permitted(user_id, 'can_view_assessment_period')
            # if not is_permitted:
            #     response["error"] = settings.ERROR_MSG.get("access_denied")
            #     response["status"] = 403
            #     return response

            user_org = UserDA().get_user_organization(user_id)

            tax_periods = TaxDA().get_all_tax_periods()
            financial_years = FinanaceDA().get_all_financial_years()
            data_list = []
            current_fin_year = FinanaceDA().get_current_financial_year()
            current_fin_year_id = current_fin_year.financial_year_id
            current_financial_year = current_fin_year.description

            fin_data = financial_years.order_by('-start_date')[:5]
            fin_year_data =  [ {'id': financial_year.financial_year_id, 'desc': financial_year.description }\
                            for financial_year in fin_data ]
            fin_year_data.reverse()

            organization_data = settings.ORGANIZATION
            organization_data = [ key for key, value in organization_data.items() ]

            for tax_period in list(tax_periods):
                tax_batch_count = TaxDA().get_tax_batch_by_period(tax_period_id=tax_period.id)
                fin_year = financial_years.filter(financial_year_id=tax_period.fin_year_id).last()

                if fin_year:
                    data_list.append({
                        'id': tax_period.id,
                        'fin_year_id': tax_period.fin_year_id,
                        'financial_desc': fin_year.description,
                        'claim_declaration_last_date': tax_period.claim_declaration_last_date.strftime('%d/%m/%Y'),
                        'claim_entry_last_date': tax_period.claim_entry_last_date.strftime('%d/%m/%Y'),
                        'tax_batch_count': len(tax_batch_count)
                    })

            response['current_month_year_name'] = datetime.now().strftime("%B %Y")
            response['tax_periods'] = data_list
            response['fin_year_data'] = fin_year_data
            response['current_fin_year_id'] = current_fin_year_id
            response['current_fin_year_desc'] = current_financial_year
            response['organization_data'] = organization_data
            response['user_org'] = user_org
            response['success'] = True
            response['message'] = 'Listed Successfully'

        except Exception as err:
            response["error"] = settings.ERROR_MSG['application_error'].format(
                str(err), self.__log.error(self.__exception.get_exception())
            )
        return response


    def get_dropdown_params_for_initiate_assessment(self, request):
        response = {
            "financial_years": [],
            "categories": [],
            "current_financial_year": {},
            'employee_list': [],
            'assessment_years': [],
            'not_initiated_list': []
        }
        try:
            user_id = request.user.id
            role_id, name = UserDA().get_user_role_by_id(user_id)

            if role_id == 3:
                is_manager = True
            else:
                is_manager = False

            current_fyd = FinanaceDA().get_financial_year_by_date(datetime.now())
            assessment_years = FinanaceDA().get_all_financial_years()


            for financial_year in assessment_years:
                financial_year_data = {'id':financial_year.financial_year_id, 'value':financial_year.description}
                response["financial_years"].append(financial_year_data)

            categories = TaxDA().get_all_categories()
            for category in categories:
                response["categories"].append(
                    {
                    'id': category.id,
                    'name': category.name,
                    'parent_id': category.parent_id,
                    'description': category.description,
                    'maximum_amount': category.maximum_allowed
                })

            users = UserDA().get_all_active_users().order_by('username')
            user_ids = users.values_list('id', flat=True)

            user_profiles = UserDA().get_all_user_profiles()
            user_profiles = user_profiles.filter(user_id__in = user_ids)

            user_org_ids = { profile.user_id : profile.company_id for profile in user_profiles }
            for user in users:
                emp_name = user.first_name+' '+user.last_name
                response["employee_list"].append({'id': user.id, 'name': emp_name, 'emp_code': user.username, 'org_id': user_org_ids[user.id] if user.id in user_org_ids.keys() else 0})

            response["employee_list"] = sorted(response["employee_list"], key=lambda x: int(x['emp_code']))
            response['current_financial_year'] = {'id': current_fyd.financial_year_id, 'name': current_fyd.description}

            for assessment_year in assessment_years:
                tax_period = TaxDA().get_tax_period_from_financial_year_id(assessment_year.financial_year_id)
                if tax_period is not None:
                    temp_dict = {}
                    temp_dict['id'] = assessment_year.financial_year_id
                    temp_dict['tax_period_id'] = tax_period.id
                    temp_dict['claim_declaration_last_date'] = tax_period.claim_declaration_last_date.strftime('%d/%m/%Y')
                    temp_dict['claim_entry_last_date'] = tax_period.claim_entry_last_date.strftime('%d/%m/%Y')
                    temp_dict['name'] = assessment_year.description

                    tax_batches = TaxDA().get_all_tax_batches_from_period_id(tax_period.id)
                    dm_batch = tax_batches.filter(org_id=2)
                    em_batch = tax_batches.filter(org_id=3)

                    temp_dict['dm_initiated'] = True if dm_batch else False
                    temp_dict['em_initiated'] = True if em_batch else False

                    response["assessment_years"].append(temp_dict)
                    del temp_dict
                else:
                    response['not_initiated_list'].append(assessment_year.description)
            response['is_manager'] = is_manager

            active_users = UserDA().get_all_active_users()
            users = { user.id : {"firstname": user.first_name, "emp_code": user.username} for user in active_users }
            current_user = users[user_id]
            filename_original = f"{current_user['emp_code']}_{current_user['firstname']}_12BB_original.xlsx"
            filename_estimate = f"{current_user['emp_code']}_{current_user['firstname']}_12BB_estimate.xlsx"
            filename_original_tc = f"{current_user['emp_code']}_{current_user['firstname']}_tax_computation_original.pdf"
            filename_estimate_tc = f"{current_user['emp_code']}_{current_user['firstname']}_tax_computation_estimate.pdf"

            response['filename_original'] = filename_original
            response['filename_estimate'] = filename_estimate
            response['filename_original_tc'] = filename_original_tc
            response['filename_estimate_tc'] = filename_estimate_tc

        except Exception as err:
            response["error"] = settings.ERROR_MSG['application_error'].format(
                str(err), self.__log.error(self.__exception.get_exception())
            )
        return response


    def initiate_claims_forms(self, request):
        response = {"error": None, "success": False}
        data = {}
        emp_mail_list = list()
        try:
            user_id = request.user.id
            role_id, name = UserDA().get_user_role_by_id(user_id)
            is_permitted = self.__utility.is_permitted(user_id, 'can_add_assessment_period')
            if not is_permitted:
                response["error"] = settings.ERROR_MSG.get('access_denied')
                response['status'] = 403
                return response

            request_data = request.data
            financial_year_id = request_data.get('fin_year_id')
            claim_declaration_last_date = request_data.get('claim_declaration_last_date')
            claim_entry_last_date = request_data.get('claim_entry_last_date')

            current_tax_period_initiated = request_data.get('current_tax_period_initiated')

            try:
                is_declaration_date_valid = datetime.strptime(claim_declaration_last_date, "%Y-%m-%d")
                is_entry_date_valid = datetime.strptime(claim_entry_last_date, "%Y-%m-%d")
            except Exception as e:
                response['success'] = False
                response['error'] = 'Date Format Entered Invalid'
                return response
            # tax_period_id = TaxDA().get_tax_period_from_financial_year_id(financial_year_id)

            tax_data = request_data.getlist('tax_data')
            if not tax_data:
                response['success'] = False
                response['error'] = 'Please Select an Employee to Initate Decaration Form'
                return response
            for each in tax_data:
                each = json.loads(each)

            is_fyi_valid = self.__is_valid_financial_year(financial_year_id)
            if not is_fyi_valid:
                response['success'] = False
                response['error'] = 'Invalid Financial Year'
                return response

            is_date_valid = self.__validate_date(claim_declaration_last_date)
            if not is_date_valid:
                response['success'] = False
                response['error'] = 'Invalid Claim Declaration Deadline'
                return response

            is_date_valid = self.__validate_date(claim_entry_last_date)
            if not is_date_valid:
                response['success'] = False
                response['error'] = 'Invalid Claim Entry Deadline'
                return response

            is_duplicate_entry = self.__check_duplicate_entry(financial_year_id)
            # if is_duplicate_entry:
            #     response['success'] = False
            #     response['error'] = 'Assessment for this period is already initiated.'
            #     return response

            users = UserDA().get_all_active_users().order_by('username')
            user_ids = users.values_list('id', flat=True)

            user_profiles = UserDA().get_all_user_profiles()
            user_profiles = user_profiles.filter(user_id__in = user_ids)

            user_org_ids = { profile.user_id : profile.company_id for profile in user_profiles }

            with transaction.atomic():
                data = {'fin_year_id': financial_year_id, 'claim_declaration_last_date':claim_declaration_last_date,
                        'claim_entry_last_date': claim_entry_last_date, 'created_by':user_id}


                if current_tax_period_initiated in [True, 'true', 'True']:
                    is_created = TaxDA().get_tax_period_from_financial_year_id(financial_year_id)
                else:
                    is_created = TaxDA().create_tax_period_data(data)

                if not is_created:
                    response['success'] = False
                    response['message'] = 'IT Assessment Initiation Unsuccessful.'
                    return response

                tax_period_id = is_created.id

                user_ids = list()
                user_ids = [json.loads(data).get('emp_id') for data in tax_data]

                data_dict = json.loads(tax_data[0])
                last_date_of_declaration = data_dict['last_date_of_declaration']
                last_date_of_declaration= datetime.strptime(last_date_of_declaration, "%Y-%m-%d")
                last_date_of_declaration = self.convert_date_format(last_date_of_declaration)
                bulk_data = {json.loads(user_data).get('emp_id'): {'user_id': json.loads(user_data).get('emp_id'), 'last_date_of_declaration': json.loads(user_data).get('last_date_of_declaration'), \
                    'last_date_of_claim_entry': json.loads(user_data).get('last_date_of_claim_entry'), 'tax_period_id': is_created.id, 'regime_type': 0, 'created_by': request.user.id, \
                    'org_id': user_org_ids[int(json.loads(user_data).get('emp_id'))] if int(json.loads(user_data).get('emp_id')) in list(user_org_ids.keys()) else 0} for user_data in tax_data }

                add_tax_batch = TaxDA().bulk_create_tax_batch(bulk_data)

                add_tds = self.create_tds_data(tax_period_id, user_ids, user_id)

                emp_mail_list = UserDA().get_user_mails_from_user_ids(user_ids)
                emp_job_title = self.__get_user_job_title(user_id)
                comment = ''
                emp_name = request.user.first_name + " " + request.user.last_name
                subject = 'Important Notice: Commencement of Income Tax Assessment Process'

                email_content_dto = new_dto()
                email_content_dto.comment = comment
                email_content_dto.heading = 'Important Notice: Commencement of Income Tax Assessment Process'
                email_content_dto.emp_name = emp_name
                email_content_dto.last_date_of_declaration = last_date_of_declaration
                email_content_dto.emp_designation = emp_job_title
                email_content_dto.emp_email = request.user.email
                email_msg = NotificationBL().generate_initiate_email_messages(email_content_dto)

                #TODO
                #emp_mail_list = ['subish@mydomain.com']
                #TODO

                NotificationBL().send_finance_mail(email_msg, emp_name, emp_mail_list, subject)

                response['success'] = True
                response['message'] = 'IT Assessment Initiated Successfully'

        except Exception as err:
            response["error"] = settings.ERROR_MSG["application_error"].format(
                str(err), self.__log.error(self.__exception.get_exception())
            )
        return response


    def delete_tax_period(self, request):
        response = {}
        try:
            user_id = request.user.id
            role_id, name = UserDA().get_user_role_by_id(user_id)
            is_permitted = self.__utility.is_permitted(user_id, 'can_delete_assessment_period')
            if not is_permitted:
                response["error"] = settings.ERROR_MSG.get('access_denied')
                response['status'] = 403
                return response

            request_data = request.data
            period_id = request_data.get('period_id')

            fin_year_id = TaxDA().get_fin_year_id_from_tax_period_id(period_id)

            is_declared = TaxDA().get_claim_declarations_under_tax_period_id(period_id)
            if is_declared:
                response['success'] = False
                response['error'] = 'Deletion unsuccessful, Some claim declarations have been created by users'
                return response

            is_deleted_tax_period = TaxDA().delete_tax_period(period_id)
            if not is_deleted_tax_period:
                response['success'] = False
                response['error'] = 'Assessment Period Deletion Unsuccessful'
                return response

            is_deleted_tax_batch = TaxDA().delete_tax_batches_from_tax_period_id(period_id)
            if not is_deleted_tax_batch:
                response['success'] = False
                response['error'] = 'Assessment Period Deletion Unsuccessful'
                return response

            is_deleted_tds = TaxDA().delete_tds_by_fin_year_id(fin_year_id)
            if not is_deleted_tds:
                response['success'] = False
                response['error'] = 'Assessment Period Deletion Unsuccessful'
                return response


            response['message'] = 'Assessment Period Deleted Successfully'
            response['success'] = True

        except Exception as err:
            response["error"] = settings.ERROR_MSG['application_error'].format(
                str(err), self.__log.error(self.__exception.get_exception())
            )
        return response


    def add_tax_batch(self, request, is_edit):
        response = {}
        try:
            user_id = request.user.id
            role_id, name = UserDA().get_user_role_by_id(user_id)
            is_permitted = self.__utility.is_permitted(user_id, 'can_add_employee_to_assessment_period')
            if not is_permitted:
                response["error"] = settings.ERROR_MSG.get('access_denied')
                response['status'] = 403
                return response

            request_data = request.data

            tax_batch_user_ids = request_data.get('user_id') #zzzzzzz
            tax_period_id = request_data.get('tax_period_id')
            last_date_of_declaration = request_data.get('last_date_of_declaration')
            last_date_of_claim_entry = request_data.get('last_date_of_claim_entry')

            try:
                is_declaration_date_valid = datetime.strptime(last_date_of_declaration, "%Y-%m-%d")
                is_entry_date_valid = datetime.strptime(last_date_of_claim_entry, "%Y-%m-%d")
            except Exception as e:
                response['success'] = False
                response['error'] = 'Date Format Entered Invalid'
                return response

            active_users = self.__get_all_active_users_dict(True)

            user_ids = list(active_users.keys())

            user_profiles = UserDA().get_all_user_profiles()
            user_profiles = user_profiles.filter(user_id__in = user_ids)

            user_org_ids = { profile.user_id : profile.company_id for profile in user_profiles }

            with transaction.atomic():
                tax_batch_data = { 'tax_period_id': tax_period_id, 'regime_type':0,\
                            'created_by':request.user.id, 'last_date_of_declaration':last_date_of_declaration, \
                            'last_date_of_claim_entry':last_date_of_claim_entry }


                #is_tds_created = self.create_tds_data(tax_period_id, tax_batch_user_ids, user_id)

                # if not is_tds_created:
                #     response['success'] = False
                #     response['error'] = 'Update Unsuccessful'
                #     return response

                if is_edit:
                    tax_batch_data = { 'tax_period_id': tax_period_id,\
                            'created_by':request.user.id, 'last_date_of_declaration':last_date_of_declaration, \
                            'last_date_of_claim_entry':last_date_of_claim_entry }
                    is_created = TaxDA().update_tax_batch(is_edit, tax_batch_data)
                    response['message'] = 'Updated Successfully'
                else:
                    is_tds_created = self.create_tds_data(tax_period_id, tax_batch_user_ids, user_id)
                    response['message'] = 'Added Successfully'
                    for each in tax_batch_user_ids:
                        tax_batch_data['user_id'] = each
                        tax_batch_data['org_id'] = user_org_ids[each] if each in user_org_ids.keys() else 0
                        is_created = TaxDA().create_or_update_tax_bacth(tax_batch_data)

                        claim_user = UserDA().get_user_data_by_emp_id(each)

                        emp_mail = []
                        emp_mail.append(UserDA().get_user_mail_from_user_id(each))
                        subject = 'Important Notice: Commencement of Income Tax Assessment Process'

                        initiator_designation = self.__get_user_job_title(user_id)
                        initiator_name = request.user.first_name + " " + request.user.last_name
                        emp_name = claim_user.first_name + " " + claim_user.last_name
                        email_content_dto = new_dto()
                        email_content_dto.heading = subject
                        email_content_dto.emp_name = emp_name
                        email_content_dto.initiator_name = initiator_name
                        email_content_dto.last_date_of_declaration = last_date_of_declaration
                        email_content_dto.emp_designation = initiator_designation
                        email_content_dto.emp_email = request.user.email

                        email_msg = NotificationBL().generate_initiate_employee_email_messages(email_content_dto)
                        emp_mail = 'subish@mydomain.com' #TODO delete this
                        NotificationBL().send_finance_mail(email_msg, emp_name, emp_mail, subject)

                if not is_created:
                    response['success'] = False
                    response['error'] = 'Process Unsuccessful'
                    return response
                response['success'] = True


        except Exception as err:
            response["error"] = settings.ERROR_MSG['application_error'].format(
                str(err), self.__log.error(self.__exception.get_exception())
            )
        return response



    def create_tds_data(self, tax_period_id, tax_batch_user_ids, user_id):
        fin_year_id = TaxDA().get_fin_year_id_from_tax_period_id(tax_period_id)
        financial_year = FinanaceDA().get_financial_year_by_id(fin_year_id)
        month_order_list = settings.FIN_YEAR_MONTH_ORDER_LIST

        years_in_fin_year = self.get_years_in_a_financial_year(financial_year)
        last_year_months = month_order_list[:9]

        tds_data = []
        for each in tax_batch_user_ids:
            for month in month_order_list:
                temp_dict = {}
                temp_dict['fin_year_id'] = fin_year_id
                temp_dict['month_id'] = month
                temp_dict['year'] = years_in_fin_year[0] if month in last_year_months else years_in_fin_year[1]
                temp_dict['user_id'] = each
                temp_dict['last_updated_by'] = user_id
                tds_data.append(temp_dict)
                del temp_dict

        is_tds_created = TaxDA().bulk_create_tds_data(tds_data)
        return is_tds_created



    def delete_tax_batch(self, request):
        response = {}
        try:
            user_id = request.user.id
            role_id, name = UserDA().get_user_role_by_id(user_id)
            is_permitted = self.__utility.is_permitted(user_id, 'can_delete_employee_from_assessment_period')
            if not is_permitted:
                response["error"] = settings.ERROR_MSG.get('access_denied')
                response['status'] = 403
                return response

            request_data = request.data

            tax_batch_id = request_data.get('tax_batch_id')

            is_tax_batch_valid = self.__validate_tax_batch(tax_batch_id)

            tax_period_id = is_tax_batch_valid.tax_period_id
            tax_batch_user = is_tax_batch_valid.user_id

            fin_year_id = TaxDA().get_fin_year_id_from_tax_period_id(tax_period_id)

            if not is_tax_batch_valid:
                response['success'] = False
                response['error'] = 'Tax Batch Delete Failed'
                return response

            is_claim_declared = TaxDA().get_declaration_by_period_and_user(is_tax_batch_valid.tax_period_id, is_tax_batch_valid.user_id)

            if is_claim_declared:
                response['success'] = False
                response['error'] = 'Deletion Unsuccessful, User has already made some claim declarations.'
                return response

            is_deleted = TaxDA().delete_tax_batch_data(tax_batch_id)

            if not is_deleted:
                response['success'] = False
                response['error'] = 'Tax Batch Delete Failed'
                return response

            is_tds_deleted = TaxDA().delete_individual_tds_by_fin_year_id(tax_batch_user, fin_year_id)
            if not is_tds_deleted:
                response['success'] = False
                response['error'] = 'Assessment Period Deletion Unsuccessful'
                return response

            response['message'] = 'Tax Batch Deleted Successfully'
            response['success'] = True

            return response

        except Exception as err:
            response["error"] = settings.ERROR_MSG['application_error'].format(
                str(err), self.__log.error(self.__exception.get_exception())
            )
        return response



    def update_claims_forms(self, request):
        response = {"error": None, "success": False}
        data = {}
        emp_mail_list = list()
        try:
            user_id = request.user.id
            role_id, name = UserDA().get_user_role_by_id(user_id)
            is_permitted = self.__utility.is_permitted(user_id, 'can_add_assessment_period')
            if not is_permitted:
                response["error"] = settings.ERROR_MSG.get('access_denied')
                response['status'] = 403
                return response

            request_data = request.data
            financial_year_id = request_data.get('fin_year_id')
            claim_declaration_last_date = request_data.get('claim_declaration_last_date')
            claim_entry_last_date = request_data.get('claim_entry_last_date')
            tax_period_id = TaxDA().get_tax_period_from_financial_year_id(financial_year_id).id
            # tax_period_id = request_data.get('tax_period_id')

            tax_data = request_data.getlist('tax_data')

            try:
                is_declaration_date_valid = datetime.strptime(claim_declaration_last_date, "%Y-%m-%d")
                is_entry_date_valid = datetime.strptime(claim_entry_last_date, "%Y-%m-%d")
            except Exception as e:
                response['success'] = False
                response['error'] = 'Date Format Entered Invalid'
                return response

            is_fyi_valid = self.__is_valid_financial_year(financial_year_id)
            if not is_fyi_valid:
                response['success'] = False
                response['error'] = 'Invalid Financial Year Id'
                return response

            is_date_valid = self.__validate_date(claim_declaration_last_date)
            if not is_date_valid:
                response['success'] = False
                response['error'] = 'Invalid Claim Declaration Deadline'
                return response


            is_date_valid = self.__validate_date(claim_entry_last_date)
            if not is_date_valid:
                response['success'] = False
                response['error'] = 'Invalid Claim Entry Deadline'
                return response


            tax_period = self.__validate_tax_period(financial_year_id)
            if not tax_period:
                response['success'] = False
                response['error'] = "Assessment Period Doesn't Exist"
                return response

            tax_batch_of_period = TaxDA().get_all_tax_batches_from_period_id(tax_period_id)

            tax_batch_data = []

            for tax_batch in tax_batch_of_period:
                temp_dict = {}
                if datetime.strptime(claim_entry_last_date, "%Y-%m-%d") > datetime.strptime(tax_batch.last_date_of_claim_entry.strftime("%Y-%m-%d"), "%Y-%m-%d"):
                    temp_dict['last_date_of_claim_entry'] = claim_entry_last_date
                    claim_entry_flag = True
                if datetime.strptime(claim_declaration_last_date, "%Y-%m-%d") > datetime.strptime(tax_batch.last_date_of_declaration.strftime("%Y-%m-%d"), "%Y-%m-%d"):
                    temp_dict['last_date_of_declaration'] = claim_declaration_last_date
                    claim_declaration_flag = True
                temp_dict['id'] = tax_batch.id
                tax_batch_data.append(temp_dict)
                del temp_dict



            with transaction.atomic():
                data = {'claim_declaration_last_date':claim_declaration_last_date,
                        'claim_entry_last_date': claim_entry_last_date}

                is_period_updated = TaxDA().edit_tax_period_data(tax_period_id, data)
                is_batch_updated = TaxDA().bulk_update_tax_batch_data(tax_batch_data)

                if not is_period_updated or not is_batch_updated:
                    response['success'] = False
                    response['error'] = 'Update Unsuccessful'
                    return response

                response['success'] = True
                response['message'] = 'Updated Successfully'


        except Exception as err:
            response["error"] = settings.ERROR_MSG["application_error"].format(
                str(err), self.__log.error(self.__exception.get_exception())
            )
        return response

    def create_declaration(self, request):
        response = {"error": None, "success": False}
        try:
            user_id = request.user.id
            request_data = request.data
            financial_year_id = request_data.get('financial_year_id', 0)
            cat_id = request_data.get('cat_id')
            amount = request_data.get('amount')
            amount = amount.strip()
            regime_type = request_data.get('regime_type')

            if not self.__is_valid_financial_year(financial_year_id):
                response['error'] = 'Invalid financial year identified.'
                return response

            is_amount_valid = self.is_amount_valid(amount)
            if not is_amount_valid:
                response['error'] = 'Invalid amount identified, Please try again'
                return response

            if not float(amount) > 0:
                response['error'] = f'Invalid amount identified, Please try again'
                return response

            assessment_period = TaxDA().get_assessment_period_by_fin_year_id(financial_year_id)
            if not assessment_period:
                response['error'] = 'Invalid assessment period identified.'
                return response

            tax_batch = TaxDA().get_tax_batch_by_period(tax_period_id=assessment_period.id, user_id=user_id)
            if  not tax_batch:
                response['error'] = 'Invalid user identified. Please verify and try again.'
                return response

            tax_batch = tax_batch[0]
            if tax_batch.last_date_of_declaration < datetime.now().date():
                response['error'] = 'You are unable to add new declarations as the declaration deadline has expired. Please contact the accounting department for assistance.'
                return response

            claim_declarations = TaxDA().get_declaration_by_period_and_user(assessment_period.id, user_id)
            if claim_declarations:
                for claim_declaration in claim_declarations:
                    if int(cat_id) == int(claim_declaration.cat_id):
                        response['error'] = 'You have already made a declaration for this category. Please update the amount you desire instead of adding as a new declaration.'
                        return response


                #claim_declaration = claim_declaration[0]




            # is_user_valid = UserDA().check_user_id_is_valid(user_id)
            # if not is_user_valid:
            #     response['success'] = False
            #     response['error'] = 'Invalid user identified. Please verify and try again.'
            #     return response


            # current_date = datetime.now()
            # is_claim_declaration_valid, message = self.__validate_claim_declaration(financial_year_id, user_id)
            # if not is_claim_declaration_valid:
            #     response['success'] = False
            #     response['error'] = message
            #     return response

            # is_claim_declaration_last_date_valid = self.check_claim_declaration_last_date_validity(tax_period.claim_declaration_last_date)
            # if not is_claim_declaration_last_date_valid:
            #     is_last_date_of_declaration_valid = TaxDA().is_last_date_of_declaration_valid(tax_period.id, user_id)
            #     if not is_last_date_of_declaration_valid:
            #         response['success'] = False
            #         response['error'] = 'You are unable to add new declarations as the declaration deadline has expired. Please contact the accounting department for assistance.'
            #         return response

            maximum_allowed_declaration_amount = float(TaxDA().get_maximum_declaration_amount(cat_id))
            if float(amount) > maximum_allowed_declaration_amount:
                response['success'] = False
                response['error'] = f'The declared amount should not exceed the maximum limit for the specified category. ({maximum_allowed_declaration_amount})'
                return response

            with transaction.atomic():
                #tax_batch = TaxDA().get_users_from_tax_batch(tax_period_id=tax_period.id, user_id=user_id).last()
                if tax_batch.regime_type==0 and regime_type not in ('None', '0'):
                    TaxDA().update_finance_data(user_id, {'regime_type': regime_type})
                if regime_type in [1,2,'1','2']:
                    TaxDA().update_finance_data(user_id, {'regime_type': regime_type})
                claim_declaration_data = {
                    'tax_period_id': assessment_period.id,
                    'user_id':user_id,
                    'cat_id':cat_id,
                    'amount':amount,
                    'created_by': user_id
                }
                TaxDA().create_claim_declaration(claim_declaration_data)
                # if not is_created:
                #     response['success'] = False
                #     response['error'] = 'Unable to Complete Update. Please review your information and try again.'
                #     return response

                # claim_declarations_log_data = {'action':'action', 'claim_id':is_created.id,\
                #     'comment':'comment', 'created_by':request.user.id} #TODO
                # is_created = TaxDA().claim_declarations_log_data(claim_declarations_log_data)
                # if not is_created:
                #     response['success'] = False
                #     response['error'] = 'Failed to create log. Please check your settings and try again.'
                #     return response

                response['success'] = True
                response['message'] = 'Successful: Your claim declaration has been successfully created.'

        except Exception as err:
            response["error"] = settings.ERROR_MSG["application_error"].format(
                str(err), self.__log.error(self.__exception.get_exception())
            )
        return response


    def edit_claim_declaration_data(self, request):
        response = {"error": None, "success": False}
        try:
            request_data = request.data
            declaration_id = request_data.get('id')
            financial_year_id = request_data.get('financial_year_id')
            user_id = request.user.id
            cat_id = request_data.get('cat_id')
            amount = request_data.get('amount')
            amount = amount.strip() if amount else None

            if not amount:
                response['error'] = "Please enter the declaration amount"
                return response

            is_amount_valid = self.is_amount_valid(amount)
            if not is_amount_valid:
                response['error'] = 'Invalid amount identified, Please try again'
                return response

            if not float(amount) > 0:
                response['error'] = f'Invalid amount identified, Please try again'
                return response

            if not self.__is_valid_financial_year(financial_year_id):
                response['error'] = 'Invalid financial year identified.'
                return response

            assessment_period = TaxDA().get_assessment_period_by_fin_year_id(financial_year_id)
            if not assessment_period:
                response['error'] = 'Invalid assessment period identified.'
                return response

            tax_batch = TaxDA().get_tax_batch_by_period(tax_period_id=assessment_period.id, user_id=user_id)
            if  not tax_batch:
                response['error'] = 'Invalid user identified. Please verify and try again.'
                return response

            tax_batch = tax_batch[0]
            if tax_batch.last_date_of_declaration < datetime.now().date():
                response['error'] = 'You are unable to modify declarations as the declaration deadline has expired. Please contact the accounting department for assistance.'
                return response

            declaration = TaxDA().get_claim_declarations_by_id(declaration_id)
            if not declaration:
                response['error'] = 'Invalid declaration identified, Please try again'
                return response

            #is_permitted = self.__utility.is_permitted(user_id, 'can_delete_employee_declaration')
            if user_id != declaration.user_id :
                response["error"] = settings.ERROR_MSG.get('access_denied')
                response['status'] = 403
                return response


            maximum_allowed_declaration_amount = round(float(TaxDA().get_maximum_declaration_amount(cat_id)), 2)
            approved_claim_amount = round(float(TaxDA().get_approved_claims_amount_by_declaration_id(declaration_id)), 2)
            in_progress_claim_amount = round(float(TaxDA().get_in_progress_claim_amount_from_declaration_id(declaration_id)), 2)

            # if int(amount) < approved_claim_amount:
            #     response['error'] = f'Account deparment already the amount {approved_claim_amount} have approved. Therefore, you cannot decrease the declaration amount below this value.'
            #     return response

            if float(amount) > maximum_allowed_declaration_amount:
                response['error'] = f'The declared amount should not exceed the maximum limit for the specified category. ({maximum_allowed_declaration_amount})'
                return response

            review_amt = approved_claim_amount + in_progress_claim_amount
            if float(amount) < review_amt:
                response['success'] = False
                response['error'] = f'The Account department has already approved or under review the amount of {review_amt}. Consequently, you are unable to decrease the declaration amount below this value.'
                return response


            TaxDA().update_claim_declaration({'amount':amount}, declaration_id)
            response['success'] = True
            response['message'] = 'Your claim declaration has been successfully updated.'
            return response

            # with transaction.atomic():
            #     is_created =

                # if not is_created:
                #     response['success'] = False
                #     response['error'] = 'Update Unsuccessful'
                #     return response

                # claim_declarations_log_data = {'action':'action', 'claim_id':is_created.id,\
                #     'comment':'comment', 'created_by':request.user.id} #TODO
                # is_created = TaxDA().claim_declarations_log_data(claim_declarations_log_data)

                # if not is_created:
                #     response['success'] = False
                #     response['error'] = 'Log creation failed'
                #     return response

                # response['success'] = True
                # response['message'] = 'Update Successful'

        except Exception as err:
            response["error"] = settings.ERROR_MSG["application_error"].format(
                str(err), self.__log.error(self.__exception.get_exception())
            )
        return response



    def delete_declaration(self, request):
        response = {"error": None, "success": False}
        try:
            user_id = request.user.id
            request_data = request.data
            declaration_id = request_data.get('claim_id')
            last_declaration = False

            declaration = TaxDA().get_claim_declarations_by_id(declaration_id)

            cat_id =declaration.cat_id
            if not declaration:
                response['error'] = 'Invalid declaration identified, Please try again'
                return response

            is_permitted = self.__utility.is_permitted(user_id, 'can_delete_employee_declaration')
            if not request.user.id == declaration.user_id and not is_permitted:
                response["error"] = settings.ERROR_MSG.get('access_denied')
                response['status'] = 403
                return response


            tax_batch = TaxDA().get_tax_batch_by_period(tax_period_id=declaration.tax_period_id, user_id=user_id)
            if  not tax_batch:
                response['error'] = 'Invalid user identified. Please verify and try again.'
                return response

            tax_batch = tax_batch[0]
            if tax_batch.last_date_of_declaration < datetime.now().date():
                response['error'] = 'You are unable to modify declarations as the declaration deadline has expired. Please contact the accounting department for assistance.'
                return response


            #claim_declaration_user_id = TaxDA().get_claim_declaration_user_id(id)

            #is_permitted = self.__utility.is_permitted(user_id, 'can_delete_employee_declaration')

            # if not request.user.id == claim_declaration_user_id and not is_permitted:
            #     response["error"] = settings.ERROR_MSG.get('access_denied')
            #     response['status'] = 403
            #     return response

            # is_claim_declaration_valid = TaxDA().get_claim_declarations_by_id(id)

            # if not is_claim_declaration_valid:
            #     response['success'] = False
            #     response['error'] = 'Invalid Claim Declaration'
            #     return response


            #is_any_claim_approved = self.is_any_claim_approved(declaration_id)
            if self.is_any_claim_approved(declaration_id):
                response['success'] = False
                response['error'] = 'Sorry, but you are unable to delete this declaration as some claims against it have been approved. Kindly reach out to the account department for further assistance.'
                return response

            declaration_user = declaration.user_id
            declaration_period = declaration.tax_period_id

            current_user_declarations = TaxDA().get_all_declarations_from_period_id(declaration_period).filter(user_id=declaration_user)
            if len(current_user_declarations) == 1:
                last_declaration = True

            with transaction.atomic():
                declaration_data = {'is_deleted': 1}
                TaxDA().update_claim_declaration(declaration_data, declaration_id)
                files = TaxDA().get_claim_files(declaration_id=declaration_id)
                files_deleting_from_folder = self.__files_remove_from_folder(files, tax_period_id=declaration.tax_period_id)
                hra_delete = TaxDA().delete_hra_details_by_declaration_id(declaration_id)
                party_ids = []
                # claims = TaxDA().get_claims_by_declaration_id(declaration_id)
                party_ids = TaxDA().get_parties(user_id).filter(period_id=declaration_period, party_type=cat_id).values_list('id', flat=True)

                # for claim in claims:
                if cat_id in (1, 3):
                    party_dict = {}
                    party_dict['is_deleted'] = 1
                    is_deleted = TaxDA().delete_party_using_list_claim_id(party_dict, party_ids)

                TaxDA().delete_claims_by_declaration(declaration_id)

                #TODO delete records from folder also


                # if not is_claims_deleted:
                #     response['success'] = False
                #     response['error'] = 'Claims Delete Unsuccessful'
                #     return response

                # claim_declarations_log_data = {'action':'delete', 'claim_id':is_deleted.id,\
                #     'comment':'comment', 'created_by':request.user.id} #TODO
                # is_created = TaxDA().claim_declarations_log_data(claim_declarations_log_data)

                # if not is_created:
                #     response['success'] = False
                #     response['error'] = 'Log creation failed'
                #     return response

                if last_declaration:
                    tax_batch = TaxDA().get_tax_batch_by_period_and_user(declaration_period, declaration_user)
                    is_regime_type_cleared = TaxDA().update_tax_batch(tax_batch.id, {'regime_type': None})

                response['success'] = True
                response['message'] = 'Your declaration has been deleted successfully.'

        except Exception as err:
            response["error"] = settings.ERROR_MSG["application_error"].format(
                str(err), self.__log.error(self.__exception.get_exception())
            )
        return response

    def create_employee_claim(self, request):
        response = {"error": None, "success": False}
        file_name = ''
        proof_attached = 0
        parties_id=0
        try:
            user_id = request.user.id
            request_data = request.data
            declaration_id = request_data.get('declaration_id')
            financial_year_id = request_data.get('fin_year_id')
            cat_id = request_data.get('cat_id')
            file_objs = request_data.getlist('proof')
            status = 'Under Review'
            created_by = user_id
            comment = request_data.get('comment') if request_data.get('comment') not in ['null', ''] else ''
            amount = request_data.get('amount')
            amount = amount.strip()
            paymentmode = request_data.get('paymentmode')
            proof_type = request_data.get('type')
            part_name = request_data.get('name')
            address_line1 = request_data.get('address_line1')
            city = request_data.get('place')
            district = request_data.get('district')
            state = request_data.get('state')
            pincode = request_data.get('pincode')
            pan_number = request_data.get('pan_number')

            regime_type = request_data.get('regime_type')
            if regime_type not in ['Old', 'old']:
                response['error'] = 'Since you have opted for the new regime, you are not eligible for any claims, \
                                     and therefore, you do not need to upload any claim proof.'
                return response

            if amount in (None, '','null','Null','0') or proof_type == 'Agreement':
                amount = '0.00'
                paymentmode = ''

            is_amount_valid = self.is_amount_valid(amount)
            if not is_amount_valid:
                response['error'] = 'Invalid amount identified, Please try again'
                return response

            declaration = TaxDA().get_claim_declarations_by_id(declaration_id)
            if not declaration:
                response['error'] = 'Invalid declaration identified, Please try again'
                return response

            if user_id != declaration.user_id :
                response["error"] = settings.ERROR_MSG.get('access_denied')
                response['status'] = 403
                return response

            if not self.__is_valid_financial_year(financial_year_id):
                response['error'] = 'Invalid financial year identified.'
                return response

            assessment_period = TaxDA().get_assessment_period_by_fin_year_id(financial_year_id)
            if not assessment_period:
                response['error'] = 'Invalid assessment period identified.'
                return response

            tax_batch = TaxDA().get_tax_batch_by_period(tax_period_id=assessment_period.id, user_id=user_id)
            if  not tax_batch:
                response['error'] = 'Invalid user identified. Please verify and try again.'
                return response

            tax_batch = tax_batch[0]


            # claim_declaration_user_id = TaxDA().get_claim_declaration_user_id(declaration_id)
            # if not claim_declaration_user_id:
            #     response["error"] = settings.ERROR_MSG.get('access_denied')
            #     response['status'] = 403
            #     return response

            # if request.user.id != claim_declaration_user_id:
            #     response["error"] = settings.ERROR_MSG.get('access_denied')
            #     response['status'] = 403
            #     return response


            # is_fyi_valid = self.__is_valid_financial_year(financial_year_id)
            # if not is_fyi_valid:
            #     response['success'] = False
            #     response['error'] = 'Invalid Financial Year'
            #     return response

            # tax_period = TaxDA().get_assessment_period_by_fin_year_id(financial_year_id)
            # tax_period_id = tax_period.id

            if not self.__validate_claim_entry_deadline(assessment_period.id, user_id):
                response['success'] = False
                response['error'] = 'You are unable to add new claim as the claim deadline has expired. Please contact the accounting department for assistance.'
                return response


            claimed_amount = TaxDA().get_claimed_amount_by_declaration(declaration_id)
            declared_amount = declaration.amount #TaxDA().get_claim_declarations_from_declarations_id(declaration_id).amount

            if float(float(claimed_amount)+float(amount)) > float(declared_amount):
                response['error'] = f'Your claimed amount should not exceed the declared amount ({declared_amount})'
                return response

            claim_category = TaxDA().get_claim_category_by_id(cat_id)
            if not claim_category:
                response['error'] = 'Invalid claim category identified, Please try again'
                return response

            if float(amount) > float(claim_category.maximum_allowed):
                response['error'] = f'Maximum allowed claim amount for {claim_category.name} is {claim_category.maximum_allowed}'
                return response

            if file_objs:
                proof_attached = 1

            with transaction.atomic():
                fernet = Fernet(settings.FERNET_KEY)

                parties_id = request_data.get('parties_id')
                if cat_id in ('1', '3'):
                    party_dict = {}
                    party_dict['party_type'] = cat_id
                    party_dict['user_id'] = user_id
                    party_dict['period_id'] = assessment_period.id
                    # party_dict['claim_id'] = is_created.id assessment_period.id
                    if parties_id in (None, '0', '',0):
                        party_dict['parent_id'] = 0
                        party_dict['name'] = part_name if part_name else ''
                        party_dict['address_line1'] = address_line1 if address_line1 else ''
                        party_dict['pan_number'] = pan_number if pan_number else ''
                        party_dict['city'] = city if city else ''
                        party_dict['district'] = district if district else ''
                        party_dict['state'] = state if state else ''
                        party_dict['pincode'] = pincode if pincode else ''

                        res = TaxDA().create_tax_parties(party_dict)
                        if res:
                            parties_id = res.id
                if not parties_id:
                    parties_id=0

                claim_data = {
                    'user_id':user_id,
                    'tax_period_id': assessment_period.id,
                    'cat_id':cat_id,
                    'proof_attached': proof_attached,
                    'file_name': file_name,
                    'amount': amount,
                    'status': status,
                    'created_by': created_by,
                    'claim_declaration_id': declaration_id,
                    'comment':comment,
                    'party_id':parties_id,
                }
                is_created = TaxDA().create_claim(claim_data)
                if is_created and file_objs:
                    for each_file in file_objs:
                        file_name = self.__generate_uuid_filename()
                        folder_path = self.__get_claim_declaration_proof_folder(file_name, assessment_period.id)
                        file = TaxDA().add_claim_files({
                            'file_name': file_name,
                            'claim_id': is_created.id,
                            'claim_declaration_id': declaration_id
                        })
                        if file:
                            FileManager().upload_encrypted_file(folder_path, each_file.read())

                if is_created and cat_id in ('1', '3'):
                    if cat_id ==  '1':
                        try:
                            is_dates_valid = self.validate_from_date_and_to_date(datetime.strptime(request_data.get('fromDate'), "%Y-%m-%d"), datetime.strptime(request_data.get('toDate'), "%Y-%m-%d"))
                        except Exception as e:
                            response['success'] = False
                            response['error'] = 'Date Format Entered Invalid'
                            return response
                        if not is_dates_valid:
                            response['error'] = f"From Date ({request_data.get('fromDate')}) should occur before To Date ({request_data.get('toDate')})."
                            return response

                        hra_dict = {'claim_id': is_created.id, 'claim_declaration_id': declaration_id}
                        hra_dict['proof_type'] = request_data.get('type')
                        hra_dict['from_date'] = request_data.get('fromDate')
                        hra_dict['to_date'] = request_data.get('toDate')
                        hra_dict['payment_mode'] = paymentmode
                        res = TaxDA().create_hra_details(hra_dict)

                response['success'] = True
                response['message'] = 'Claim entry recorded successfully.'

        except Exception as err:
            response["error"] = settings.ERROR_MSG["application_error"].format(
                str(err), self.__log.error(self.__exception.get_exception())
            )
        return response



    def update_employee_claim(self, request):
        response = {"error": None, "success": False}
        file_name = ''
        proof_attached = 0
        res = None
        try:
            user_id = request.user.id
            request_data = request.data
            claim_id = request_data.get('claim_id')
            amount = request_data.get('amount')
            amount = amount.strip()
            file_objs = request_data.getlist('proof')
            proof_added = request_data.get('proof_added')
            part_name = request_data.get('name')
            address_line1 = request_data.get('address_line1')
            city = request_data.get('place')
            district = request_data.get('district')
            state = request_data.get('state')
            pincode = request_data.get('pincode')
            pan_number = request_data.get('pan_number')
            parties_id = request_data.get('parties_id')
            if not parties_id:
                parties_id = 0

            is_amount_valid = self.is_amount_valid(amount)
            if not is_amount_valid:
                response['error'] = 'Invalid amount identified, Please try again'
                return response

            claim = TaxDA().get_claim_by_id(claim_id)
            if not claim:
                response['error'] = 'Invalid claim identified. Please verify and try again.'
                return response

            if claim.user_id != user_id:
                response["error"] = settings.ERROR_MSG.get('access_denied')
                response['status'] = 403
                return response

            if str(claim.status).lower() != "under review":
                response['error'] = 'You are not able to modify this claim since it has either been rejected or approved. You are only able to modify a claim with the status "Under Review."'
                return response

            #declaration = TaxDA().get_claim_declaration_from_claim_id(claim_id)
            declaration_id = claim.claim_declaration_id

            declaration = TaxDA().get_claim_declaration_by_id(declaration_id)
            declaration_amount = declaration.amount
            claim_amount = sum(TaxDA().get_claims_by_declaration_id(declaration_id).filter(~Q(status='Rejected') & ~Q(id=claim_id)).values_list('amount', flat=True))
            # claim_amount = TaxDA().get_claims_by_declaration_id(declaration_id)

            if float(claim_amount) + float(amount) > float(declaration_amount):
                response['error'] = 'Your sum of claim amounts exceeds declaration amount'
                response['success'] = False
                return response

            tax_batch = TaxDA().get_tax_batch_by_period(claim.tax_period_id, user_id)
            if  not tax_batch:
                response['error'] = 'Invalid user identified. Please verify and try again.'
                response['success'] = False
                return response

            tax_batch = tax_batch[0]
            if tax_batch.last_date_of_claim_entry < datetime.now().date():
                response['error'] = 'You are unable to modify the claim as the claim entry deadline has expired. Please contact the accounting department for assistance.'
                response['success'] = False
                return response

            if not file_objs and proof_added == 'false':
                response['success'] = False
                response['error'] = 'Unable to submit a claim without proof, please upload your proof.'
                return response

            if not amount:
                response['error'] = "Please enter the claim amount"
                response['success'] = False
                return response

            file_ids = request_data.getlist('file_ids')
            file_ids = list(map(lambda x: int(x), file_ids))

            #claim_declaration_user_id = TaxDA().get_claim_declaration_user_id(declaration_id)

            # if not request.user.id == claim_declaration_user_id:
            #     response["error"] = settings.ERROR_MSG.get('access_denied')
            #     response['status'] = 403
            #     return response

            # file_ids = request_data.getlist('file_ids')
            # file_ids = list(map(lambda x: int(x), file_ids))
            #claim_id = request_data.get('claim_id')
            #claim = TaxDA().get_claim_by_id(claim_id)
            #cat_id = claim.cat_id

            #financial_year_id = TaxDA().get_fin_year_id_from_tax_period_id(claim.tax_period_id)

            # is_claim_id_valid, message = self.__validate_claim_id(claim_id)
            # if not is_claim_id_valid:
            #     response['success'] = False
            #     response['error'] = message
            #     return response

            # is_fyi_valid = self.__is_valid_financial_year(financial_year_id)
            # if not is_fyi_valid:
            #     response['success'] = False
            #     response['error'] = 'Invalid Financial Year Id'
            #     return response

            # tax_period = TaxDA().get_assessment_period_by_fin_year_id(financial_year_id)
            # tax_period_id = tax_period.id

            #declaration_id = claim.claim_declaration_id
            #status = 'Under Review'

            if file_objs:
                proof_attached = 1
            # is_claim_declaration_valid, message = self.__validate_claim_declaration(financial_year_id, user_id)


            # if not is_claim_declaration_valid:
            #     response['success'] = False
            #     response['error'] = message
            #     return response

            with transaction.atomic():
                fernet = Fernet(settings.FERNET_KEY)
                # fernet = Fernet("n5cafi8eBFFiau9p3aF44DNh4ByIzIQsOrBDHvxTw3Y=")

                claim_data = {
                    'proof_attached': proof_attached,
                    'amount': amount,
                    'status': 'Under Review',
                    'created_on': datetime.now(),
                    'party_id': parties_id,
                }
                TaxDA().update_claim(claim_data, claim_id)

                if file_objs:
                    for each_file in file_objs:
                        file_name = self.__generate_uuid_filename()
                        folder_path = self.__get_claim_declaration_proof_folder(file_name, claim.tax_period_id)
                        file = TaxDA().add_claim_files({
                            'file_name': file_name,
                            'claim_id': claim_id,
                            'claim_declaration_id': declaration_id
                        })
                        if file:
                            FileManager().upload_encrypted_file(folder_path, each_file.read())

                if file_ids:
                    delete_file_list = TaxDA().delete_claim_attachments_using_file_ids(file_ids)

                    for filename in delete_file_list:
                        file_path = self.__get_claim_declaration_proof_folder(filename, claim.tax_period_id)
                        if os.path.exists(file_path):
                            os.remove(file_path)

                if claim.cat_id in (1, 3):
                    party_dict = {}
                    party_dict['party_type'] = claim.cat_id
                    party_dict['user_id'] = user_id
                    party_dict['period_id'] = claim.tax_period_id
                    parties_id = request_data.get('parties_id')
                    if parties_id in (None, '0', '', 'null'):

                        party_dict['parent_id'] = 0
                        party_dict['name'] = part_name if part_name else ''
                        party_dict['address_line1'] = address_line1 if address_line1 else ''
                        party_dict['pan_number'] = pan_number if pan_number else ''
                        party_dict['city'] = city if city else ''
                        party_dict['district'] = district if district else ''
                        party_dict['state'] = state if state else ''
                        party_dict['pincode'] = pincode if pincode else ''

                        res = TaxDA().create_tax_parties(party_dict)
                    # if not res:
                    #     response['success'] = False
                    #     response['error'] = 'Update Unsuccessful'
                    #     return response

                response['success'] = True
                response['message'] = 'Claim entry updated successfully.'

        except Exception as err:
            response["error"] = settings.ERROR_MSG["application_error"].format(
                str(err), self.__log.error(self.__exception.get_exception())
            )
        return response


    def delete_employee_claim(self, request):
        response = {"error": None, "success": False}
        try:
            user_id = request.user.id
            request_data = request.data
            claim_id = request_data.get('claim_id')

            claim = TaxDA().get_claim_by_id(claim_id)
            if not claim:
                response['error'] = 'Invalid claim identified. Please verify and try again.'
                return response

            if claim.user_id != user_id:
                response["error"] = settings.ERROR_MSG.get('access_denied')
                response['status'] = 403
                return response

            if str(claim.status).lower() != "under review":
                response['error'] = 'You are not able to delete this claim since it has either been rejected or approved.'
                return response

            # declaration = TaxDA().get_claim_declaration_from_claim_id(claim_id)
            # declaration_id = declaration.claim_declaration_id
            # claim_declaration_user_id = TaxDA().get_claim_declaration_user_id(declaration_id)

            # if not request.user.id == claim_declaration_user_id:
            #     response["error"] = settings.ERROR_MSG.get('access_denied')
            #     response['status'] = 403
            #     return response

            #request_data = request.data

            # claim = TaxDA().get_claim_by_id(claim_id)

            # cat_id = claim.cat_id

            # financial_year_id = TaxDA().get_fin_year_id_from_tax_period_id(claim.tax_period_id)

            # is_claim_id_valid, message = self.__validate_claim_id(claim_id)
            # if not is_claim_id_valid:
            #     response['success'] = False
            #     response['error'] = message
            #     return response

            # is_fyi_valid = self.__is_valid_financial_year(financial_year_id)
            # if not is_fyi_valid:
            #     response['success'] = False
            #     response['error'] = 'Invalid Financial Year Id'
            #     return response

            # current_date = datetime.now()
            # is_claim_declaration_valid, message = self.__validate_claim_declaration(financial_year_id, user_id)


            # if not is_claim_declaration_valid:
            #     response['success'] = False
            #     response['error'] = message
            #     return response

            with transaction.atomic():

                claim_data = {'is_deleted':1}
                TaxDA().update_claim({'is_deleted':1}, claim_id)

                files = TaxDA().get_claim_files(claim_id=claim_id)
                self.__files_remove_from_folder(files, claim.tax_period_id)
                TaxDA().delete_claim_attachments_by_claim_id(claim_id)
                if claim.cat_id ==1:
                    TaxDA().delete_hra_details_by_claim_id(claim_id)
                #is_deleted = TaxDA().delete_claim_data(claim_data, claim_id)

                # if not is_deleted:
                #     response['success'] = False
                #     response['error'] = 'Unfortunately, the deletion was unsuccessful. Please check your input and try again. If the issue persists, contact our support team for assistance. We apologize for any inconvenience.'
                #     return response

                # if claim.cat_id in (1, 3):
                #     party_dict = {}
                #     party_dict['is_deleted'] = 1
                #     TaxDA().delete_party_using_claim_id(party_dict, claim_id)



                    # if claim.cat_id in (1,):
                    #     is_deleted = TaxDA().delete_hra_details_by_claim_id(claim_id)

                    #     if not is_deleted:
                    #         response['success'] = False
                    #         response['error'] = 'Unfortunately, the deletion was unsuccessful. Please check your input and try again. If the issue persists, contact our support team for assistance. We apologize for any inconvenience.'
                    #         return response

                response['success'] = True
                response['message'] = 'Your claim has been successfully deleted.'

        except Exception as err:
            response["error"] = settings.ERROR_MSG["application_error"].format(
                str(err), self.__log.error(self.__exception.get_exception())
            )
        return response



    def get_user_tax_eligibilty(self, request):
        response = {"is_valid": False, 'regime_type': 0}
        user_id = request.user.id
        try:
            current_date = datetime.now()
            current_fyd = FinanaceDA().get_financial_year_by_date(current_date)
            tax_period = TaxDA().get_assessment_period_by_fin_year_id(current_fyd.financial_year_id)
            if not tax_period:
                response['error'] = 'At present, you are not eligible for IT assessment for the current year. Kindly reach out to the accounting department for further information.'
                return response

            tax_batches =  TaxDA().get_tax_batch_by_period(tax_period.id)
            if not tax_batches.filter(user_id=user_id).exists():
                response['error'] = 'At present, you are not eligible for IT assessment for the current year. Kindly reach out to the accounting department for further information.'
                return response

            tax_batch = tax_batches.filter(user_id=user_id).last()
            response['regime_type'] = tax_batch.regime_type

            response['is_valid'] = True
            response['message'] = 'User Elgible for Tax'

        except Exception as err:
            response["error"] = settings.ERROR_MSG['application_error'].format(
                str(err), self.__log.error(self.__exception.get_exception())
            )
        return response


    def get_my_declarations(self, request, emp_id, tax_period_id):#zzzzz
        response = {"declarations": [], 'error': '', 'employee': '', 'claim_declarations_last_date':'', 'claim_entry_last_date':''}
        category_dict = {}
        try:
            user_id = request.user.id
            role_id, name = UserDA().get_user_role_by_id(user_id)

            if tax_period_id in (0, '0', None):
                current_date = datetime.now()
                current_fyd = FinanaceDA().get_financial_year_by_date(current_date)
                tax_period = TaxDA().get_assessment_period_by_fin_year_id(current_fyd.financial_year_id)
            else:
                tax_period = TaxDA().get_tax_period_from_tax_period_id(tax_period_id)

            tax_period_id = tax_period.id

            if not tax_period:
                response["error"] = 'The Assessment Period is Currently unavailable'
                return response

            claims_declaration = TaxDA().get_claim_declarations_by_emp_id(emp_id, tax_period_id)

            is_permitted = self.__utility.is_permitted(user_id, 'can_view_claim')
            fin_year_id = TaxDA().get_fin_year_id_from_tax_period_id(tax_period_id)
            regime_type = TaxDA().get_regime_type_by_tax_period_user_id(tax_period_id, emp_id)
            regime_type_id = "-"
            if regime_type:
                regime_type_id = settings.REGIME_TYPE_MAPPING.get(regime_type.regime_type, "-")
            fin_year_desc = FinanaceDA().get_financial_year_by_id(fin_year_id).description
            employee = UserDA().get_user_by_id(emp_id)
            response['employee'] = employee.first_name+' '+employee.last_name
            response['emp_code'] = employee.username
            response['regime_type'] = regime_type_id
            response['claim_declaration_last_date'] = tax_period.claim_declaration_last_date.strftime("%d/%m/%Y")
            response['claim_entry_last_date'] = tax_period.claim_entry_last_date.strftime("%d/%m/%Y")
            response['fin_year_desc'] = fin_year_desc
            response['fin_year_id'] = fin_year_id

            if not claims_declaration:
                # response["error"] = "No declarations were found. Please add a new one."
                response['status'] = 403
                return response
            # if not claims_declaration:
            #     response["error"] = settings.ERROR_MSG.get('access_denied')
            #     response['status'] = 403
            #     return response

            if request.user.id != emp_id and not is_permitted:
                response["error"] = settings.ERROR_MSG.get('access_denied')
                response['status'] = 403
                return response

            if tax_period_id in (0, '0', None):
                current_date = datetime.now()
                current_fyd = FinanaceDA().get_financial_year_by_date(current_date)
                tax_period = TaxDA().get_assessment_period_by_fin_year_id(current_fyd.financial_year_id)
            else:
                tax_period = TaxDA().get_tax_period_from_tax_period_id(tax_period_id)

            if not tax_period:
                response["error"] = 'The assessment period is currently unavailable'
                return response

            categories = TaxDA().get_all_categories()

            for each in categories:
                category_dict[each.id] = each.name

            maximum_allowed_list = TaxDA().get_all_category_maximum_allowed_amount()

            claim_category_maximum_allowed_dict = { category[0]: {'cat_id':category[0], 'maximum_allowed':category[1]} for category in maximum_allowed_list }

            for claim in claims_declaration:
                # claim_amount = sum(claim_data.filter(claim_declaration_id=claim.id).values_list('amount', flat=True))
                details, total_amount, total_submitted_amount, approval_awaiting_count = self.get_claims(claim.id)
                temp_dict = {
                    "id": claim.id,
                    'category': category_dict.get(claim.cat_id),
                    'category_id': claim.cat_id,
                    'declared': claim.amount,
                    'date': claim.created_on.strftime('%d/%m/%Y'),
                    'approved': total_amount,
                    'submitted_amount': total_submitted_amount,
                    'maximum_allowed': claim_category_maximum_allowed_dict[claim.cat_id]['maximum_allowed'],
                    'logs': self.__get_log_data(claim.id),
                    'details': details,
                    'approval_awiting': approval_awaiting_count,
                    # 'total_amount': total_amount,
                }
                response['declarations'].append(temp_dict)

        except Exception as err:
            response["error"] = settings.ERROR_MSG['application_error'].format(
                str(err), self.__log.error(self.__exception.get_exception())
            )
        return response


    def check_claim_declaration_last_date_validity(self, claim_declaration_last_date):
        try:
            is_claim_declaration_last_date_valid = True if claim_declaration_last_date >= datetime.now() else None
        except Exception as err:
            self.__log.error(self.__exception.get_exception())
        return is_claim_declaration_last_date_valid


    def check_last_date_of_claim_entry_validity(self, last_date_of_claim_entry, tax_period_id):
        try:
            is_last_date_of_claim_entry_valid = True if last_date_of_claim_entry >= datetime.now() else None
        except Exception as err:
            self.__log.error(self.__exception.get_exception())
        return is_last_date_of_claim_entry_valid



    def convert_date_format(self, date_obj):
        try:
            return date_obj.strftime("%d/%m/%Y")
        except ValueError:
            raise ValueError("Invalid date format. Please provide a date in YYYY-MM-DD format.")



    def __validate_tax_batch(self, tax_batch_id):
        is_validated = None
        try:
            is_validated = TaxDA().check_tax_batch(tax_batch_id)
        except Exception as err:
            self.__log.error(self.__exception.get_exception())
        return is_validated


    def __validate_date(self, input_date):
        try:
            date = datetime.strptime(input_date, "%Y-%m-%d")
            return True
        except Exception as e:
            return False


    def __get_claim_declaration_proof_folder(self, file_name, tax_period_id):
        folder_path = f"{settings.CONFIDENTIAL_DOCS}claim_declaration_proof/{tax_period_id}/{file_name}"
        # folder_path = f"/home/subish/Documents/Subish/claim_declaration_proof/"
        folder = f"{settings.CONFIDENTIAL_DOCS}claim_declaration_proof/{tax_period_id}"
        if not os.path.exists(folder):
            os.makedirs(folder)
        return folder_path


    def __validate_tax_period(self, financial_year_id):
        tax_period = TaxDA().check_tax_period(financial_year_id=financial_year_id)
        return tax_period


    def __is_valid_financial_year(self, financial_year_id):
        is_fyi_valid = FinanaceDA().get_financial_year_by_id(financial_year_id)
        if is_fyi_valid:
            return True
        else:
            return False


    def __get_user_job_title(self, user_id):
        user_profile = UserDA().get_user_profile_by_id(user_id)
        job_title = UserDA().get_job_title_by_id(user_profile.job_title)
        job_title = job_title.job_title
        return job_title


    def __validate_claim_declaration_for_declaration_update(self, fin_year_id):
        try:
            tax_period = TaxDA().get_assessment_period_by_fin_year_id(fin_year_id)
            if tax_period.claim_declaration_last_date >= datetime.now():
                return True
            else:
                return False
        except Exception as e:
            return False


    def __validate_claim_declaration(self, fin_year_id, user_id):
        try:
            tax_period = TaxDA().get_assessment_period_by_fin_year_id(fin_year_id)
            #tax_period_excludes = TaxDA().get_tax_period_excludes(tax_period.id, user_id=user_id)
            if tax_period.claim_entry_last_date >= datetime.now():
                return True, 'Claim Declaration Exists'
            else:
                return False, 'Claim Declaration is not valid'
        except Exception as e:
            return False, 'Error in Validation'

    def __validate_claim_id(self, claim_id):
        try:
            is_claim_id_valid, message = TaxDA().check_claim_id(claim_id)
            if is_claim_id_valid:
                return is_claim_id_valid, message
            else:
                return is_claim_id_valid, message
        except Exception as e:
            return False, 'Error in Claim Id Validation'


    def __get_log_data(self, claim_id):
        result = []
        logs = TaxDA().get_logs_by_claim_id(claim_id)
        user_dict = self.__get_all_active_users(False)
        for each_log in logs:
            result.append(
                f'{each_log.action} By {user_dict[each_log.created_by]} on {each_log.created_on.strftime("%d/%m/%y %I:%M %p")}'
            )
        return result


    def __get_all_active_users(self, is_active=True):
        user_dict = {}
        users = UserDA().get_all_users()
        for each in users:
            if is_active and not each.is_active:
                continue
            user_dict[each.id] = each.first_name+' '+each.last_name
        return user_dict

    def __get_all_active_users_dict(self, is_active=True):
        user_dict = {}
        users = UserDA().get_all_users()
        for each in users:
            if is_active and not each.is_active:
                continue
            user_dict[each.id] = [each.first_name+' '+each.last_name, each.username, each.first_name]
        return user_dict


    def get_parties(self, request):
        response = {"parties": [], 'error': ''}
        unique_names = []
        try:
            user_id = request.user.id
            period_id = request.GET.get('period_id')
            cat_id = request.GET.get('cat_id')

            parties = TaxDA().get_parties(user_id).filter(party_type=cat_id, period_id=period_id)

            for each in parties:
                temp_key = str(each.name).lower() + "_" + str(each.pan_number).lower()
                if temp_key in unique_names:
                    continue
                unique_names.append(temp_key)
                response['parties'].append({
                    'id':each.id,
                    'party_name':each.name
                })

        except Exception as err:
            response["error"] = settings.ERROR_MSG['application_error'].format(
                str(err), self.__log.error(self.__exception.get_exception())
            )
        return response


    def create_parties(self, request):
        response = { 'error': '', 'success': False}
        try:
            user_id = request.user.id
            form_data = request.data
            claim_id = form_data.get('declaration_id')
            declaration = TaxDA().get_claim_declarations_from_declarations_id(claim_id)
            emp_id = declaration.user_id

            if not user_id == emp_id:
                response["error"] = settings.ERROR_MSG.get("access_denied")
                response["status"] = 403
                return response

            name = form_data.get('name')
            party_type = form_data.get('cat_id')
            if self.__check_parties_name_exist(user_id, name, party_type):
                response["error"] = 'Lender/Landloard name already exist'
                return response

            pan_number = form_data.get('pan_number')
            address_line1 = form_data.get('address_line1')
            city = form_data.get('place')
            district = form_data.get('district')
            state = form_data.get('state')
            pincode = form_data.get('pincode')


            create_dict = {
                'party_type': party_type,
                'user_id': user_id,
                'period_id': declaration.tax_period_id,
                'claim_id': claim_id,
                'name': name,
                'address_line1': address_line1,
                'pan_number': pan_number,
                'city': city,
                'district': district,
                'state': state,
                'pincode': pincode,
            }
            res = TaxDA().create_tax_parties(create_dict)
            if res:
                log_dict = {
                    'action': 'Claim Added',
                    'comment': '',
                    'created_by': user_id,
                    'claim_id': claim_id
                }
                TaxDA().claim_declarations_log_data(log_dict)
                response['success'] = True
                response['message'] = 'Created Successfully'
        except Exception as err:
            response["error"] = settings.ERROR_MSG['application_error'].format(
                str(err), self.__log.error(self.__exception.get_exception())
            )
        return response


    def get_party_data(self, request, party_id):
        response = { 'error': '', 'success': False, 'party_data':[]}
        try:
            user_id = request.user.id

            party = TaxDA().get_partie_by_id(party_id)
            party_data = [{'party_type':party.party_type, 'party_name':party.name, 'address_line1':party.address_line1,\
                          'city':party.city, 'state':party.state, 'pincode':party.pincode, 'pan_number':party.pan_number,\
                          'district':party.district}]

            can_view_party = self.__utility.is_permitted(user_id, 'can_view_party_data')
            is_permitted = True if party.user_id == user_id or can_view_party else False
            if not is_permitted:
                response["error"] = settings.ERROR_MSG.get("access_denied")
                response["status"] = 403
                return response

            response['party_data'] = party_data

        except Exception as err:
            response["error"] = settings.ERROR_MSG['application_error'].format(
                str(err), self.__log.error(self.__exception.get_exception())
            )
        return response


    def update_parties(self, request, party_id):
        response = { 'error': '', 'success': False}
        try:
            user_id = request.user.id

            form_data = request.data

            claim_id = form_data.get('claim_id')
            party_name = form_data.get('party_name')
            address_line1 = form_data.get('address_line1')
            city = form_data.get('city')
            state = form_data.get('state')
            pincode = form_data.get('pincode')
            pan_number = form_data.get('pan_number')
            district = form_data.get('district')

            is_party_valid = self.validate_party(user_id, claim_id, party_id)
            if not is_party_valid:
                response['error'] = 'Party data update unsuccessful'
                response['success'] = False
                return response

            party_data = {'name': party_name, 'address_line1': address_line1, 'city':city, \
                          'state': state, 'pincode':pincode, 'pan_number':pan_number, 'district':district}

            is_permitted = True if is_party_valid.user_id == user_id else False
            if not is_permitted:
                response["error"] = settings.ERROR_MSG.get("access_denied")
                response["status"] = 403
                return response

            is_party_updated = TaxDA().update_party(party_data, party_id)

            if not is_party_updated:
                response["error"] = 'Party data update unsuccessful'
                response["success"] = False
                return response

            response['success'] = True
            response['message'] = 'Party data update successful'

        except Exception as err:
            response["error"] = settings.ERROR_MSG['application_error'].format(
                str(err), self.__log.error(self.__exception.get_exception())
            )
        return response


    def __check_duplicate_entry(self, fin_year_id):
        duplicate = False
        try:
            tax_periods = TaxDA().get_all_tax_periods()
            if tax_periods.filter(fin_year_id=fin_year_id):
                duplicate = True
        except:
            pass
        return duplicate


    def __check_parties_name_exist(self, emp_id, name, party_type):
        invalid = False
        try:
            parties = TaxDA().get_parties(emp_id)
            if parties.filter(name==name, party_type=party_type).exists():
                invalid=True
        except:
            pass
        return invalid

    def get_sub_category_by_parent_id(self, request, parent_id):
        response = {'error': '', 'is_sub': False, 'categories': []}
        try:
            is_permitted = True #if user_id== emp_id or role==123
            if not is_permitted:
                response["error"] = settings.ERROR_MSG.get("access_denied")
                response["status"] = 403
                return response
            categories = TaxDA().get_sub_categories(parent_id)
            if categories:
                response['is_sub'] = True
                for each in categories:
                    response['categories'].append({
                        'id': each.id,
                        'name': each.name
                    })
        except Exception as err:
            response["error"] = settings.ERROR_MSG['application_error'].format(
                str(err), self.__log.error(self.__exception.get_exception())
            )
        return response

    def get_claims(self, declaration_id):
        resultList = []
        file_dict = {}
        total_amount = 0
        total_submitted_amount = 0
        approval_awaiting_count = 0
        recipt_type_dict = {}
        try:
            claims = TaxDA().get_claims_by_declaration_id(declaration_id)
            categories = self.__get_categories_dict()
            files = TaxDA().get_claim_files(declaration_id)
            for each in files:
                hra = TaxDA().get_hra_details_from_claim_id(each.claim_id)
                if hra:
                    recipt_type_dict[each.claim_id] = hra.proof_type
                if each.claim_id in file_dict.keys():
                    file_dict[each.claim_id].append({'id': each.id, 'file': each.file_name})
                else:
                    file_dict[each.claim_id] = [{'id': each.id, 'file': each.file_name}]
            for each in claims:
                if each.status == 'Under Review':
                    approval_awaiting_count+=1
                    total_submitted_amount += each.amount
                temp_dict = {
                    'id': each.id,
                    'category': categories.get(each.cat_id),
                    'amount': each.amount,
                    'files': file_dict.get(each.id, []),
                    'status': each.status,
                    'reject_reason': each.reject_reason if each.reject_reason else '',
                    'recipt_type': recipt_type_dict.get(each.id, '')
                }
                resultList.append(temp_dict)
                if each.status == 'Approved':
                    total_amount += each.amount

        except Exception as err:
            self.__log.error(self.__exception.get_exception())
        return resultList, total_amount, total_submitted_amount, approval_awaiting_count

    def __get_categories_dict(self):
        result_dict = {}
        try:
            categories = TaxDA().get_all_categories()
            for each in categories:
                result_dict[each.id] = each.name
        except:
            pass
        return result_dict

    def __get_categories_id_dict(self):
        result_dict = {}
        try:
            categories = TaxDA().get_all_categories()
            for each in categories:
                result_dict[each.id] = each.id
        except:
            pass
        return result_dict

    def __generate_uuid_filename(self):
        return f"{str(uuid.uuid4())}.pdf"


    def is_any_claim_approved(self, declaration_id):
        is_approved = False
        claims = TaxDA().get_claims_by_declaration_id(declaration_id)
        for claim in claims:
            if str(claim.status).lower() == "approved":
                is_approved = True
                break
            # approved_claims = claims.filter(status='Approved')
            # if approved_claims:
            #     is_approved = True
        return is_approved


    def get_claim_by_claim_id(self, request, claim_id):
        response = {'error': '', 'data': {}}
        file_dict = {}
        partie_dict = {}
        try:
            login_user_id = request.user.id
            claim = TaxDA().get_claim_by_id(claim_id)
            if not claim:
                response["error"] = settings.ERROR_MSG.get("access_denied")
                response["status"] = 403
                return response
            #claim = claims

            if login_user_id == claim.user_id:
                is_permitted = True
            else:
                is_permitted = self.__utility.is_permitted(login_user_id, 'can_view_claim')
            if not is_permitted:
                response["error"] = settings.ERROR_MSG.get("access_denied")
                response["status"] = 403
                return response

            parties = TaxDA().get_parties(claim.user_id)
            categories = self.__get_categories_id_dict()
            files = TaxDA().get_claim_files(claim_id=claim_id)
            for each in files:
                if each.claim_id in file_dict.keys():
                    file_dict[each.claim_id].append({'id': each.id, 'file': each.file_name})
                else:
                    file_dict[each.claim_id] = [{'id': each.id, 'file': each.file_name}]

            if parties.filter(id=claim.party_id).exists():
                partie = parties.filter(id=claim.party_id).last()
                partie_dict['name'] = partie.name
                partie_dict['pan'] = partie.pan_number
                partie_dict['current_party_id'] = partie.id
                if partie.address_line1 is None or not partie.address_line1:
                    partie.address_line1 = ''

                if partie.city is None or not partie.city:
                    partie.city = ''

                if partie.district is None or not partie.district:
                    partie.district = ''

                if partie.state is None or not partie.state:
                    partie.state = ''

                if partie.pincode is None or not partie.pincode:
                    partie.pincode = ''

                partie_dict['address'] = ', '.join(filter(None, [partie.address_line1, partie.city, partie.district, partie.state, partie.pincode]))

                if partie.parent_id:
                    partie_dict['id'] = partie.parent_id
                else:
                    partie_dict['id'] = partie.id

            if claim.cat_id == 1:
                hra_details = TaxDA().get_hra_details_from_claim_id(claim.id)

            section_name, category = TaxDA().get_section_and_category_from_cat_id(claim.cat_id)
            fin_year_id = TaxDA().get_fin_year_id_from_tax_period_id(claim.tax_period_id)
            regime_type = TaxDA().get_regime_type_by_tax_period_user_id(claim.tax_period_id, claim.user_id)
            regime_type_id = "-"
            if regime_type:
                regime_type_id = settings.REGIME_TYPE_MAPPING.get(regime_type.regime_type, "-")

            fin_year_desc = FinanaceDA().get_financial_year_by_id(fin_year_id).description

            current_fin_year = FinanaceDA().get_current_financial_year()

            is_current_fin_year = 0
            if current_fin_year.description == fin_year_desc:
                is_current_fin_year = 1
            employee = UserDA().get_user_by_id(claim.user_id)

            temp_dict = {
            'emp_id': claim.user_id,
            'emp_name': UserDA().get_user_full_name_from_id(claim.user_id),
            'emp_code': employee.username,
            'regime_type': regime_type_id,
            'section_name': section_name,
            'submitted_date': claim.created_on.strftime("%d/%m/%Y"),
            'id': claim.id,
            'cat_id':claim.cat_id,
            'category': category,
            'amount': self.format_number(claim.amount),
            'files': file_dict.get(claim.id, []),
            'status': claim.status,
            'parties': partie_dict if categories.get(claim.cat_id) in (1, 3) else None,
            'period_id': claim.tax_period_id,
            'created_on': claim.created_on.strftime("%d/%m/%Y"),
            'proof_type': hra_details.proof_type if claim.cat_id == 1 else None,
            'payment_mode': hra_details.payment_mode if claim.cat_id == 1 else None,
            'to_date': hra_details.to_date.strftime("%d/%m/%Y") if claim.cat_id == 1 else None,
            'from_date': hra_details.from_date.strftime("%d/%m/%Y") if claim.cat_id == 1 else None,
            'fin_year_id': fin_year_id,
            'fin_year_desc': fin_year_desc,
            'is_current_fin_year': is_current_fin_year,
            }
            response['data']= temp_dict

        except Exception as err:
            response["error"] = settings.ERROR_MSG['application_error'].format(
                str(err), self.__log.error(self.__exception.get_exception())
            )
        return response



    def get_file(self, request):
        response = {'error': '', 'data': {}}
        try:
            user_id = request.user.id
            request_data = request.data
            is_permitted = True #if user_id== emp_id or role==123
            if not is_permitted:
                response["error"] = settings.ERROR_MSG.get("access_denied")
                response["status"] = 403
                return response
            file_name = request.GET.get('filename')
            period_id = request.GET.get('period_id')
            pdf_file_path = f"{settings.CONFIDENTIAL_DOCS}claim_declaration_proof/{period_id}/{file_name}"

            file_content = FileManager().read_encrypted_file(pdf_file_path)
            if file_content:
                response = HttpResponse(file_content , content_type='application/pdf')
                response['Content-Disposition'] = 'inline; filename="your_pdf_file.pdf"'
                return response
            else:
                return HttpResponse(status=404)

        except Exception as err:
            response["error"] = settings.ERROR_MSG['application_error'].format(
                str(err), self.__log.error(self.__exception.get_exception())
            )
        return response

    def check_claim_declaration_last_date_validity(self, claim_declaration_last_date):
        try:
            is_claim_declaration_last_date_valid = True if claim_declaration_last_date > datetime.now() else None
        except Exception as err:
            self.__log.error(self.__exception.get_exception())
        return is_claim_declaration_last_date_valid


    def check_last_date_of_claim_entry_validity(self, last_date_of_claim_entry):
        try:
            is_last_date_of_claim_entry_valid = True if last_date_of_claim_entry > datetime.now() else None
        except Exception as err:
            self.__log.error(self.__exception.get_exception())
        return is_last_date_of_claim_entry_valid


    def send_message(self, request, emp_id):
        response = {"approved":False}
        is_completed = False

        try:
            user_id = request.user.id

            if user_id == emp_id:
                response["error"] = settings.ERROR_MSG.get("access_denied")
                response["status"] = 403
                return response

            request_data = request.data
            message = request_data.get('message')
            chat_id =  request_data.get('chat_id')
            tax_period_id = request_data.get('tax_period_id')

            is_message_created = TaxDA().create_message_data(user_id, chat_id, tax_period_id, message)

            if not is_message_created:
                response['success'] = False
                response['message'] = 'Message Sent Fail'
                return response

            claim_user = UserDA().get_user_data_by_emp_id(emp_id)

            emp_mail = []
            emp_mail.append(UserDA().get_user_mail_from_user_id(emp_id))

            initiator_designation = self.__get_user_job_title(user_id)
            initiator_name = request.user.first_name + " " + request.user.last_name
            emp_name = claim_user.first_name + " " + claim_user.last_name
            email_content_dto = new_dto()
            email_content_dto.message = message
            email_content_dto.initiator_name = initiator_name
            email_content_dto.initiator_designation = initiator_designation
            email_content_dto.initiator_email = request.user.email
            email_content_dto.emp_name = emp_name
            subject = f"Message from {initiator_name}"
            email_content_dto.heading = subject
            email_content_dto.message = message
            email_content_dto.page = 'sugesstion_message.html'
            response['message'] = 'Message sent successful'
            email_msg = NotificationBL().generate_email_for_sugesstion_message(email_content_dto)
            NotificationBL().send_finance_mail(email_msg, emp_name, emp_mail, subject)
            response['success'] = True
            is_completed = True
            if not is_completed:
                response['success'] = False
                response['error'] = 'Process Incomplete'
        except Exception as err:
            response["error"] = settings.ERROR_MSG['application_error'].format(
                str(err), self.__log.error(self.__exception.get_exception())
            )

        return response



    def get_years_in_a_financial_year(self, financial_year):
        years = []
        try:
            years.append(financial_year.start_date.year)
            years.append(financial_year.end_date.year)
        except Exception as err:
            self.__log.error(self.__exception.get_exception())
        return years


    def __validate_claim_entry_deadline(self, tax_period_id, user_id):
        is_valid = False
        tax_batch = TaxDA().get_tax_batch_by_period_and_user(tax_period_id, user_id)
        if tax_batch and tax_batch.last_date_of_claim_entry >= datetime.now().date():
            is_valid = True
        return is_valid


    def __files_remove_from_folder(self, files, tax_period_id):
        try:
            for file_obj in files:
                pdf_file_path = f"{settings.CONFIDENTIAL_DOCS}claim_declaration_proof/{tax_period_id}/{file_obj.file_name}"
                if os.path.exists(pdf_file_path):
                    os.remove(pdf_file_path)
            return True
        except Exception as err:
            self.__log.error(self.__exception.get_exception())
            return False



    def is_amount_valid(self, value):
        pattern = r"^[0-9]+(\.[0-9]{2})?$"
        return bool(re.match(pattern, value))



    def format_number(self, number):
        number_str = str(number)
        if '.' not in number_str:
            return number_str + ".00"
        else:
            parts = number_str.split('.')
            decimal_places = len(parts[1])

            if decimal_places == 1:
                return number_str + "0"
        return number_str



    def validate_from_date_and_to_date(self, from_date, to_date):
        return True if from_date <= to_date else False


    def validate_party(self, user_id, claim_id, party_id):
        current_fin_year_id = FinanaceDA().get_current_financial_year()
        current_period_id = TaxDA().get_tax_period_from_financial_year_id(current_fin_year_id.financial_year_id).id
        claim_period = TaxDA().get_claim_by_id(claim_id).tax_period_id
        if not current_period_id == claim_period:
            return False

        party = TaxDA().get_partie_by_id(party_id)
        if not party:
            return False
        else:
            return party


    def test_mail(self):
        from pTracker.dataaccess.ptracker_access.tax_models import TaxBatch
        tax_batch_data = TaxBatch.objects.filter(tax_period_id=1, is_deleted=0)
        user_ids = []
        if tax_batch_data:
            for each in tax_batch_data:
                user_ids.append(each.user_id)


        emp_mail_list = UserDA().get_user_mails_from_user_ids(user_ids)
        print(emp_mail_list)
        emp_job_title = self.__get_user_job_title(4)
        comment = ''
        emp_name = "Renjith M B"
        subject = 'Important Notice: Commencement of Income Tax Assessment Process'

        email_content_dto = new_dto()
        email_content_dto.comment = comment
        email_content_dto.heading = 'Important Notice: Commencement of Income Tax Assessment Process'
        email_content_dto.emp_name = emp_name
        email_content_dto.last_date_of_declaration = "22/05/2024"
        email_content_dto.emp_designation = emp_job_title
        email_content_dto.emp_email = "renjith@mydomain.com"
        email_msg = NotificationBL().generate_initiate_email_messages(email_content_dto)

        #TODO
        #emp_mail_list = ['abdul.jaseem@mydomain.com', 'subish@mydomain.com']
        #TODO

        NotificationBL().send_finance_mail(email_msg, emp_name, emp_mail_list, subject)
        print('ok')
