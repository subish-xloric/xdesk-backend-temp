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

from pTracker.dataaccess.ptracker_access.user_da import UserDA
from pTracker.dataaccess.ptracker_access.finance_da import FinanaceDA
from pTracker.dataaccess.ptracker_access.tax_da import TaxDA
from pTracker.api.finance.tax_dict_generator import TaxDictGenerator

from pTracker.api.finance.notification_biz import NotificationBL

from pTracker.settings import constants
from pTracker.cronjobs.email_sender import send_email_notification

from cryptography.fernet import Fernet
from django.db.models import Q


import os
import re

chapter_vi_max_dict ={
                "section_24": 200000,
                "80C": 150000,
                "80CCC": 150000,
                "80CCD": 150000,
                "80CCD(1)": 150000,
                "80CCD(2)":50000,
                "80CCD(1B)":50000,
                "80DD":75000,
                "80D":25000,
                "80TTA":10000,
                "80EEA": 150000,
                "80EEB":150000,
                "80DDB":40000

            }


def new_dto():
    dto = SimpleNamespace()
    return dto

class TaxComputationBL():
    def __init__(self):
        self.__log = Logs()
        self.__exception = ExceptionHandler()
        self.__utility = Utility()
        self.__tax_da = TaxDA()
        self.__dict_gen = TaxDictGenerator()
        self.regime_type = None

        #1 find annual salary
        #2 Less  find HRA
        #3 Less Standard deduction
        #4 Less find professtional tax


    def test_subish(self, emp_id, fin_year_id):
        response = {"error": None, "amount": 0}
        try:
            ctc_master_data = self.__tax_da.get_all_details_from_ctc()
            ctc_earning_ids = ctc_master_data.filter(type='Earning').values_list('ctc_id', flat=True)
            ctc_deduction_ids = ctc_master_data.filter(type='Deduction', name='lop').values_list('ctc_id', flat=True)

            ctc_employee_data = self.__tax_da.get_ctc_employee_data_by_emp_id_fin_year_id(fin_year_id, emp_id)
            amount_list = ctc_employee_data.filter(ctc_id__in=ctc_earning_ids).values_list('amount', flat=True)
            deduction_amount_list = ctc_employee_data.filter(ctc_id__in=ctc_deduction_ids).values_list('amount', flat=True)
            
            try:
                lop = sum(list(map(self.__utility.decrypt_ctc_amount, deduction_amount_list)))
            except:
                lop = 0
            print('deduction_amount_list', lop)

            if amount_list:
                gross_salary = sum(list(map(self.__utility.decrypt_ctc_amount, amount_list))) # - sum(list(map(self.__utility.decrypt_ctc_amount, deduction_amount_list)))
                response['amount'] = gross_salary - lop
            else:
                response['error'] = 'Gross Salary calculation failed hence pdf cannot be generated'

        except Exception as err:
            response["error"] = settings.ERROR_MSG["application_error"].format(
                str(err), self.__log.error(self.__exception.get_exception())
            )
        return response
    

    def __get_employee_pf(self, emp_id, fin_year_id):
        response = {"error": None, "amount": 0}
        try:
            if self.regime_type == 'new':
                response['amount'] = 0
                return response
            
            ctc_master_data = self.__tax_da.get_all_details_from_ctc()            
            ctc_deduction_ids = ctc_master_data.filter(type='Deduction', name='pf').values_list('ctc_id', flat=True)
            ctc_employee_data = self.__tax_da.get_ctc_employee_data_by_emp_id_fin_year_id(fin_year_id, emp_id)            
            deduction_amount_list = ctc_employee_data.filter(ctc_id__in=ctc_deduction_ids).values_list('amount', flat=True)
            if deduction_amount_list:
                try:
                    emp_pf_amount = sum(list(map(self.__utility.decrypt_ctc_amount, deduction_amount_list)))
                except:
                    emp_pf_amount = 0

                response['amount'] = emp_pf_amount             
            else:
                response['amount'] = 0                 

        except Exception as err:
            response["error"] = settings.ERROR_MSG["application_error"].format(
                str(err), self.__log.error(self.__exception.get_exception())
            )
        return response
    

    def __get_gross_salary_sec_17_1(self, emp_id, fin_year_id):
        response = {"error": None, "amount": 0}
        try:
            ctc_master_data = self.__tax_da.get_all_details_from_ctc()
            ctc_earning_ids = ctc_master_data.filter(type='Earning').values_list('ctc_id', flat=True)
            ctc_deduction_ids = ctc_master_data.filter(type='Deduction', name='lop').values_list('ctc_id', flat=True)

            ctc_employee_data = self.__tax_da.get_ctc_employee_data_by_emp_id_fin_year_id(fin_year_id, emp_id)
            amount_list = ctc_employee_data.filter(ctc_id__in=ctc_earning_ids).values_list('amount', flat=True)
            deduction_amount_list = ctc_employee_data.filter(ctc_id__in=ctc_deduction_ids).values_list('amount', flat=True)
            try:
                lop = sum(list(map(self.__utility.decrypt_ctc_amount, deduction_amount_list)))
            except:
                lop = 0

            if amount_list:
                gross_salary = sum(list(map(self.__utility.decrypt_ctc_amount, amount_list))) # - sum(list(map(self.__utility.decrypt_ctc_amount, deduction_amount_list)))
                response['amount'] = gross_salary - lop
            else:
                response['error'] = 'Gross Salary calculation failed hence pdf cannot be generated'

        except Exception as err:
            response["error"] = settings.ERROR_MSG["application_error"].format(
                str(err), self.__log.error(self.__exception.get_exception())
            )
        return response


    def __get_reported_total_salary_from_other_employer(self, emp_id, fin_year_id, section):
        response = {"error": None, "amount": 0}
        try:
            amount = self.__get_other_income_and_deductions(emp_id, fin_year_id, section)
            response['amount'] = amount
        except Exception as err:
            response["error"] = settings.ERROR_MSG["application_error"].format(
                str(err), self.__log.error(self.__exception.get_exception())
            )
        return response


    def __get_perquisites_value_sec_17_2(self, emp_id, fin_year_id, section):
        response = {"error": None, "amount": 0}
        try:
            amount = self.__get_other_income_and_deductions(emp_id, fin_year_id, section)
            #amount = 0
            response['amount'] = amount
        except Exception as err:
            response["error"] = settings.ERROR_MSG["application_error"].format(
                str(err), self.__log.error(self.__exception.get_exception())
            )
        return response


    def __get_profits_lieu_sec_17_3(self, emp_id, fin_year_id, section):
        response = {"error": None, "amount": 0}
        try:
            amount = self.__get_other_income_and_deductions(emp_id, fin_year_id, section)
            response['amount'] = amount
        except Exception as err:
            response["error"] = settings.ERROR_MSG["application_error"].format(
                str(err), self.__log.error(self.__exception.get_exception())
            )
        return response

    #other income and deductions
    def __get_other_income_and_deductions(self, emp_id, fin_year_id, section):
        amount = 0
        amount_list = TaxDA().get_other_income_and_deduction(fin_year_id, emp_id, section)
        if amount_list:
            amount_list = amount_list.values_list('amount', flat=True)
            amount = sum(list(amount_list))
        return amount

    #Travel concession
    def __get_travel_concessions_assistance_sec_10_5(self, emp_id, fin_year_id):
        response = {"error": None, "amount": 0}
        try:
            if self.regime_type == 'new':
                response['amount'] = 0
                return response
            ctc_id = TaxDA().get_all_details_from_ctc().filter(section='10(15)').first().ctc_id
            amount_list = TaxDA().get_ctc_employee_data_by_emp_id_fin_year_id(fin_year_id, emp_id).filter(ctc_id=ctc_id).values_list('amount', flat=True)
            amount = sum(list(map(self.__utility.decrypt_ctc_amount, amount_list)))
            response['amount'] = amount
        except Exception as err:
            response["error"] = settings.ERROR_MSG["application_error"].format(
                str(err), self.__log.error(self.__exception.get_exception())
            )
        return response


    #Death-cum-retirement gratuity under section 10(10)
    def __get_gratuity_sec_10_10(self, emp_id, fin_year_id, section):
        response = {"error": None, "amount": 0}
        if self.regime_type == 'new':
            response['amount'] = 0
            return response
        amount = self.__get_other_income_and_deductions(emp_id, fin_year_id, section)
        response['amount'] = amount
        return response

    #Commuted value of pension under section 10(10A)
    def __get_pension_sec_10_10_a(self, emp_id, fin_year_id, section):
        response = {"error": None, "amount": 0}
        try:
            if self.regime_type == 'new':
                response['amount'] = 0
                return response
            amount = self.__get_other_income_and_deductions(emp_id, fin_year_id, section)
            response['amount'] = amount
        except Exception as err:
            response["error"] = settings.ERROR_MSG["application_error"].format(
                str(err), self.__log.error(self.__exception.get_exception())
            )
        return response

    #Cash equivalent of leave salary encashment under section 10(10AA
    def __get_leave_salary_encashment_sec_10_10_aa(self, emp_id, fin_year_id):
        response = {"error": None, "amount": 0}
        try:
            if self.regime_type == 'new':
                response['amount'] = 0
                return response

            amount = self.__get_other_income_and_deductions(emp_id, fin_year_id, '10(10AA)')
            response['amount'] = amount
        except Exception as err:
            response["error"] = settings.ERROR_MSG["application_error"].format(
                str(err), self.__log.error(self.__exception.get_exception())
            )
        return response

    #House rent allowance under section 10(13A)
    def __get_hra_exemption_sec_10_13_a(self, emp_id, fin_year_id, tax_period_id, as_per_declarations = 0):
        response = {"error": None, "amount":0}
        try:
            if self.regime_type == 'new':
                response['amount'] = 0
                return response

            hra_declaration = TaxDA().get_all_declarations_from_period_id(tax_period_id).filter(cat_id=1, user_id=emp_id)#.first()
            if not hra_declaration:
                return response

            employee_ctc_data = TaxDA().get_ctc_employee_data_by_emp_id_fin_year_id(fin_year_id, emp_id)
            if not employee_ctc_data:
                response['error'] = 'HRA Exemption can be calculated only after CTC data is updated for the Employee'
                return response

            hra_ctc_id = TaxDA().get_all_details_from_ctc().filter(section='10(13A)').first().ctc_id
            basic_ctc_id = TaxDA().get_all_details_from_ctc().filter(name='basic').first().ctc_id

            actual_hra = self.__utility.decrypt_ctc_amount(employee_ctc_data.filter(ctc_id=hra_ctc_id).first().amount)
            basic_salary = self.__utility.decrypt_ctc_amount(employee_ctc_data.filter(ctc_id=basic_ctc_id).first().amount)

            if as_per_declarations:
                hra_declaration = hra_declaration.first()
                actual_rent_paid = hra_declaration.amount
                hra_exemption = min(actual_hra, 0.4*basic_salary, float(actual_rent_paid)-(0.1*basic_salary))

            else:
                hra_claim = TaxDA().get_all_user_claims_by_period_id(emp_id, tax_period_id, 'Approved').filter(cat_id=1).values_list('amount', flat=True)
                if not hra_claim:
                    hra_exemption = 0
                else:
                    actual_rent_paid = sum(hra_claim)
                    hra_exemption = min(actual_hra, 0.4*basic_salary, float(actual_rent_paid)-(0.1*basic_salary))
            if hra_exemption <=0:
                hra_exemption = 0
            response['amount'] = float(hra_exemption)

        except Exception as err:
            response["error"] = settings.ERROR_MSG["application_error"].format(
                str(err), self.__log.error(self.__exception.get_exception())
            )
        return response


    #Meal Card
    def __get_other_exemption_amount_sec_10(self, emp_id, fin_year_id):
        response = {"error": None, "amount":0}
        try:
            if self.regime_type == 'new':
                response['amount'] = 0
                return response
            ctc_ids = TaxDA().get_all_details_from_ctc().filter(section='10').values_list('ctc_id', flat=True)
            amount_list = TaxDA().get_ctc_employee_data_by_emp_id_fin_year_id(fin_year_id, emp_id).filter(ctc_id__in=ctc_ids).values_list('amount', flat=True)
            amount = sum(list(map(self.__utility.decrypt_ctc_amount, amount_list)))
            response['amount'] = amount
        except Exception as err:
            response["error"] = settings.ERROR_MSG["application_error"].format(
                str(err), self.__log.error(self.__exception.get_exception())
            )
        return response


    def __get_total_other_exemption_sec_10(self, emp_id, fin_year_id):
        response = {"error": None, "amount": 0}
        try:
            amount = 0
            response['amount'] = amount
            if self.regime_type == 'new':
                response['amount'] = 0
                return response

        except Exception as err:
            response["error"] = settings.ERROR_MSG["application_error"].format(
                str(err), self.__log.error(self.__exception.get_exception())
            )
        return response


    #Standard deduction under section 16(ia)
    def __get_standard_deduction_sec_16_ia(self, emp_id, fin_year_id, regime_type):
        response = {"error": None, "amount": 0}
        if str(regime_type).lower() == "new":
            response['amount'] = 75000
        else:
            response['amount'] = settings.TAX_CONSTANTS['standard_deduction']
        return response

    #Entertainment allowance under section 16(ii)
    def __get_entertainment_allowance_sec_16_ii(self, emp_id, fin_year_id, section):
        response = {"error": None, "amount": 0}
        try:
            if self.regime_type == 'new':
                response['amount'] = 0
                return response
            amount = self.__get_other_income_and_deductions(emp_id, fin_year_id, section)
            response['amount'] = amount
        except Exception as err:
            response["error"] = settings.ERROR_MSG["application_error"].format(
                str(err), self.__log.error(self.__exception.get_exception())
            )
        return response

    #Tax on employment under section 16(iii)
    def __get_employment_tax_sec_16_iii(self, emp_id, fin_year_id):
        response = {"error": None, "amount": 0}
        try:
            if self.regime_type == 'new':
                response['amount'] = 0
                return response
            amount = 2500 #TODO
            response['amount'] = amount
        except Exception as err:
            response["error"] = settings.ERROR_MSG["application_error"].format(
                str(err), self.__log.error(self.__exception.get_exception())
            )
        return response

    #Income under the head Other Sources offered for TDS
    def __get_head_other_sources_income(self, emp_id, fin_year_id):
        response = {"error": None, "amount": 0}
        try:
            amount = self.__get_other_income_and_deductions(emp_id, fin_year_id, '192(2B)')

            response['amount'] = amount

        except Exception as err:
            response["error"] = settings.ERROR_MSG["application_error"].format(
                str(err), self.__log.error(self.__exception.get_exception())
            )
        return response


    def __get_deductions_under_chapter_vi_a(self, section, emp_id, tax_period_id, as_per_declarations=0):
        response = {"error": None, "amount": 0}

        try:
            if self.regime_type == 'new':
                response['amount'] = 0
                return response
            cat_ids = TaxDA().get_all_categories().filter(section=section).values_list('id', flat=True)
            if as_per_declarations:
                deduction_amount = self.__get_declaration_amount(emp_id, cat_ids, tax_period_id)
            else:
                deduction_amount = self.__get_approved_amount(emp_id, cat_ids, tax_period_id)
            response['amount'] = deduction_amount

        except Exception as err:
            response["error"] = settings.ERROR_MSG["application_error"].format(
                str(err), self.__log.error(self.__exception.get_exception())
            )
        return response

    def __get_declaration_amount(self, emp_id, cat_ids, tax_period_id):
        deduction_amount = 0
        obj_declaration = TaxDA().get_all_declarations_from_period_id(tax_period_id).filter(cat_id__in=cat_ids, user_id=emp_id)#.first()
        if obj_declaration:
            obj_declaration = obj_declaration[0]
            deduction_amount = obj_declaration.amount
        return deduction_amount

    def __get_approved_amount(self, emp_id, cat_ids, tax_period_id):
        deduction_amount = 0
        section_claim = TaxDA().get_all_user_claims_by_period_id(emp_id, tax_period_id, 'Approved').filter(cat_id__in=cat_ids).values_list('amount', flat=True)
        if section_claim:
            deduction_amount = sum(section_claim)
        return deduction_amount


    #Amount deductible under any other provision(s) of Chapter VI-A
    def __get_deductions_under_other_provisions_chapter_vi_a(self, emp_id, fin_year_id):
        response = {"error": None, "amount": 0}
        try:
            amount = amount = self.__get_other_income_and_deductions(emp_id, fin_year_id, 'Chapter VI-A')
            response['amount'] = amount
        except Exception as err:
            response["error"] = settings.ERROR_MSG["application_error"].format(
                str(err), self.__log.error(self.__exception.get_exception())
            )
        return response

    #Rebate under section 87A, if applicable
    def __get_rebate_sec_87_a(self, gross_total_income):
        response = {"error": None, "amount": 0}
        try:
            amount = 0
            if self.regime_type == 'new':
                if gross_total_income <=700000:
                    amount = 25000
            else:
                if gross_total_income <=500000:
                    amount = 12500
            response['amount'] = amount
        except Exception as err:
            response["error"] = settings.ERROR_MSG["application_error"].format(
                str(err), self.__log.error(self.__exception.get_exception())
            )
        return response

    #Relief under section 89
    def __get_relief_sec_89(self, emp_id, fin_year_id):
        response = {"error": None, "amount": 0}
        try:
            amount = self.__get_other_income_and_deductions(emp_id, fin_year_id, '89')
            response['amount'] = amount
        except Exception as err:
            response["error"] = settings.ERROR_MSG["application_error"].format(
                str(err), self.__log.error(self.__exception.get_exception())
            )
        return response


    def __tax_calculation_old_regime(self, emp_id, amount):
        response = {"error": None, 'tax_amount': -1}
        try:
            user_data = { 'id': 0, 'age': 18}
            user_data = UserDA().get_user_profile_by_id(emp_id)
            if user_data:
                user_data = { 'id': user_data.user_id, 'age': self.calculate_age(user_data.dob) }

            amount = float(amount)

            tax_amount = 0
            if amount >= 0 and amount <= 250000:
                tax_amount = 0
            elif amount >= 250001 and amount <= 300000:
                tax_amount = 0.05*(amount-250000) if user_data['age'] < 60 else 0
            elif amount >= 300001 and amount <= 500000:
                tax_amount = 0.05*50000 if user_data['age'] < 60 else 0

                tax_amount += 0.05*(amount-300000) if user_data['age'] < 80 else 0
            elif amount >= 500001 and amount <= 1000000:
                tax_amount = 0.05*50000 if user_data['age'] < 60 else 0
                tax_amount += 0.05*200000 if user_data['age'] < 80 else 0
                tax_amount += 0.2*(amount-500000)
            elif amount >= 1000001:
                tax_amount = 0.05*50000 if user_data['age'] < 60 else 0
                tax_amount += 0.05*200000 if user_data['age'] < 80 else 0
                tax_amount += 0.2*500000
                tax_amount += 0.3*(amount-1000000)
            response['tax_amount'] = f"{float(tax_amount):.2f}"
        except Exception as err:
            response["error"] = settings.ERROR_MSG["application_error"].format(
                str(err), self.__log.error(self.__exception.get_exception())
            )
        return response


    def __tax_calculation_new_regime(self, amount):
        response = {"error": None, 'tax_amount': ''}
        try:
            # tax_amount = 0
            # amount = float(amount)
            # if amount >= 0 and amount <= 300000:
            #     tax_amount = 0
            # elif amount >= 300001 and amount <= 600000:
            #     tax_amount = 0.05*(amount-300000)
            # elif amount >= 600001 and amount <= 900000:
            #     tax_amount = 0.05*300000 + 0.1*(amount-600000)
            # elif amount >= 900001 and amount <= 1200000:
            #     tax_amount = 0.05*300000 + 0.1*300000 + 0.15*(amount-900000)
            # elif amount >= 1200001 and amount <= 1500000:
            #     tax_amount = 0.05*300000 + 0.1*300000 + 0.15*300000 + 0.2*(amount-1200000)
            # elif amount >= 1500001:
            #     tax_amount = 0.05*300000 + 0.1*300000 + 0.15*300000 + 0.2*300000 + 0.3*(amount-1500000)

            #*********************
            tax_amount = 0
            amount = float(amount)
            if amount >= 0 and amount <= 300000:
                tax_amount = 0
            elif amount >= 300001 and amount <= 600000:
                tax_amount = 0.05*(amount-300000)
            elif amount >= 600001 and amount <= 700000:
                tax_amount =  0.05*(amount-300000) #0.05*300000 + 0.05*(amount-600000)
            elif amount >= 700001 and amount <= 900000:
                tax_amount = 0.05*300000 + 0.05*100000 + 0.1*(amount-700000)            
            elif amount >= 900001 and amount <= 1000000:
                tax_amount = 0.05*300000 + 0.05*100000 + 0.1*(amount-700000)
            elif amount >= 1000001 and amount <= 1200000:
                tax_amount = 0.05*300000 + 0.05*100000 + 0.1*300000 + 0.15*(amount-1000000)
            elif amount >= 1200001 and amount <= 1500000:
                tax_amount = 0.05*300000 + 0.05*100000 + 0.1*300000 + 0.15*200000 + 0.2*(amount-1200000)
            elif amount >= 1500001:
                tax_amount =0.05*300000 + 0.05*100000 + 0.1*300000 + 0.15*200000 + 0.2*300000 + 0.3*(amount-1500000)

            response['tax_amount'] = f"{float(tax_amount):.2f}"
        except Exception as err:
            response["error"] = settings.ERROR_MSG["application_error"].format(
                str(err), self.__log.error(self.__exception.get_exception())
            )
        return response


    def __get_surcharges(self, total_income):
        surcharge = 0
        try:
            total_income = float(total_income)
            if total_income > 50000000:
                surcharge = total_income*0.37
            elif total_income > 20000000:
                surcharge = total_income*0.25
            elif total_income > 10000000:
                surcharge = total_income*0.15
            elif total_income > 5000000:
                surcharge = total_income*0.10

        except Exception as err:
            self.__log.error(self.__exception.get_exception())
        return surcharge

    def calculate_age(self, birth_date):
        today = datetime.now()
        age = today.year - birth_date.year - ((today.month, today.day) < (birth_date.month, birth_date.day))
        return age

    def is_amount_valid(self, value):
        pattern = r"^[0-9]+(\.[0-9]{2})?$"
        return bool(re.match(pattern, value))


    def tax_pdf_generation_data(self, emp_id, fin_year_id, claim_type):
        response = {"error": None}
        try:
            tax_period = TaxDA().get_tax_period_from_financial_year_id(fin_year_id)#.id
            if not tax_period:
                response['success'] = False
                response['error'] = "We are currently unable to identify the tax period for the financial year."
                return response

            tax_period_id = tax_period.id
            obj_regime_type = TaxDA().get_regime_type_by_tax_period_user_id(tax_period_id, emp_id)#.regime_type
            if not obj_regime_type:
                response['success'] = False
                response['error'] = "We are unable to determine the user's tax regime, preventing us from proceeding with the tax computation. Please contact the accounting department for assistance"
                return response

            regime_type = obj_regime_type.regime_type
            self.regime_type = 'old' if regime_type == 1 else ("new" if regime_type == 2 else None)

            tds_data = list(TaxDA().get_employee_tds_by_fin_year_id(emp_id, fin_year_id).values_list('amount', flat=True))
            tds_data = list(map(lambda x: 0 if x in [None, ''] else x, tds_data))
            tds_sum = sum(tds_data)

            """*********************Gross Salary******************"""

            #Salary as per provisions contained in section 17(1)
            gross_salary_sec_17_1 = self.__get_gross_salary_sec_17_1(emp_id, fin_year_id)
            if gross_salary_sec_17_1['error'] is not None:
                response['success'] = False
                response['error'] = gross_salary_sec_17_1['error']
                return response
            else:
                gross_salary_sec_17_1 = gross_salary_sec_17_1['amount']

            #Reported total amount of salary received from other employer(s)
            reported_total_salary_from_other_employer = self.__get_reported_total_salary_from_other_employer(emp_id, fin_year_id, 'other_employer')
            reported_total_salary_from_other_employer = 0 if reported_total_salary_from_other_employer['error'] is not None else \
                                                        reported_total_salary_from_other_employer['amount']

            perquisites_value_sec_17_2 = self.__get_perquisites_value_sec_17_2(emp_id, fin_year_id, 'section 17(2)')
            perquisites_value_sec_17_2 = 0 if perquisites_value_sec_17_2['error'] is not None else perquisites_value_sec_17_2['amount']

            profits_lieu_sec_17_3 = self.__get_profits_lieu_sec_17_3(emp_id, fin_year_id, 'section 17(3)')
            profits_lieu_sec_17_3 = 0 if profits_lieu_sec_17_3['error'] is not None else profits_lieu_sec_17_3['amount']

            """**************Less : Allowances to the extent exempt under section 10***************"""


            #Travel concession
            travel_concession_sec_10_5 = self.__get_travel_concessions_assistance_sec_10_5(emp_id, fin_year_id)
            travel_concession_sec_10_5 = 0 if travel_concession_sec_10_5['error'] is not None else travel_concession_sec_10_5['amount']

            #Death-cum-retirement gratuity under section 10(10)
            gratuity_sec_10_10 = self.__get_gratuity_sec_10_10(emp_id, fin_year_id, 'section 10(10)')
            gratuity_sec_10_10 = 0 if gratuity_sec_10_10['error'] else gratuity_sec_10_10['amount']

            #Commuted value of pension under section 10(10A)
            pension_sec_10_10_a = self.__get_pension_sec_10_10_a(emp_id, fin_year_id, 'section 10(10A)')
            pension_sec_10_10_a = 0 if pension_sec_10_10_a['error'] else pension_sec_10_10_a['amount']

            #Cash equivalent of leave salary encashment under section 10(10AA
            leave_salary_encashment_sec_10_10_aa = self.__get_leave_salary_encashment_sec_10_10_aa(emp_id, fin_year_id)
            leave_salary_encashment_sec_10_10_aa = 0 if leave_salary_encashment_sec_10_10_aa['error'] is not None \
                                                   else leave_salary_encashment_sec_10_10_aa['amount']

            #HRA
            hra_exemption_sec_10_13_a = self.__get_hra_exemption_sec_10_13_a(emp_id, fin_year_id, tax_period_id, claim_type)
            hra_exemption_sec_10_13_a = 0 if hra_exemption_sec_10_13_a['error'] else hra_exemption_sec_10_13_a['amount']

            #Total amount of any other exemption under section 10
            other_exemption_sec_10 = self.__get_other_exemption_amount_sec_10(emp_id, fin_year_id)
            other_exemption_sec_10 = 0 if other_exemption_sec_10['error'] else other_exemption_sec_10['amount']

            total_other_exemption_sec_10 = self.__get_total_other_exemption_sec_10(emp_id, fin_year_id)
            total_other_exemption_sec_10 = 0 if total_other_exemption_sec_10['error'] else total_other_exemption_sec_10['amount']

            """************************** 4  Less: Deductions under section 16****************"""

            #Standard deduction under section 16(ia)
            standard_deduction_sec_16_ia = self.__get_standard_deduction_sec_16_ia(emp_id, fin_year_id, self.regime_type)
            standard_deduction_sec_16_ia = 0 if standard_deduction_sec_16_ia['error'] else standard_deduction_sec_16_ia['amount']

            #Entertainment allowance under section 16(ii)
            entertainment_allowance_sec_16_ii = self.__get_entertainment_allowance_sec_16_ii(emp_id, fin_year_id, 'section 16(ii)')
            entertainment_allowance_sec_16_ii = 0 if entertainment_allowance_sec_16_ii['error'] else entertainment_allowance_sec_16_ii['amount']

            #Tax on employment under section 16(iii)
            employment_tax_sec_16_iii = self.__get_employment_tax_sec_16_iii(emp_id, fin_year_id)
            employment_tax_sec_16_iii = 0 if employment_tax_sec_16_iii['error'] else employment_tax_sec_16_iii['amount']

            """******************** 7 Add: Any other income reported by the employee under as per section 192 (2B) *************"""

            #Income (or admissible loss) from house property reported by employee offered for TDS
            house_property_income = self.__get_deductions_under_chapter_vi_a('section_24', emp_id, tax_period_id, claim_type)
            house_property_income = 0 if house_property_income['error'] else house_property_income['amount']
            if house_property_income:
                house_property_income = house_property_income * -1

            #Income under the head Other Sources offered for TDS
            head_other_sources_income = self.__get_head_other_sources_income(emp_id, fin_year_id)
            head_other_sources_income = 0 if head_other_sources_income['error'] else head_other_sources_income['amount']

            """************************ 10 Deductions under Chapter VI-A **********************"""

            #Employee PF            
            emp_pf_amt = self.__get_employee_pf(emp_id, fin_year_id)
            emp_pf_amt = 0 if emp_pf_amt['error'] else emp_pf_amt['amount']

            # 80C
            deduction_sec_80_c = self.__get_deductions_under_chapter_vi_a('80C', emp_id, tax_period_id, claim_type)
            deduction_sec_80_c = 0 if deduction_sec_80_c['error'] else deduction_sec_80_c['amount']

            try:
                deduction_sec_80_c = float(str(deduction_sec_80_c)) + float(str(emp_pf_amt))
                if deduction_sec_80_c > 150000:
                    deduction_sec_80_c = 150000             
            except Exception as err:                
                self.__log.error(str(err))
                self.__log.error(self.__exception.get_exception())            

            # 80CCC
            deduction_sec_80_ccc = self.__get_deductions_under_chapter_vi_a('80CCC', emp_id, tax_period_id, claim_type)
            deduction_sec_80_ccc = 0 if deduction_sec_80_ccc['error'] else deduction_sec_80_ccc['amount']

            # 80CCD
            deduction_sec_80_ccd = self.__get_deductions_under_chapter_vi_a('80CCD', emp_id, tax_period_id, claim_type)
            deduction_sec_80_ccd = 0 if deduction_sec_80_ccd['error'] else deduction_sec_80_ccd['amount']

            # 80CCD (1)
            deduction_sec_80_ccd_1 = self.__get_deductions_under_chapter_vi_a('80CCD(1)', emp_id, tax_period_id, claim_type)
            deduction_sec_80_ccd_1 = 0 if deduction_sec_80_ccd_1['error']  else deduction_sec_80_ccd_1['amount']

            #80CCD (2)
            deduction_sec_80_ccd_2 = self.__get_deductions_under_chapter_vi_a('80CCD(2)', emp_id, tax_period_id, claim_type)
            deduction_sec_80_ccd_2 = 0 if deduction_sec_80_ccd_2['error']else deduction_sec_80_ccd_2['amount']

            #80CCD (1B)
            deduction_sec_80_ccd_1b = self.__get_deductions_under_chapter_vi_a('80CCD(1B)', emp_id, tax_period_id, claim_type)
            deduction_sec_80_ccd_1b = 0 if deduction_sec_80_ccd_1b['error'] else deduction_sec_80_ccd_1b['amount']

            #80 D
            deduction_sec_80_d = self.__get_deductions_under_chapter_vi_a('80D', emp_id, tax_period_id, claim_type)
            deduction_sec_80_d = 0 if deduction_sec_80_d['error'] else deduction_sec_80_d['amount']

            #80 E
            deduction_sec_80_e = self.__get_deductions_under_chapter_vi_a('80E', emp_id, tax_period_id, claim_type)
            deduction_sec_80_e = 0 if deduction_sec_80_e['error']  else deduction_sec_80_e['amount']

            # 80G
            deduction_sec_80_g = self.__get_deductions_under_chapter_vi_a('80G', emp_id, tax_period_id, claim_type)
            deduction_sec_80_g = 0 if deduction_sec_80_g['error']  else deduction_sec_80_g['amount']

            #80 TTA
            deduction_sec_80_tta = self.__get_deductions_under_chapter_vi_a('80TTA', emp_id, tax_period_id, claim_type)
            deduction_sec_80_tta = 0 if deduction_sec_80_tta['error'] else deduction_sec_80_tta['amount']

            #80EEA
            deduction_sec_80_eea = self.__get_deductions_under_chapter_vi_a('80EEA', emp_id, tax_period_id, claim_type)
            deduction_sec_80_eea = 0 if deduction_sec_80_eea['error'] else deduction_sec_80_eea['amount']

            #80EEB
            deduction_sec_80_eeb = self.__get_deductions_under_chapter_vi_a('80EEB', emp_id, tax_period_id, claim_type)
            deduction_sec_80_eeb = 0 if deduction_sec_80_eeb['error'] else deduction_sec_80_eeb['amount']

            #80DD
            deduction_sec_80_dd = self.__get_deductions_under_chapter_vi_a('80DD', emp_id, tax_period_id, claim_type)
            deduction_sec_80_dd = 0 if deduction_sec_80_dd['error'] else deduction_sec_80_dd['amount']

            #80EEB
            deduction_sec_80_ddb = self.__get_deductions_under_chapter_vi_a('80DDB', emp_id, tax_period_id, claim_type)
            deduction_sec_80_ddb = 0 if deduction_sec_80_ddb['error'] else deduction_sec_80_ddb['amount']

            # total_deduction_80_c_80_ccc_80_ccd_1 = deduction_sec_80_c + deduction_sec_80_ccc + deduction_sec_80_ccd_1
            total_deduction_80_c_80_ccc_80_ccd_1 = 0

            #Amount deductible under any other provision(s) of Chapter VI-A
            other_provisions_chapter_vi_a = self.__get_deductions_under_other_provisions_chapter_vi_a(emp_id, fin_year_id)
            other_provisions_chapter_vi_a = 0 if other_provisions_chapter_vi_a['error'] else other_provisions_chapter_vi_a['amount']

            ##Relief under section 89
            relief_sec_89 = self.__get_relief_sec_89(emp_id, fin_year_id)
            relief_sec_89 = 0 if relief_sec_89['error'] else relief_sec_89['amount']


            """ ******************Dict preparation Start Here*****************************************"""

            #1 : Gross Salary
            gross_salary_sec_details_dict = self.__dict_gen.get_gross_salary_sec_details_dict(
                gross_salary_sec_17_1=gross_salary_sec_17_1,
                perquisites_value_sec_17_2=perquisites_value_sec_17_2,
                profits_lieu_sec_17_3=profits_lieu_sec_17_3,
                reported_total_salary_from_other_employer=reported_total_salary_from_other_employer)
            if gross_salary_sec_details_dict['error']:
                response['error'] = gross_salary_sec_details_dict['error']
                return response



            #2 :Allowances to the extent exempt under section 10
            allowances_extent_exempt_sec_10_details_dict = self.__dict_gen.get_allowances_extent_exempt_sec_10_details_dict(
                travel_concession_sec_10_5=travel_concession_sec_10_5,
                pension_sec_10_10_a=pension_sec_10_10_a, gratuity_sec_10_10=gratuity_sec_10_10,
                leave_salary_encashment_sec_10_10_aa=leave_salary_encashment_sec_10_10_aa,
                hra_exemption_sec_10_13_a=hra_exemption_sec_10_13_a,
                other_exemption_sec_10=other_exemption_sec_10,
                # total_other_exemption_sec_10=total_other_exemption_sec_10
            )
            if allowances_extent_exempt_sec_10_details_dict['error'] is not None:
                response['error'] = allowances_extent_exempt_sec_10_details_dict['error']
                return response

            #3 : Total amount of salary received from current employer [1(d)-2(h)]
            total_salary_amount_from_current_employer_details_dict = self.__dict_gen.get_total_salary_amount_from_current_employer_details_dict(
                gross_total = float(gross_salary_sec_details_dict['data']['sub_items'][4]['deductable_amount']),
                allowances_sec_10_total = float(allowances_extent_exempt_sec_10_details_dict['data']['sub_items'][8]['deductable_amount']))
            if total_salary_amount_from_current_employer_details_dict['error'] is not None:
                response['error'] = total_salary_amount_from_current_employer_details_dict['error']
                return response

            #4 Less: Deductions under section 16
            deductions_under_sec_16_details_dict = self.__dict_gen.get_deductions_sec_16_details_dict(
                standard_deduction_sec_16_ia=standard_deduction_sec_16_ia,
                entertainment_allowance_sec_16_ii=entertainment_allowance_sec_16_ii,
                employment_tax_sec_16_iii=employment_tax_sec_16_iii
            )
            if deductions_under_sec_16_details_dict['error'] is not None:
                response['error'] = deductions_under_sec_16_details_dict['error']
                return response


            # 5: Total amount of deductions under section 16 [4(a)+4(b)+4(c)]
            total_deductions_sec_16_details_dict = self.__dict_gen.get_total_deductions_sec_16_details_dict(
                standard_deduction_sec_16_ia=standard_deduction_sec_16_ia,
                entertainment_allowance_sec_16_ii=entertainment_allowance_sec_16_ii,
                employment_tax_sec_16_iii=employment_tax_sec_16_iii
            )
            if total_deductions_sec_16_details_dict['error'] is not None:
                response['error'] = total_deductions_sec_16_details_dict['error']
                return response

            # 6. Income chargeable under the head "Salaries" [(3+1(e)-5]
            income_interchangeable_under_head_salaries_details_dict = self.__dict_gen.get_income_interchangeable_under_head_salaries_details_dict(
                salary_from_current_employer = float(total_salary_amount_from_current_employer_details_dict['data']['deductable_amount']),
                gross_salary = float(gross_salary_sec_details_dict['data']['sub_items'][5]['deductable_amount']),
                total_deductions_sec_16 = float(total_deductions_sec_16_details_dict['data']['deductable_amount']))
            if income_interchangeable_under_head_salaries_details_dict['error'] is not None:
                response['error'] = income_interchangeable_under_head_salaries_details_dict['error']
                return response

            #7 Add: Any other income reported by the employee under as per section 192 (2B)
            other_income_reported_sec_192_2B_dict = self.__dict_gen.get_other_income_reported_by_employee_under_sec_192_2B_details_dict(
                house_property_income=house_property_income,
                head_other_sources_income=head_other_sources_income
            )
            if other_income_reported_sec_192_2B_dict['error'] is not None:
                response['error'] = other_income_reported_sec_192_2B_dict['error']
                return response

            #8 Total amount of other income reported by the employee [7(a)+7(b)]
            total_income_reported_by_employee_dict = self.__dict_gen.get_total_other_income_reported_by_employee_details_dict(
                house_property_income=house_property_income,
                head_other_sources_income=head_other_sources_income
            )
            if total_income_reported_by_employee_dict['error'] is not None:
                response['error'] = total_income_reported_by_employee_dict['error']
                return response

            #9 Gross total income (6+8)
            gross_total_income_dict = self.__dict_gen.get_gross_total_income_details_dict(
                income_interchangeable=float(income_interchangeable_under_head_salaries_details_dict['data']['deductable_amount']),
                total_income_reported=float(total_income_reported_by_employee_dict['data']['deductable_amount'])
            )
            if gross_total_income_dict['error'] is not None:
                response['error'] = gross_total_income_dict['error']
                return response

            # 10 Deductions under Chapter VI-A
            deductions_under_chapter_vi_a_dict = self.__dict_gen.get_deductions_under_chapter_vi_a_dict(
                deduction_sec_80_c=deduction_sec_80_c,
                deduction_sec_80_ccc=deduction_sec_80_ccc,
                deduction_sec_80_ccd=deduction_sec_80_ccd,
                deduction_sec_80_e=deduction_sec_80_e,
                deduction_sec_80_g=deduction_sec_80_g,
                deduction_sec_80_tta=deduction_sec_80_tta,
                deduction_sec_80_d=deduction_sec_80_d,
                deduction_sec_80_ccd_1=deduction_sec_80_ccd_1,
                deduction_sec_80_ccd_2=deduction_sec_80_ccd_2,
                deduction_sec_80_ccd_1b=deduction_sec_80_ccd_1b,
                other_provisions_chapter_vi_a=other_provisions_chapter_vi_a,
                deduction_sec_80_eea=deduction_sec_80_eea,
                deduction_sec_80_eeb=deduction_sec_80_eeb,
                deduction_sec_80_dd=deduction_sec_80_dd,
                deduction_sec_80_ddb=deduction_sec_80_ddb,
            )
            if deductions_under_chapter_vi_a_dict['error'] is not None:
                response['error'] = deductions_under_chapter_vi_a_dict['error']
                return response

            #11 Aggregate of deductible amount under Chapter VI-A
            aggregate_deductable_amount_dict = self.__dict_gen.get_aggregate_deductable_income_chapter_vi_a_dict(
                deductions_sec_80_c=deduction_sec_80_c,
                deduction_sec_80_ccc=deduction_sec_80_ccc,
                deduction_sec_80_ccd_1=deduction_sec_80_ccd_1,
                deduction_sec_80_ccd_1b=deduction_sec_80_ccd_1b,
                deduction_sec_80_ccd_2=deduction_sec_80_ccd_2,
                deduction_sec_80_d=deduction_sec_80_d,
                deduction_sec_80_e=deduction_sec_80_e,
                deduction_sec_80_g=deduction_sec_80_g,
                deduction_sec_80_tta=deduction_sec_80_tta,
                other_provisions_chapter_vi_a=other_provisions_chapter_vi_a,
                total_deduction_80_c_80_ccc_80_ccd_1=total_deduction_80_c_80_ccc_80_ccd_1
            )
            if aggregate_deductable_amount_dict['error'] is not None:
                response['error'] = aggregate_deductable_amount_dict['error']
                return response

            # 12 Total taxable income (9-11)
            total_taxable_income = 0
            total_taxable_income_dict = self.__dict_gen.get_total_taxable_income_dict(
                gross_total_income=float(gross_total_income_dict['data']['deductable_amount']),
                aggregate_deductable_amount=float(aggregate_deductable_amount_dict['data']['deductable_amount']))


            if total_taxable_income_dict['error'] is not None:
                response['error'] = total_taxable_income_dict['error']
                return response

            total_taxable_income = float(total_taxable_income_dict['data']['deductable_amount'])


            """*****************Rebate under section 87A***************************************"""
            rebate_sec_87_a = self.__get_rebate_sec_87_a(total_taxable_income)
            rebate_sec_87_a = 0 if rebate_sec_87_a['error'] else rebate_sec_87_a['amount']


            if regime_type == 2:
                tax_total_income_response = self.__tax_calculation_new_regime(total_taxable_income_dict['data']['deductable_amount'])
                tax_total_income = tax_total_income_response['tax_amount']
            else:
                tax_total_income_response = self.__tax_calculation_old_regime(emp_id, total_taxable_income_dict['data']['deductable_amount'])
                tax_total_income = tax_total_income_response['tax_amount']

            if tax_total_income_response['error'] is not None:
                response['error'] = tax_total_income_response['error']
                return response

            # 13 Tax on total income
            tax_total_income_dict = self.__dict_gen.get_tax_total_income_dict(tax_total_income=tax_total_income)
            if tax_total_income_dict['error'] is not None:
                response['error'] = tax_total_income_dict['error']
                return response

            # 14 Rebate under section 87A, if applicable
            rebate_sec_87_a_dict = self.__dict_gen.get_rebate_sec_87_a_dict(rebate_sec_87_a=rebate_sec_87_a)
            if rebate_sec_87_a_dict['error'] is not None:
                response['error'] = rebate_sec_87_a_dict['error']
                return response

            # 15 Surcharge, wherever applicable
            total_income = float(total_taxable_income_dict['data']['deductable_amount'])
            surcharge = self.__get_surcharges(total_income)
            surcharge_dict = self.__dict_gen.get_surcharge_dict(surcharge)
            if surcharge_dict['error'] is not None:
                response['error'] = surcharge_dict['error']
                return response

            # 16 Health and education cess
            tax_on_total_income = float(tax_total_income_dict['data']['deductable_amount'])
            health_education_cess = 0.04 * (surcharge + tax_on_total_income)
            health_education_cess_dict = self.__dict_gen.get_health_education_cess_dict(health_education_cess)
            if health_education_cess_dict['error'] is not None:
                response['error'] = health_education_cess_dict['error']
                return response

            #17 Tax payable (13+15+16-14)
            tax_payable_dict = self.__dict_gen.get_tax_payable_dict(
                tax_total_income=tax_total_income_dict['data']['deductable_amount'],
                surcharge=surcharge_dict['data']['deductable_amount'],
                health_education_cess=health_education_cess_dict['data']['deductable_amount'],
                rebate_sec_87_a=rebate_sec_87_a_dict['data']['deductable_amount'])
            if tax_payable_dict['error'] is not None:
                response['error'] = tax_payable_dict['error']
                return response

            # 18 Less: Relief under section 89 (attach details)
            relief_sec_89_dict = self.__dict_gen.get_relief_sec_89_dict(relief_sec_89=relief_sec_89)
            if relief_sec_89_dict['error'] is not None:
                response['error'] = relief_sec_89_dict['error']
                return response

            #19 Net tax payable (17-18)
            net_tax_payable_dict = self.__dict_gen.get_net_tax_payable_dict(
                tax_payable=tax_payable_dict['data']['deductable_amount'],
                relief_sec_89=relief_sec_89_dict['data']['deductable_amount'])
            if net_tax_payable_dict['error'] is not None:
                response['error'] = net_tax_payable_dict['error']
                return response

            #20 Tax Paid Till Now
            tax_paid_till_now_dict = self.__dict_gen.get_tax_paid_till_now_dict(tds_sum=tds_sum)
            if tax_paid_till_now_dict['error'] is not None:
                response['error'] = tax_paid_till_now_dict['error']
                return response

            remaining_tax_to_be_paid_dict = self.__dict_gen.get_remaining_tax_to_be_paid_dict(tax_paid_till_now=tax_paid_till_now_dict['data']['deductable_amount'],
                                                                                             net_tax_payable=net_tax_payable_dict['data']['deductable_amount'])
            if remaining_tax_to_be_paid_dict['error'] is not None:
                response['error'] = remaining_tax_to_be_paid_dict['error']
                return response

            current_month = datetime.now().month
            month_list = settings.FIN_YEAR_MONTH_ORDER_LIST
            current_month_pos = month_list.index(current_month)
            remaining_months = month_list[current_month_pos:]
            remaining_month_count = len(remaining_months)
            estimated_tds_to_be_deducted_in_future_dict = self.__dict_gen.get_estimated_tds_to_be_deducted_in_future_dict(remaining_tax_to_be_paid=remaining_tax_to_be_paid_dict['data']['deductable_amount'],
                                                                                             remaining_month_count=remaining_month_count)
            if remaining_tax_to_be_paid_dict['error'] is not None:
                response['error'] = remaining_tax_to_be_paid_dict['error']
                return response

            data_dict = {
                1 : gross_salary_sec_details_dict['data'],
                2 : allowances_extent_exempt_sec_10_details_dict['data'],
                3 : total_salary_amount_from_current_employer_details_dict['data'],
                4 : deductions_under_sec_16_details_dict['data'],
                5 : total_deductions_sec_16_details_dict['data'],
                6 : income_interchangeable_under_head_salaries_details_dict['data'],
                7 : other_income_reported_sec_192_2B_dict['data'],
                8 : total_income_reported_by_employee_dict['data'],
                9 : gross_total_income_dict['data'],
                10 : deductions_under_chapter_vi_a_dict['data'],
                11 : aggregate_deductable_amount_dict['data'],
                12 : total_taxable_income_dict['data'],
                13 : tax_total_income_dict['data'],
                14 : rebate_sec_87_a_dict['data'],
                15 : surcharge_dict['data'],
                16 : health_education_cess_dict['data'],
                17 : tax_payable_dict['data'],
                18 : relief_sec_89_dict['data'],
                19 : net_tax_payable_dict['data'],
                20 : tax_paid_till_now_dict['data'],
                21 : remaining_tax_to_be_paid_dict['data'],
                22 : estimated_tds_to_be_deducted_in_future_dict['data'],
            }

            response['data'] = data_dict
            response['tds_data'] = tds_data
        except Exception as err:
            response["error"] = settings.ERROR_MSG["application_error"].format(
                str(err), self.__log.error(self.__exception.get_exception())
            )
        return response



    def __is_valid_financial_year(self, financial_year_id):
        is_fyi_valid = FinanaceDA().get_financial_year_by_id(financial_year_id)
        if is_fyi_valid:
            return True
        else:
            return False


    def __is_valid_user_id(self, user_id):
        is_user_valid = UserDA().get_user_by_id(user_id)
        if is_user_valid.is_active == 1:
            return True
        else:
            return False