import uuid
import json
from datetime import datetime
from types import SimpleNamespace

from django.http import HttpResponse
from django.db import  transaction
from cryptography.fernet import Fernet
from django.conf import Settings, settings

from pTracker.common.utility import Utility
from pTracker.common.exception_handler import ExceptionHandler
from pTracker.common.logs import Logs
from pTracker.common.file_manager import FileManager
from pTracker.dataaccess.ptracker_access.user_da import UserDA
from pTracker.dataaccess.ptracker_access.finance_da import FinanaceDA
from pTracker.dataaccess.ptracker_access.tax_da import TaxDA
from itertools import product
import os
import re
import base64
import csv


def new_dto():
    dto = SimpleNamespace()
    return dto

class EmployeeCtcBL():
    def __init__(self):
        self.__log = Logs()
        self.__exception = ExceptionHandler()
        self.__utility = Utility()
        self.__file_manager = FileManager()
        self.cipher_suite = Fernet(settings.FERNET_KEY)


    def get_employees_ctc(self, request, fin_year_id, org_id):
        response = {"error": None, "emp_list": None, 'status':200}
        emp_dict = {}
        total_earnings = 0
        total_deductions = 0
        emp_list = []

        try:
            user_id = request.user.id
            is_permitted = self.__utility.is_permitted(user_id, 'can_manage_ctc')
            if not is_permitted:
                response['is_manager'] = False
                response["error"] = settings.ERROR_MSG.get('access_denied')
                response['status'] = 403
                return response

            #is_manager = True

            fin_year = FinanaceDA().get_financial_year_by_id(fin_year_id)
            if not fin_year:
                response["error"] = "You have tried an invalid financial year."
                response['status'] = 499
                return response

            if org_id not in(3,2,'3','2'):
                response["error"] = "You have tried an invalid organization."
                response["status"] = 499
                return response

            role_id, name = UserDA().get_user_role_by_id(user_id)
            if role_id in (3,2,1):
                is_manager = True
            else:
                is_manager = False

            fin_year_desc = fin_year.description

            ctc_employee = TaxDA().get_all_employees_ctc_by_fin_year(fin_year_id)
            if ctc_employee:
                ctc_employee_list = set(ctc_employee.values_list('emp_id', flat=True))

                user_profiles_obj = UserDA().get_user_profiles_by_employee_ids(ctc_employee_list).filter(company_id=org_id)
                user_profiles = user_profiles_obj.values_list('user_id', flat=True)
                active_users = UserDA().get_all_users().filter(id__in=user_profiles)
                user_dict = {user.id: user for user in active_users}

                ctc_master_details = TaxDA().get_ctc_master()
                categories_earnings = ctc_master_details.filter(type='Earning').values_list('ctc_id', flat=True)
                ctc_master_dict = {ctc_master.ctc_id: ctc_master.name for ctc_master in ctc_master_details}

                for ctc_emp in ctc_employee:
                    if ctc_emp.emp_id not in user_dict:
                        continue
                    user = user_dict[ctc_emp.emp_id]
                    dec_amount = self.__decrypt_ctc(ctc_emp.amount)
                    amount_as_int = float(dec_amount)

                    user_id = user.id
                    if user_id not in emp_dict:
                        emp_dict[user_id] = {
                            'emp_name': f"{user.first_name} {user.last_name}",
                            'emp_id': user.username,
                            'user_id': user_id,
                            'fin_year_desc': fin_year_desc,
                            'earnings_total': 0,
                            'deduction_total': 0,
                            'earnings': [],
                            'deduction': [],
                        }

                    emp_entry = emp_dict[user_id]
                    if ctc_emp.ctc_id in categories_earnings:
                        emp_entry['earnings'].append({
                            ctc_emp.emp_ctc_id: {
                                'name': ctc_master_dict.get(ctc_emp.ctc_id, ''),
                                'amount': amount_as_int
                            }
                        })
                        emp_entry['earnings_total'] += amount_as_int
                        total_earnings += amount_as_int
                    else:
                        emp_entry['deduction'].append({
                            ctc_emp.emp_ctc_id: {
                                'name': ctc_master_dict.get(ctc_emp.ctc_id, ''),
                                'amount': amount_as_int
                            }
                        })
                        emp_entry['deduction_total'] += amount_as_int
                        total_deductions += amount_as_int

                emp_list = list(emp_dict.values())

            response['is_manager'] = is_manager
            response['emp_list'] = emp_list

        except Exception as err:
            response["error"] = settings.ERROR_MSG['application_error']\
                .format(err, self.__logs.error(self.__exception.get_exception()))

        return response

    # def create_or_update_ctc_employee(self, request):
    #     response = {"success": [], "message":[], "error":[]}
    #     response['success'] = False
    #     try:
    #         ctc_emps_list = []
    #         user_id = request.user.id
    #         current_fyd = FinanaceDA().get_financial_year_by_date(datetime.now())

    # def create_or_update_ctc_employee(self, request):
    #     response = {"success": [], "message":[], "error":[]}
    #     response['success'] = False
    #     try:
    #         ctc_emps_list = []
    #         user_id = request.user.id
    #         current_fyd = FinanaceDA().get_financial_year_by_date(datetime.now())

    #         with transaction.atomic():
    #             ctc_details_list = [{"ctc_id": ctc.ctc_id} for ctc in TaxDA().get_ctc_master()]
    #             ctc_emps = TaxDA().get_all_details_from_ctc_emp().filter(current_fyd.financial_year_id)
    #             ctc_emps_list = set(ctc_emps.values_list('emp_id', flat=True)) if ctc_emps else set()
    #             ctc_id_list = set(ctc_emps.values_list('ctc_id', flat=True)) if ctc_emps else set()
    #             unmatched_ctc_ids =  set(ctc_details['ctc_id'] for ctc_details in ctc_details_list) - ctc_id_list
    #             if unmatched_ctc_ids:
    #                 users = UserDA().get_all_active_users().filter(id__in=ctc_emps_list)
    #                 ctc_emp_data = [
    #                     {
    #                         'fin_yr_id': current_fyd.financial_year_id,
    #                         'emp_id': user.id,
    #                         'ctc_id': ctc_id,
    #                         'created_by': user_id,
    #                         'amount': self.__encrypt_ctc(value='0')
    #                     }
    #                     for user, ctc_id in product(users, unmatched_ctc_ids)
    #                 ]
    #                 bulk_create_ctc_emp = TaxDA().bulk_create_ctc_employee(ctc_emp_data)
    #                 response['message'] = 'New CTC details are added'

    #             users = UserDA().get_all_active_users().exclude(id__in=ctc_emps_list)
    #             #product to create the cartesian product of user details and ctc details
    #             if users:
    #                 ctc_emp_data = [
    #                     {
    #                     'fin_yr_id': current_fyd.financial_year_id,
    #                     'emp_id': user.id,
    #                     'ctc_id': each_ctc['ctc_id'],
    #                     'created_by': user_id,
    #                     'amount': self.__encrypt_ctc(value='0')
    #                     }
    #                     #to avoid inner loop product using
    #                     for user, each_ctc in product(users, ctc_details_list)
    #                 ]
    #                 bulk_create_ctc_emp = TaxDA().bulk_create_ctc_employee(ctc_emp_data)
    #                 response['success'] = True
    #                 response['message'] = 'Employees added successfully'
    #             else:
    #                 response['success'] = False
    #                 response['error'] = 'No new employees are exist'
    #     except Exception as err:
    #         response["error"] = settings.ERROR_MSG['application_error'].format(
    #             str(err), self.__log.error(self.__exception.get_exception())
    #         )
    #     return response


    def update_employee_ctc(self, request):
        response = {"success": True, "message":[], "error":None}
        response['success'] = False
        ctc_amounts = []
        try:
            request_data = request.data

            user_id = request.user.id
            is_permitted = self.__utility.is_permitted(user_id, 'can_modify_ctc')
            if not is_permitted:
                response["error"] = settings.ERROR_MSG.get('access_denied')
                response['status'] = 403
                return response

            for emp_ctc_id, amount in request_data.items():
                try:
                    emp_ctc_id = int(emp_ctc_id)
                except:
                    continue
                if not self.is_amount_valid(amount):
                    continue
                amount = self.__encrypt_ctc(amount)
                ctc_amounts.append({"emp_ctc_id":emp_ctc_id, "amount":amount})

            #TODO validate Fin year
            TaxDA().update_employee_ctc(ctc_amounts)
            response['success'] = True
            response['message'] = 'The CTC has been successfully updated'
        except Exception as err:
            response["error"] = settings.ERROR_MSG['application_error'].format(
                str(err), self.__log.error(self.__exception.get_exception())
            )
        return response


    def get_ctc_categories(self, request):
        response = {'error': '', 'categories_earnings': [], 'categories_deductions':[]}
        try:
            user_id = request.user.id
            is_permitted = self.__utility.is_permitted(user_id, 'can_manage_ctc')
            if not is_permitted:
                response['is_manager'] = False
                response["error"] = settings.ERROR_MSG.get('access_denied')
                response['status'] = 403
                return response

            role_id, name = UserDA().get_user_role_by_id(user_id)
            if role_id == 3:
                is_manager = True
            else:
                is_manager = False

            categories = TaxDA().get_ctc_master()
            categories_earnings = categories.filter(type='Earning')
            categories_deductions = categories.filter(type='Deduction')
            if categories_earnings:
                response['is_sub'] = True
                response['categories_earnings'] = [
                    {
                        'id': each.ctc_id,
                        'name': each.name,
                        'desc': each.description,
                        'type': each.type,
                    }for each in categories_earnings
                ]
            if categories_deductions:
                response['is_sub'] = True
                response['categories_deductions'] = [
                    {
                        'id': each.ctc_id,
                        'name': each.name,
                        'desc': each.description,
                        'type': each.type,
                    }for each in categories_deductions
                ]
            response['is_manager'] = is_manager
        except Exception as err:
            response["error"] = settings.ERROR_MSG['application_error'].format(
                str(err), self.__log.error(self.__exception.get_exception())
            )
        return response

    
    
    def test_ctc(self):
        
        import csv
        import io
        # Read the CSV file using FileManager
        csv_path = '/var/www/dm_ptracker/backend_app/pTracker/pTracker/api/finance/dm_lop.csv'
        csv_bytes = self.__file_manager.read_file(csv_path)
        if csv_bytes is not None:
            csv_str = csv_bytes.decode('utf-8')
            csvfile = io.StringIO(csv_str)
            reader = csv.reader(csvfile)
    
            # Iterate through the rows
            dict_users = {}
            users = UserDA().get_all_users()

            
            if users:
                for each_user in users:
                    try:
                        dict_users[int(each_user.username)] = each_user.id 
                    except:
                        pass
                    #if each_user.id not in ctc_emps_list: 
                        #user_ids.append(each_user.id)

            ctc_amounts =[]
            for row in reader:
                #print(row)  # Each row is a list of values
                
                
                
                try:
                    emp_id = int(row[1])
                    user_id = dict_users.get(emp_id, 0)
                    lop = int(row[5])
                except:
                    #print('haiiiiiiiiiiiiiii')
                    continue

                lop = self.__encrypt_ctc(row[5])

                ctc_amount = {
                                'fin_yr_id': 2,
                                'emp_id': user_id,
                                'ctc_id': 17,
                                'created_by': 54,
                                'amount': lop #self.__encrypt_ctc(lop)
                            }
                ctc_amounts.append(ctc_amount)
                print('ctc_amount', ctc_amount)
            is_updated = TaxDA().bulk_create_ctc_employee(ctc_amounts)
        
    
    
    def create_employee_ctc(self, request):
        response = {"success": True, "message":[], "error":None}
        response['success'] = False
        ctc_amounts = []
        max_amount = 10000000
        try:
            user_id = request.user.id
            is_permitted = self.__utility.is_permitted(user_id, 'can_modify_ctc')
            if not is_permitted:
                response["error"] = settings.ERROR_MSG.get('access_denied')
                response['status'] = 403
                return response

            request_data = request.data
            emp_id =request_data.get('emp_id')
            selected_fin_year_id = int(request_data.get('SelectedFinYearID'))
            current_fyd = FinanaceDA().get_financial_year_by_date(datetime.now())

            if current_fyd and selected_fin_year_id != current_fyd.financial_year_id:
                response['error'] = 'You can add the CTC exclusively for the current financial year only.'
                return response

            ctc_employee = TaxDA().get_all_details_from_ctc_emp().filter(emp_id=emp_id,fin_yr_id=current_fyd.financial_year_id)
            if ctc_employee:
                response['error'] = 'The CTC for this employee already exists. You may update the amount as needed to align with your requirements.'
                return response

            #TODO a validation on EMP is active
            request_data_items = list(request_data.items())[2:]


            with transaction.atomic():
                for ctc_id, amount in request_data_items:
                    is_amount_valid = self.is_amount_valid(amount)
                    if float(amount) > max_amount or not is_amount_valid:
                        response['error'] = 'Amount exceeds the limit.'
                        return response
                    ctc_amount = {
                        'fin_yr_id': current_fyd.financial_year_id,
                        'emp_id': emp_id,
                        'ctc_id': ctc_id,
                        'created_by': user_id,
                        'amount': self.__encrypt_ctc(amount)
                    }
                    ctc_amounts.append(ctc_amount)
                is_updated = TaxDA().bulk_create_ctc_employee(ctc_amounts)
                if not is_updated:
                    response['success'] = False
                    response['error'] = "Unable to add the employee's CTC. Please try again or contact support for assistance."
                else:
                    response['success'] = True
                    response['message'] = 'Employee CTC has been added successfully!'

        except Exception as err:
            response["error"] = settings.ERROR_MSG['application_error'].format(
                str(err), self.__log.error(self.__exception.get_exception())
            )
        return response


    def get_dropdown_params_for_ctc(self, request, fin_yr_id):
        response = {
            "financial_years": [],
            "current_financial_year": {},
            'employee_list': []
        }
        try:
            user_id = request.user.id
            not_ctc = request.GET.get('not_ctc')
            is_permitted = self.__utility.is_permitted(user_id, 'can_manage_ctc')
            if not is_permitted:
                response["error"] = settings.ERROR_MSG.get('access_denied')
                response['status'] = 403
                return response

            fin_year = FinanaceDA().get_financial_year_by_id(fin_yr_id)
            if not fin_year:
                response["error"] = "You have tried an invalid financial year."
                response['status'] = 499
                return response

            #user_id = request.user.id
            role_id, name = UserDA().get_user_role_by_id(user_id)
            if role_id == 3:
                is_manager = True
            else:
                is_manager = False

            current_fyd = FinanaceDA().get_financial_year_by_date(datetime.now())
            #assessment_years = FinanaceDA().get_all_financial_years()

            if not_ctc in ['true']:
                users = UserDA().get_all_active_users().order_by('username')
            else:
                ctc_emps = TaxDA().get_all_details_from_ctc_emp().filter(fin_yr_id=fin_yr_id)
                ctc_emps_list = set(ctc_emps.values_list('emp_id', flat=True)) if ctc_emps else set()
                users = UserDA().get_all_active_users()#.exclude(id__in=ctc_emps_list).order_by('username')

            user_ids = []
            if users:
                for each_user in users:
                    if each_user.id not in ctc_emps_list: 
                        user_ids.append(each_user.id)
                #user_ids = users.values_list('id', flat=True)

            user_profiles = UserDA().get_all_user_profiles()
            user_profiles = user_profiles.filter(user_id__in = user_ids)
            user_org_ids = { profile.user_id : profile.company_id for profile in user_profiles }
            for user in users:
                emp_name = user.first_name+' '+user.last_name
                response["employee_list"].append(
                    {
                        'id': user.id,
                        'name': emp_name,
                        'emp_code': user.username,
                        'org_id': user_org_ids[user.id] if user.id in user_org_ids.keys() else 0
                    }
                )
            response["employee_list"] = sorted(response["employee_list"], key=lambda x: int(x['emp_code']))
            response['current_financial_year'] = {'id': current_fyd.financial_year_id, 'name': current_fyd.description}
            response['is_manager'] = is_manager

        except Exception as err:
            response["error"] = settings.ERROR_MSG['application_error'].format(
                str(err), self.__log.error(self.__exception.get_exception())
            )
        return response


    def import_csv_ctc(self, request):
        response = {"success": [], "message":[], "error":[]}
        utility = Utility()
        exception = ExceptionHandler()

        error = ''
        output = ''
        success = ''
        columns = []
        data = []
        isError = False
        try:

            user_id = request.user.id
            is_permitted = self.__utility.is_permitted(user_id, 'can_manage_ctc')
            if not is_permitted:
                response["error"] = settings.ERROR_MSG.get('access_denied')
                response['status'] = 403
                return response
            request_data = request.data
            csvUpload =request_data.getlist('csv')
            is_overwrite =request_data.get('checkbox')
            if csvUpload:
                try:
                    inputFile = request.FILES['csv']
                except:
                    inputFile = None

                if not inputFile:
                    response['error'] = 'Please select a file for uploading.'
                else:
                    # Read the uploaded file using the csv module
                    file_data = inputFile.read().decode('utf-8').splitlines()
                    csv_reader = csv.reader(file_data)

                    # Extract the column names
                    columns = next(csv_reader)

                    # Extract the data
                    data = [dict(zip(columns, row)) for row in csv_reader]
                    response['success'] = True
                    response['message'] = 'File uploaded and processed successfully!'
            else:
                response['error'] = 'Please select a file for uploading.'

        except Exception as err:
            response["error"] = settings.ERROR_MSG['application_error'].format(
                str(err), self.__log.error(self.__exception.get_exception())
            )
        finally:
            del utility, exception
        return response


    def get_user_ctc(self, request):
        response = {
            "error": None,
            "emp_list": None,
            "status": 200,
            "categories_earnings": None,
            "categories_deductions": None
        }

        try:
            user_id = request.user.id
            #TODO set selected fin year
            fin_year = FinanaceDA().get_financial_year_by_date(datetime.now())

            if not fin_year:
                return {
                    "error": "You have tried an invalid financial year.",
                    "emp_list": [],
                    "status": 499
                }

            fin_year_desc = fin_year.description
            fin_year_id = fin_year.financial_year_id

            ctc_employee = TaxDA().get_emp_ctc_by_user_id_and_fin_yr(user_id, fin_year_id)
            if not ctc_employee:
                return {
                    "error": "Your CTC has not yet been updated to the DM Desk. For assistance, please contact the accounts manager",
                    "emp_list": [],
                    "status": 499
                }

            active_user = UserDA().get_user_by_id(user_id)

            ctc_master_details = TaxDA().get_ctc_master()
            ctc_master_dict = {ctc.ctc_id: ctc.name for ctc in ctc_master_details}
            categories_earnings = {ctc.ctc_id for ctc in ctc_master_details if ctc.type == 'Earning'}
            ctc_master_earnings = [ctc for ctc in ctc_master_details if ctc.type == 'Earning']
            ctc_master_deductions = [ctc for ctc in ctc_master_details if ctc.type == 'Deduction']

            if ctc_master_earnings:
                response['categories_earnings'] = [
                    {
                        'id': each.ctc_id,
                        'name': each.name,
                        'desc': each.description,
                        'type': each.type,
                    } for each in ctc_master_earnings
                ]
            if ctc_master_deductions:
                response['categories_deductions'] = [
                    {
                        'id': each.ctc_id,
                        'name': each.name,
                        'desc': each.description,
                        'type': each.type,
                    } for each in ctc_master_deductions
                ]

            emp_data = {
                'emp_name': f"{active_user.first_name} {active_user.last_name}",
                'emp_id': active_user.username,
                'user_id': active_user.id,
                'fin_year_desc': fin_year_desc,
                'earnings_total': 0,
                'deduction_total': 0,
                'earnings': [],
                'deduction': [],
            }
            for ctc_emp in ctc_employee:
                dec_amount = self.__decrypt_ctc(ctc_emp.amount)
                amount_as_int = float(dec_amount)
                if ctc_emp.ctc_id in categories_earnings:
                    emp_data['earnings'].append({
                        ctc_emp.emp_ctc_id: {
                            'name': ctc_master_dict.get(ctc_emp.ctc_id, ''),
                            'amount': amount_as_int
                        }
                    })
                    emp_data['earnings_total'] += amount_as_int
                else:
                    emp_data['deduction'].append({
                        ctc_emp.emp_ctc_id: {
                            'name': ctc_master_dict.get(ctc_emp.ctc_id, ''),
                            'amount': amount_as_int
                        }
                    })
                    emp_data['deduction_total'] += amount_as_int

            response['emp_list'] = [emp_data]

        except Exception as err:
            response["error"] = settings.ERROR_MSG['application_error'].format(
                err, self.__logs.error(self.__exception.get_exception())
            )
        return response

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


    def __decrypt_ctc(self, encrypted_value_base64):

        try:
            encrypted_value = base64.b64decode(encrypted_value_base64.encode('utf-8'))
            decrypted_value = self.cipher_suite.decrypt(encrypted_value)
            decrypted_value_str = decrypted_value.decode('utf-8')
        except Exception as err:
            decrypted_value_str = settings.ERROR_MSG['application_error'].format(
                str(err), self.__log.error(self.__exception.get_exception())
            )

        return decrypted_value_str


    def is_amount_valid(self, value):
        try:
            amt = float(value)
            return True
        except:
            return False
