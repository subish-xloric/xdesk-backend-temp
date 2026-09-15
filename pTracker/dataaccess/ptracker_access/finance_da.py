
from  datetime import datetime, date, timedelta
from types import SimpleNamespace

from django.conf import settings
from django.db.models import query
from django.db.models import Q

from django.contrib.auth.models import User
from django.contrib.auth.models import Group
from django.contrib.auth.models import Permission

from pTracker.common.utility import Utility
from pTracker.common.exception_handler import ExceptionHandler
from pTracker.common.logs import Logs

from pTracker.dataaccess.ptracker_access.finance_models import FinancialYear
from pTracker.dataaccess.ptracker_access.finance_models import EmployeePayHeader
from pTracker.dataaccess.ptracker_access.finance_models import EmployeePayDetails
from pTracker.dataaccess.ptracker_access.finance_models import EmployeePayLog



from pTracker.dataaccess.db import Connection

from io import BytesIO
import os

from PIL import Image

def new_dto():
    dto = SimpleNamespace()
    return dto

class FinanaceDA():

    def __init__(self):
        self.__log = Logs()
        self.__exception = ExceptionHandler()
        self.__utility = Utility()


    def get_last_years(self, limit=3):
        resultSet = FinancialYear.objects.order_by('-financial_year_id').filter(start_date__year__gte=2023)[:limit]
        return resultSet

    def get_financial_year_by_id(self, pk):
        resultSet = FinancialYear.objects.filter(financial_year_id=pk)#.last()
        if resultSet:
            return resultSet[0]
        return None

    def get_payslip_headers(self, params):
        filtered_results = EmployeePayHeader.objects.filter(organization=params.organization, \
            financial_year_id=params.financial_year_id)
        return filtered_results

    def get_all_employee_details(self, financial_year_id, user_id):
        filtered_results = EmployeePayDetails.objects.filter(financial_year_id=financial_year_id, emp_id=user_id)
        return filtered_results

    def validate_financial_year_period(self, fin_year_id):
        is_valid = None
        try:
            today = datetime.today()
            formatted_date = today.strftime("%Y-%m-%d %H:%M:%S")
            is_valid = FinancialYear.objects.filter(financial_year_id=fin_year_id, start_date__lte=formatted_date, end_date__gte=formatted_date)
        except Exception as err:
            self.__log.error(self.__exception.get_exception())
        return is_valid


    def create_finanace_log(self, dataDict):
        return EmployeePayLog.objects.create(**dataDict)

    def get_finanace_log_by_header_id(self, header_id):
        return EmployeePayLog.objects.filter(header_id=header_id)

    def create_employee_pay_header(self, dataDict):
        return EmployeePayHeader.objects.create(**dataDict)

    def create_or_update_employee_pay_header(self, dataDict):
        financial_year_id = dataDict.get('financial_year_id')
        month = dataDict.get('month')
        year = dataDict.get('year')
        organization = dataDict.get('organization')
        employee_pay_header, _= EmployeePayHeader.objects.update_or_create(
            financial_year_id=financial_year_id,
            month=month,
            year=year,
            organization=organization,
            defaults=dataDict
        )
        return employee_pay_header

    def create_or_update_employee_pay_details(self, dataDict):
        financial_year_id = dataDict.get('financial_year_id')
        pay_header_id = dataDict.get('pay_header_id')
        emp_id = dataDict.get('emp_id')
        employee_pay_header, _= EmployeePayDetails.objects.update_or_create(
            pay_header_id=pay_header_id,
            financial_year_id=financial_year_id,
            emp_id=emp_id,
            defaults=dataDict
        )
        return employee_pay_header

    def create_employee_Pay_details(self, dataDict):
        return EmployeePayDetails.objects.create(**dataDict)

    def delete_payslip_details(self, pay_header_id):
        return EmployeePayDetails.objects.filter(pay_header_id=pay_header_id).delete()

    def update_payslip_header(self, header_id, dataDict):
        return EmployeePayHeader.objects.filter(pay_header_id=header_id).update(**dataDict)

    def update_payslip_details_by_header(self, header_id, dataDict):
        return EmployeePayDetails.objects.filter(pay_header_id=header_id).update(**dataDict)

    def update_payslip_details(self, detail_id, dataDict):
        return EmployeePayDetails.objects.filter(pay_detail_id=detail_id).update(**dataDict)

    def get_payslip_details_by_header_id(self, header_id):
        return EmployeePayDetails.objects.filter(pay_header_id=header_id)

    def get_payslip_by_id(self, detail_id):
        return EmployeePayDetails.objects.filter(pay_detail_id=detail_id)

    def get_payslip_header(self, header_id):
        return EmployeePayHeader.objects.filter(pay_header_id=header_id).last()

    def delete_employee_pay_details_by_detail_id(self, detail_id):
        return EmployeePayDetails.objects.filter(pay_detail_id=detail_id).delete()

    def get_financial_year_by_date(self, date):
        try:
            financial_year = FinancialYear.objects.filter(
                Q(start_date__lte=date) & Q(end_date__gte=date)
            ).first()
        except:
            financial_year = None
        return financial_year

    def is_payslip_header_exists(self,month,year,organization):
        return EmployeePayHeader.objects.filter(month=month, year=year, organization=organization,is_reverted=0).exists()

    # def get_all_employee_Pay_details(self, headerDict):
    #     return EmployeePayDetails.objects.filter(**)

    def get_all_financial_years(self):
        return FinancialYear.objects.all()


    # def check_financial_year_id(self, financial_year_id):
    #     return FinancialYear.objects.filter(financial_year_id=financial_year_id)


    def get_financial_year_desc(self, financial_year_id):
        financial_year_desc = FinancialYear.objects.get(financial_year_id=financial_year_id)
        financial_year_desc = financial_year_desc.description
        return financial_year_desc


    def check_date_with_current_financial_year(check_date):
        current_date = datetime.date
        current_financial_year = FinancialYear.objects.filter(
            Q(start_date__lte=current_date) & Q(end_date__gte=current_date)
        ).first()
        if current_financial_year.start_date <= current_date <= current_financial_year.end_date:
            return current_financial_year.financial_year_id
        else:
            return None


    def get_current_financial_year(self):
        from datetime import date
        current_date = date.today()
        try:
            current_financial_year = FinancialYear.objects.filter(
                Q(start_date__lte=current_date) & Q(end_date__gte=current_date)
            ).first()
        except Exception as err:
            self.__log.error(self.__exception.get_exception())
        return current_financial_year