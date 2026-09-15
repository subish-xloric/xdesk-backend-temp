import uuid
import json
from datetime import datetime
from types import SimpleNamespace

from django.http import HttpResponse
from django.conf import settings
from collections import defaultdict

from pTracker.common.utility import Utility
from pTracker.common.exception_handler import ExceptionHandler
from pTracker.common.logs import Logs
from pTracker.dataaccess.ptracker_access.user_da import UserDA
from pTracker.dataaccess.ptracker_access.tax_da import TaxDA
from pTracker.dataaccess.ptracker_access.finance_da import FinanaceDA

import re


def new_dto():
    dto = SimpleNamespace()
    return dto

class TaxDeduction():

    def __init__(self):
        self.__log = Logs()
        self.__exception = ExceptionHandler()
        self.__utility = Utility()

    def get_all_other_income_and_deduction(self, request, fin_year_id, org_id):
        response = {
            'tax_deduction_data': [],
            'tax_deduction_sections':[],
            'error': None,
            'is_single_user': False,
        }

        try:
            user_id = request.user.id
            is_permitted = self.__utility.is_permitted(user_id, 'can_manage_other_income')
            emp_data = []

            fin_year = FinanaceDA().get_financial_year_by_id(fin_year_id)
            if not fin_year:
                response["error"] = "It seems there's an error with the financial year you've entered. Please check and try again."
                response['status'] = 499
                return response

            fin_year_desc = fin_year.description

            if is_permitted:
                employee_tax_deduction = TaxDA().get_employee_tax_deduction_by_fin_year_id(fin_year_id)
            else:
                employee_tax_deduction = TaxDA().get_employee_tax_deduction_by_fin_year_id(fin_year_id, user_id)
                response['is_single_user'] = True

            if employee_tax_deduction:
                employee_list = list(set(employee_tax_deduction.values_list('emp_id', flat=True)))
                user_profiles_obj = UserDA().get_user_profiles_by_employee_ids(employee_list).filter(company_id=org_id)

                if user_profiles_obj:
                    user_profiles = user_profiles_obj.values_list('user_id', flat=True)
                    all_users = UserDA().get_all_users().filter(id__in=user_profiles)
                    user_dict = {user.id: user for user in all_users}

                    for each_tax_deduct in employee_tax_deduction:
                        user_id = each_tax_deduct.emp_id
                        user = user_dict.get(user_id, None)
                        if user:
                            emp_entry = {
                                "emp_name": f"{user.first_name} {user.last_name}",
                                "emp_id": user.id,
                                "emp_code": user.username,
                                "fin_year_id": each_tax_deduct.fin_year_id,
                                "codename" : each_tax_deduct.codename,
                                "section" : each_tax_deduct.section,
                                "amount" : each_tax_deduct.amount,
                                "fin_year_desc" : fin_year_desc
                            }
                            emp_data.append(emp_entry)
            if is_permitted:
                tax_deduction_sections = settings.CODENAME
            else:
                tax_deduction_sections = settings.CODENAME_EMP
            response['tax_deduction_data'] = emp_data
            response['tax_deduction_sections'] = tax_deduction_sections
        except Exception as err:
            response["error"] = settings.ERROR_MSG['application_error'].format(
                str(err), self.__log.error(self.__exception.get_exception())
            )
        return response

    def create_other_income_deduction(self, request):
        response = {'success':False, 'message':'', 'error':False}
        max_amount = 1000000
        try:
            user_id = request.user.id
            is_permitted = self.__utility.is_permitted(user_id, 'can_approve_claim')

            codenames = [d["codename"] for d in settings.CODENAME]
            codenames_emp = [d["codename"] for d in settings.CODENAME_EMP]

            tax_deduct_data = {}
            request_data=request.data

            emp_id = request_data.get('emp_id')
            fin_year_id = request_data.get('fin_year_id')
            code_name = request_data.get('codename')
            section = request_data.get('section')
            amount = request_data.get('amount')

            current_fyd = FinanaceDA().get_financial_year_by_date(datetime.now())
            if current_fyd and current_fyd.financial_year_id != fin_year_id:
                response["error"] = "You cannot add other income and deductions for any period other than the current financial year."
                response['status'] = 499
                return response

            if is_permitted:
                if code_name not in codenames:
                    response['error'] = 'The section name provided is not valid for creation.'
                    return response
            else:
                if user_id != emp_id:
                    response["error"] = settings.ERROR_MSG.get('access_denied')
                    response['status'] = 403
                    return response

                if code_name not in codenames_emp:
                    response['error'] = 'The section name provided is not valid for creation.'
                    return response

            is_amount_valid = self.is_amount_valid(amount)
            if not is_amount_valid:
                response['error'] = 'Invalid amount identified, Please try again'
                return response

            if float(amount) >= float(max_amount):
                response['error'] = f'Amount should be less than allowed limit ({max_amount})'
                return response

            is_found = TaxDA().get_employee_tax_deduction_by_emp_id_fin_year_id(fin_year_id,emp_id).filter(codename=code_name)
            if is_found:
                response['error'] = 'Error: The section already exists.'
                return response

            tax_period_id = TaxDA().get_tax_period_from_financial_year_id(fin_year_id)
            regime_type = TaxDA().get_regime_type_by_tax_period_user_id(tax_period_id.id, emp_id)
            regime_type_id = 0
            if regime_type:
                regime_type_id = regime_type.regime_type
            tax_deduct_data = {
                'emp_id': emp_id,
                'fin_year_id' : fin_year_id,
                'codename' : code_name,
                'section' : section,
                'amount' : amount,
                'regime_type' : regime_type_id,
                'criteria' : 1

            }
            is_created = TaxDA().create_other_income_deduction(tax_deduct_data)
            if is_created:
                response['success'] = True
                response['message'] = 'Other Inc. & Ded. created sucessfully'
            else:
                response['error'] = True
                response['message'] = 'Other Inc. & Ded. creation unsucessful'

        except Exception as err:
            response["error"] = settings.ERROR_MSG['application_error'].format(
                str(err), self.__log.error(self.__exception.get_exception())
            )
        return response


    def update_other_income_deduction(self, request):
        response = {'success':False, 'message':'', 'error':False}
        max_amount = 1000000
        try:
            user_id = request.user.id
            is_permitted = self.__utility.is_permitted(user_id, 'can_approve_claim')

            codenames = [d["codename"] for d in settings.CODENAME]
            codenames_emp = [d["codename"] for d in settings.CODENAME_EMP]

            tax_deduct_data = {}
            request_data=request.data
            emp_id = request_data.get('emp_id')
            fin_year_id = request_data.get('fin_year_id')
            code_name = request_data.get('codename')
            amount = request_data.get('amount')

            current_fyd = FinanaceDA().get_financial_year_by_date(datetime.now())
            if current_fyd and current_fyd.financial_year_id != fin_year_id:
                response["error"] = "You cannot update other income and deductions for any period other than the current financial year."
                response['status'] = 499
                return response


            if is_permitted:
                if code_name not in codenames:
                    response['error'] = 'The section name provided is not valid for update'
                    response['status'] = 499
                    return response
            else:
                if code_name not in codenames_emp:
                    response['status'] = 499
                    response['error'] = 'The section name provided is not valid for update'
                    return response

                if user_id != emp_id:
                    response["error"] = settings.ERROR_MSG.get('access_denied')
                    response['status'] = 403
                    return response

            is_amount_valid = self.is_amount_valid(amount)
            if not is_amount_valid:
                response['error'] = 'Invalid amount identified, Please try again'
                return response

            if float(amount) >= float(max_amount):
                response['error'] = f'Amount should be less than allowed limit ({max_amount})'
                return response

            tax_deduct_data = {
                'emp_id': emp_id,
                'fin_year_id' : fin_year_id,
                'codename' : code_name,
                'amount' : amount,
            }
            is_updated = TaxDA().update_other_income_deduction(tax_deduct_data)
            if is_updated:
                response['success'] = True
                response['message'] = 'Other Inc. & Ded. updated sucessfully'
            else:
                response['error'] = 'Other Inc. & Ded. updation unsucessful'

        except Exception as err:
            response["error"] = settings.ERROR_MSG['application_error'].format(
                str(err), self.__log.error(self.__exception.get_exception())
            )
        return response


    def delete_other_income_deduction(self, request):
        response = {'success':False,'message':'', 'error':False}
        try:
            user_id = request.user.id
            is_permitted = self.__utility.is_permitted(user_id, 'can_approve_claim')

            codenames = [d["codename"] for d in settings.CODENAME]
            codenames_emp = [d["codename"] for d in settings.CODENAME_EMP]

            tax_deduct_data = {}
            request_data=request.data
            emp_id = request_data.get('emp_id')
            fin_year_id = request_data.get('fin_year_id')
            code_name = request_data.get('codename')

            current_fyd = FinanaceDA().get_financial_year_by_date(datetime.now())
            if current_fyd and current_fyd.financial_year_id != fin_year_id:
                response["error"] = "You cannot delete other income and deductions for any period other than the current financial year."
                response['status'] = 499
                return response


            if is_permitted:
                if code_name not in codenames:
                    response['error'] = 'The section name provided is not valid for delete.'
                    response['status'] = 499
                    return response
            else:
                if code_name not in codenames_emp:
                    response['error'] = 'The section name provided is not valid for delete'
                    response['status'] = 499
                    return response

                if user_id != emp_id:
                    response["error"] = settings.ERROR_MSG.get('access_denied')
                    response['status'] = 403
                    return response

            tax_deduct_data = {
                'emp_id': emp_id,
                'fin_year_id' : fin_year_id,
                'codename' : code_name
            }
            is_deleted = TaxDA().delete_tax_deduction_data(tax_deduct_data)
            if is_deleted:
                response['success'] = True
                response['message'] = 'Other Inc. & Ded. deleted sucessfully.'
            else:
                response['error'] = True
                response['message'] = 'Other Inc. & Ded. deletion unsucessfull.'

        except Exception as err:
            response["error"] = settings.ERROR_MSG['application_error'].format(
                str(err), self.__log.error(self.__exception.get_exception())
            )
        return response


    def is_amount_valid(self, value):
        try:
            value = float(value)
            return True
        except:
            return False