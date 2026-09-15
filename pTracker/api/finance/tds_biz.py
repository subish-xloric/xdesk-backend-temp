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

import os
import re


def new_dto():
    dto = SimpleNamespace()
    return dto

class TDSBL():
    def __init__(self):
        self.__log = Logs()
        self.__exception = ExceptionHandler()
        self.__utility = Utility()
        self.__file_manager = FileManager()


    def get_employee_tds_data(self, request, fin_year_id, org_id):
        response = {"error": None, "success": False, "tds_data": []}
        try:
            user_id = request.user.id
            is_permitted = self.__utility.is_permitted(user_id, 'can_manage_tds')
            if not is_permitted:
                response["error"] = settings.ERROR_MSG.get('access_denied')
                response['status'] = 403
                return response

            fin_year_details = FinanaceDA().get_financial_year_by_id(fin_year_id)
            if not fin_year_details:
                response["error"] = "You have tried an invalid financial year."
                response["status"] = 499
                return response

            if org_id not in(3,2,'3','2'):
                response["error"] = "You have tried an invalid organization."
                response["status"] = 499
                return response


            active_users = UserDA().get_all_users()
            active_user_profiles = UserDA().get_user_profiles_by_employee_ids(active_users.values_list('id'))

            user_data = { user.id : { "name": user.first_name + " " + user.last_name, "employee_id": user.username } for user in active_users }
            profile_data = { user.user_id : { "company_id": user.company_id } for user in active_user_profiles }

            tds_data = TaxDA().get_tds_data_from_fin_year_id(fin_year_id)
            fin_year_data = FinanaceDA().get_all_financial_years()[:5]

            fin_year_data = { fin_year.financial_year_id : {'desc': fin_year.description} for fin_year in fin_year_data }

            month_order_list = settings.FIN_YEAR_MONTH_ORDER_LIST
            current_month_index = month_order_list.index(datetime.now().month)
            edit_enable = month_order_list[current_month_index:]

            result_dict = {}
            month_list = []
            count = 0

            for each in tds_data:
                if count < 12:
                    count += 1
                    month_list.append(f'{datetime(each.year, each.month_id, 1).strftime("%B")[:3]} {datetime(each.year, each.month_id, 1).strftime("%Y")[-2:]}')

                if each.user_id in result_dict.keys():
                    if len(result_dict[each.user_id]['month_data']) >= 12:
                        continue
                    result_dict[each.user_id]['month_data'].append(
                        {
                            "tds_id":each.id,
                            "fin_year_id":each.fin_year_id,
                            "month_id": each.month_id,
                            "year": each.year,
                            "month": datetime(each.year, each.month_id, 1).strftime("%B %Y"),
                            "month_name": datetime(each.year, each.month_id, 1).strftime("%B"),
                            "amount": each.amount,
                            "is_editable": True if each.month_id in edit_enable else False
                        }
                    )

                    if each.month_id == month_order_list[current_month_index]:
                        result_dict[each.user_id]['current_month_tds_id'] = each.id
                        result_dict[each.user_id]['current_month_tds_value'] = each.amount
                        result_dict[each.user_id]['fin_year_id'] = each.fin_year_id
                else:
                    temp_dict = {}
                    temp_dict['emp_id'] = each.user_id
                    temp_dict['emp_name'] = user_data[each.user_id]['name']
                    temp_dict['company_id'] = profile_data[each.user_id]['company_id'] if each.user_id in profile_data else None
                    temp_dict['month_data'] =[
                        {
                            "tds_id":each.id,
                            "fin_year_id":each.fin_year_id,
                            "month_id": each.month_id,
                            "year": each.year,
                            "month": datetime(each.year, each.month_id, 1).strftime("%B %Y"),
                            "month_name": datetime(each.year, each.month_id, 1).strftime("%B"),
                            "amount": each.amount,
                            "is_editable": True if each.month_id in edit_enable else False
                        }
                    ]
                    temp_dict['employee_id'] = user_data[each.user_id]['employee_id']

                    if each.month_id == month_order_list[current_month_index]:
                        temp_dict['current_month_tds_id'] = each.id
                        temp_dict['current_month_tds_value'] = each.amount
                        temp_dict['fin_year_id'] = each.fin_year_id

                    result_dict[each.user_id] = temp_dict


            tds_response = [each for each in result_dict.values() ]
            tds_response = list(filter(lambda x: x['company_id'] == org_id, tds_response))

            response['current_month_name'] = datetime.now().strftime("%B")
            response['current_month_year_name'] = datetime.now().strftime("%B %Y")
            response['current_month_id'] = month_order_list[current_month_index]
            response['tds_data'] = tds_response
            response['month_list'] = month_list
            response['fin_year_data'] = fin_year_data
            response['success'] = True
            response['message'] = 'Listed Successfully'

        except Exception as err:
            response["error"] = settings.ERROR_MSG['application_error']\
                .format(str(err), self.__log.error(self.__exception.get_exception()))
        return response


    def update_employee_tds_data(self, request):
        response = {"error": None, "success": False}
        try:
            user_id = request.user.id
            is_permitted = self.__utility.is_permitted(user_id, 'can_modify_tds')
            if not is_permitted:
                response["error"] = settings.ERROR_MSG.get('access_denied')
                response['status'] = 403
                return response

            request_data = request.data

            tds_id = request_data['tds_id']
            tds_amount = request_data['amount']
            #tds_amount = tds_amount.strip() if not tds_amount == 0 else str(tds_amount).strip()

            is_amount_valid = self.is_amount_valid(tds_amount)
            if not is_amount_valid:
                response['error'] = 'Invalid amount identified, Please try again'
                return response

            tds_amount = float(tds_amount)
            tds_data = TaxDA().get_tds_by_id(tds_id)
            if not tds_data:
                response['error'] = 'Invalid TDS entry identified, Please try again'
                return response

            tds_user = tds_data.user_id
            tds_fin_year = tds_data.fin_year_id
            tds_month = tds_data.month_id

            current_month_id = datetime.now().month

            current_date = datetime.now()
            current_fyd = FinanaceDA().get_financial_year_by_date(current_date)
            current_fy_year_id = 0
            if current_fyd:
                current_fy_year_id = current_fyd.financial_year_id

            if tds_fin_year != current_fy_year_id:
                response['error'] = 'Invalid financial year identified, Please try again'
                return response

            if tds_month == current_month_id:
                month_order_list = settings.FIN_YEAR_MONTH_ORDER_LIST
                future_months = month_order_list[month_order_list.index(tds_month):]

                tds_update_list = []
                for month in future_months:
                    temp_dict = {}
                    temp_dict['user_id'] = tds_user
                    temp_dict['month_id'] = month
                    temp_dict['amount'] = tds_amount
                    temp_dict['fin_year_id'] = tds_fin_year
                    tds_update_list.append(temp_dict)

                is_updated = TaxDA().bulk_update_tds_data(tds_update_list)
            else:
                data_dict = {}
                data_dict['id'] = tds_id
                data_dict['amount'] = tds_amount
                is_updated = TaxDA().update_tds_data(data_dict)

            if not is_updated:
                response['success'] = False
                response['error'] = 'TDS Data update Unsuccessful'
                return response
            response['success'] = True
            response['message'] = 'TDS Data updated Successfully'
        except Exception as err:
            response["error"] = settings.ERROR_MSG['application_error']\
                .format(str(err), self.__log.error(self.__exception.get_exception()))
        return response


    def is_amount_valid(self, value):
        try:
            amt = float(value)
            if amt >= 0:
                return True
        except:
            return False
        #return False
        #pattern = r"^[0-9]+(\.[0-9]{2})?$"
        #return bool(re.match(pattern, value))


    # def create_tds_data(self, tax_period_id, tax_batch_user_ids, user_id):
    def create_tds_data(self, request):
        response = {"success": [], "message":[], "error":[]}
        try:
            user_id = request.user.id
            #user_id = request.user.id
            is_permitted = self.__utility.is_permitted(user_id, 'can_modify_tds')
            if not is_permitted:
                response["error"] = settings.ERROR_MSG.get('access_denied')
                response['status'] = 403
                return response


            fin_year_id = 0
            current_fyd = FinanaceDA().get_financial_year_by_date(datetime.now())
            if current_fyd:
                fin_year_id = current_fyd.financial_year_id

            #fin_year_id = current_fyd.financial_year_id
            tax_period = TaxDA().get_assessment_period_by_fin_year_id(fin_year_id)
            if not tax_period:
                response['success'] = False
                response['error'] = 'You cannot create TDS for any period other than the current financial year.'
                return response

            tax_batches = TaxDA().get_tax_batches_by_tax_period_id(tax_period.id)
            if tax_batches:
                month_order_list = settings.FIN_YEAR_MONTH_ORDER_LIST
                tax_batch_user_ids = tax_batches.values_list('user_id',flat=True)

                years_in_fin_year = self.get_years_in_a_financial_year(current_fyd)
                last_year_months = month_order_list[:9]

                tds_employees = TaxDA().get_tds_data_from_fin_year_id(fin_year_id)
                tds_emps_list = list(set(tds_employees.values_list('user_id', flat=True)) if tds_employees else set())

                tds_data = []
                with transaction.atomic():
                    for each in tax_batch_user_ids:
                        if each in tds_emps_list:
                            continue
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
                    response['success'] = True
                    response['message'] = 'Employee tds created successfully'
                if not is_tds_created:
                    response['success'] = False
                    response['error'] = 'Employee tds created Unsuccessful'
            else:
                response['success'] = False
                response['error'] = 'Employee tds created Unsuccessful'
                return response
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
    

    def test_tds(self):
        import csv



        dict_users = {}
        dict_user_code = {}
        users = UserDA().get_all_users()            
        if users:
            for each_user in users:
                try:
                    dict_users[int(each_user.username)] = each_user.id 
                    dict_user_code[int( each_user.id)] = int(each_user.username) 
                except:
                    pass

        tds_dict= {}
        import io
        csv_path = '/var/www/dm_ptracker/backend_app/pTracker/pTracker/api/finance/tds.csv'
        csv_bytes = self.__file_manager.read_file(csv_path)
        if csv_bytes is not None:
            csv_str = csv_bytes.decode('utf-8')
            csvfile = io.StringIO(csv_str)
            reader = csv.reader(csvfile) 
            for row in reader:
                #print(row)  # Each row is a list of values                  
                try:
                    emp_id = int(row[1])
                except:
                    continue
                try:
                    tds = int(row[2].split(".")[0])
                    tds_dict [emp_id] = tds 
                except:
                    #print('row[2]', row[2])
                    tds_dict [emp_id] = 0

        #print('tds_dict', tds_dict)


        fin_year_id = 0
        current_fyd = FinanaceDA().get_financial_year_by_date(datetime.now())
        if current_fyd:
            fin_year_id = current_fyd.financial_year_id

        #fin_year_id = current_fyd.financial_year_id
        tax_period = TaxDA().get_assessment_period_by_fin_year_id(fin_year_id)
        # if not tax_period:
        #     response['success'] = False
        #     response['error'] = 'You cannot create TDS for any period other than the current financial year.'
        #     return response

        tax_batches = TaxDA().get_tax_batches_by_tax_period_id(tax_period.id)
        if tax_batches:
            month_order_list = settings.FIN_YEAR_MONTH_ORDER_LIST
            tax_batch_user_ids = tax_batches.values_list('user_id',flat=True)

            years_in_fin_year = self.get_years_in_a_financial_year(current_fyd)
            last_year_months = month_order_list[:9]

            tds_employees = TaxDA().get_tds_data_from_fin_year_id(fin_year_id)
            tds_emps_list = list(set(tds_employees.values_list('user_id', flat=True)) if tds_employees else set())

            tds_data = []
            with transaction.atomic():
                for each in tax_batch_user_ids:
                    emp_code = dict_user_code.get(each) 
                    total_tds = tds_dict.get(emp_code,0)
                    # if not total_tds:
                    #     print('UserID no data', each)  
                    #     continue
                    tds_amt = total_tds/10 
                    # if each in tds_emps_list:
                    #     continue
                    for month in month_order_list:
                        temp_dict = {}
                        temp_dict['fin_year_id'] = fin_year_id
                        temp_dict['month_id'] = month
                        temp_dict['year'] = years_in_fin_year[0] if month in last_year_months else years_in_fin_year[1]
                        temp_dict['user_id'] = each
                        temp_dict['amount'] = tds_amt
                        temp_dict['last_updated_by'] = 54
                        tds_data.append(temp_dict)
                        print('temp_dict', temp_dict)
                        del temp_dict

                is_tds_created = TaxDA().bulk_create_tds_data_v1(tds_data)
