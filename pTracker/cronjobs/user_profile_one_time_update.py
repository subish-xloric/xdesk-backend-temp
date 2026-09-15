from django.conf import settings
from django.db import  transaction
from datetime import datetime
from cryptography.fernet import Fernet

from pTracker.common.utility import Utility
from pTracker.common.exception_handler import ExceptionHandler
from pTracker.common.logs import Logs

from pTracker.dataaccess.ptracker_access.user_models import UserProfile
from pTracker.dataaccess.ptracker_access.user_da import UserDA
from pTracker.dataaccess.ptracker_access.finance_da import FinanaceDA
from pTracker.dataaccess.ptracker_access.tax_da import TaxDA

import csv
import base64

class TestDBUpdate:

    def __init__(self):
        self.__log = Logs()
        self.__exception = ExceptionHandler()
        self.__utility = Utility()
        self.cipher_suite = Fernet(settings.FERNET_KEY)

    # def update_user_profiles_from_csv(self,csv_file_path):

    #     response = {"success": ''}
    #     try:
    #         # Open the CSV file
    #         with open(csv_file_path, 'r') as csvfile:
    #             csv_reader = csv.DictReader(csvfile)

    #             with transaction.atomic():
    #                 for row in csv_reader:
    #                     employee_code = row['employee_code']
    #                     new_pan = row['pan']
    #                     new_father_name = row['father_name']
    #                     user = UserDA().get_user_by_emp_id(employee_code)

    #                     if user:
    #                         is_update = UserProfile.objects.filter(user_id=user.id).update(
    #                             pan=new_pan,
    #                             father_name=new_father_name
    #                         )
    #                     response['success'] = True
    #     except Exception as err:
    #         response["error"] = settings.ERROR_MSG['application_error'].format(
    #             str(err), self.__log.error(self.__exception.get_exception())
    #         )
    #     return response


    # def update_ctc_employee_from_csv(self, request, csv_file_path):
    #     response = {"success": ''}
    #     user_id = request.user.id
    #     user_dict = {}
    #     ctc_emp_data = []

    #     try:
    #         with open(csv_file_path, 'r') as csvfile:
    #             csv_reader = csv.DictReader(csvfile)
    #             current_fyd = FinanaceDA().get_financial_year_by_date(datetime.now())
    #             with transaction.atomic():
    #                 ctc_details_list = TaxDA().get_ctc_master()

    #                 for row in csv_reader:
    #                     employee_code = row['employee_code']
    #                     if employee_code not in user_dict:
    #                         user = UserDA().get_user_by_emp_id(employee_code)
    #                         if user:
    #                             user_dict[employee_code] = user
    #                         else:
    #                             continue
    #                     else:
    #                         user = user_dict[employee_code]

    #                     COLUMN_NAMES = ['basic', 'hra', 'conveyance', 'sp_allowance', 'bonus', 'pf', \
    #                         'wel_fund', 'emp_wel_fund']

    #                     for counter, column in enumerate(COLUMN_NAMES):
    #                         amount = row[column]
    #                         ctc_emp_data.append({
    #                             'fin_yr_id': current_fyd.financial_year_id,
    #                             'emp_id': user.id,
    #                             'ctc_id': ctc_details_list[counter].ctc_id,
    #                             'created_by': user_id,
    #                             'amount': self.__encrypt_ctc(amount)
    #                         })
    #                 bulk_create_ctc_emp = TaxDA().bulk_create_ctc_employee(ctc_emp_data)
    #                 response["success"] = "CTC employees updated successfully."
    #     except Exception as err:
    #         response["error"] = settings.ERROR_MSG['application_error'].format(
    #             str(err), self.__log.error(self.__exception.get_exception())
    #         )
    #     return bulk_create_ctc_emp


    def __encrypt_ctc(self, value):

        try:
            value_bytes = str(value).encode('utf-8')
            encrypted_value = self.cipher_suite.encrypt(value_bytes)
            encrypted_value_base64 = base64.b64encode(encrypted_value).decode('utf-8')
        except Exception as err:
            encrypted_value_base64 = settings.ERROR_MSG['application_error'].format(
                str(err), self.__log.error(self.__exception.get_exception())
            )
        return encrypted_value_base64
