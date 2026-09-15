from django.conf import settings

from types import SimpleNamespace

from pTracker.dataaccess.db import Connection
from pTracker.common.utility import Utility

from pTracker.dataaccess.ptracker_access.models import AdminEmployee
from pTracker.dataaccess.ptracker_access.models import AttendanceExcludeEmployee


def new_dto():
    dto = SimpleNamespace()
    return dto


class Employee():

    def __init__(self):
        pass


    def get_all_active_employees(self):
        emp_dict = {}
        str_sql = """SELECT
        EmployeeId, EmployeeName, EmployeeCode, CompanyId, Gender, DOJ, Designation
        FROM Employees
        WHERE
        (CompanyId = 2 OR CompanyId = 3)
        AND  Status='Working'"""
        conn = Connection('essl_db')
        results, error = conn.execute(str_sql)
        if error:
            Utility().log(error)
        if results:
            for each_item in results:
                dto = new_dto()
                emp_code = str(each_item[2]).strip()
                dto.emp_name = str(each_item[1]).strip()
                dto.emp_id = int(each_item[0])
                dto.company_id = int(each_item[3])
                dto.gender = each_item[4]
                dto.doj = each_item[5]
                dto.designation = each_item[6]

                emp_dict[emp_code] = dto
                del dto
        return emp_dict

    def get_admin_employees_code(self, company_id=0):
        admin_employees = AdminEmployee.objects.filter(deleted=0)
        if company_id:
            admin_employees = admin_employees.filter(company_id=company_id)
        return admin_employees


    def get_att_exclude_employees_code(self, company_id=0):
        admin_employees = AttendanceExcludeEmployee.objects.filter(deleted=0)
        if company_id:
            admin_employees = admin_employees.filter(company_id=company_id)
        return admin_employees

    def get_all_email_recipient(self, report_type, company_id=0):
        emails = ['subish@mydomain.com',
                  'renjith@mydomain.com', 'ajiths@mydomain.com', 'ratheesh@mydomain.com',
                  'roshan@mydomain.com', 'ravijohn@mydomain.com', 'radhi.menon@mydomain.com',
                  'riju.raghunathan@mydomain.com']
        return emails

    def get_att_email_recipient(self, report_type, company_id=0):
        emails = ['subish@mydomain.com',
                  'renjith@mydomain.com', 'ajiths@mydomain.com', 'ratheesh@mydomain.com',
                  'roshan@mydomain.com', 'ravijohn@mydomain.com', 'radhi.menon@mydomain.com']
        return emails

    def get_missing_time_sheet_email_recipient(self):
        emails = ['ajiths@mydomain.com',
                  'roshan@mydomain.com',
                  'radhi.menon@mydomain.com',
                  'subish@mydomain.com'
                  ]
        return emails