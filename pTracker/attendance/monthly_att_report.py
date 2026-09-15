import os
import datetime
import time
import calendar
import sys
import traceback
#from datetime import timedelta

from django.conf import settings

from types import SimpleNamespace

import openpyxl
from openpyxl.styles import PatternFill, Border, Side, Alignment, Protection, Font
from openpyxl.styles import Alignment
from openpyxl.styles.borders import Border, Side
from openpyxl.styles import Color, Fill
from openpyxl.styles import Font

from pTracker.dataaccess.db import Connection
from pTracker.common.utility import Utility
from pTracker.user_management.employee import Employee
from pTracker.dataaccess.ptracker_access.attendance import AttendanceDA
from pTracker.user_management.holiday_da import HolidayDA
from pTracker.cronjobs.email_sender import send_monthly_att_report


def att_dto():
    dto = SimpleNamespace()
    dto.emp_code = None
    dto.emp_name = None
    dto.gender = None
    dto.doj = None
    dto.designation = None
    dto.work_hours = 0
    dto.att_status = 'X'
    return dto


def new_dto():
    dto = SimpleNamespace()
    return dto





class ExceptionHandler :

    def __init__(self):
        pass

    def getException(self):

        """ Method to track the exception """
        cla, exc, trbk = sys.exc_info()
        excName = cla.__name__

        try:
            excArgs = exc.__dict__["args"]
        except KeyError:
            excArgs = "<no args>"

        excTb = traceback.format_tb(trbk, 8)
        message = '%s %s %s' % (excName, excArgs, excTb)

        return message


class MonthlyAttendanceReportBL():

    def get_holidays_for_month(self, start_date, end_date):
        holiday_list = []

        week_ends = Utility().get_all_weekends(start_date, end_date)
        if week_ends:
            for each_day in week_ends:
                try:
                    holiday_list.append(each_day.strftime("%d"))
                except:
                    pass

        start_date = start_date.strftime("%Y-%m-%d")
        end_date = end_date.strftime("%Y-%m-%d")

        obj_holidays = HolidayDA().get_all_holidays(start_date, end_date)
        if obj_holidays:
            for each_item in obj_holidays:
                try:
                    holiday_list.append(each_item.holiday_date.strftime("%d"))
                except Exception as err:
                    pass

        return holiday_list



    def is_leap_year(self, year):
        year = int(year)
        if(year % 4 == 0 and year % 100 != 0 or year % 400 == 0):
            return True
        else:
            return False



    def format_excel_report(self, log_list, month, year, company_name, holidays):

        try:
            #str_month  = 12_2019
            is_current_month = False

            #month = int(str_month .split("_")[0])
            #year = int(str_month .split("_")[1])

            today = datetime.datetime.today()
            current_month = today.month
            current_year = today.year
            current_day = today.day

            if month == current_month and year == current_year:
                is_current_month = True

            #holidays = self.get_holidays_for_month(month, year)
            str_month = datetime.datetime(year, month, 1)
            temp_month = str_month.strftime("%B, %Y")
            str_month = str_month.strftime("%B_%Y")


            bold = Font(bold=True)
            header_fill = PatternFill(
                start_color="F0F802", end_color="F0F802", fill_type='solid')

            thin_border = Border(
                left=Side(style='thin'),
                right=Side(style='thin'),
                top=Side(style='thin'),
                bottom=Side(style='thin'))


            if log_list:
                log_list.sort(key=lambda x: x.emp_name, reverse=False)

                day_head = ['G','H', 'I','J', 'K','L', 'M','N', 'O','P', 'Q','R', 'S','T',
                'U','V', 'W','X', 'Y','Z', 'AA','AB', 'AC','AD', 'AE','AF', 'AG','AH', 'AI','AJ', 'AK']

                work_hrs_col = "AL"
                remarks_col = "AM"

                if month in [4, 6, 9, 11]:
                    day_head = day_head[:-1]
                    work_hrs_col =  "AK"
                    remarks_col = "AL"
                elif month == 2:
                    if self.is_leap_year(year):
                        day_head = day_head[:29]
                        work_hrs_col = "AJ"
                        remarks_col = "AK"
                    else:
                        day_head = day_head[:28]
                        work_hrs_col = "AI"
                        remarks_col = "AJ"

                wb = openpyxl.Workbook()
                ws = wb.worksheets[0]


                if company_name == 'Digitalmesh':
                    company_address = company_address = """Digital Mesh Softech India (P) Limited\nUnit 1: 43-A, E Block, 2nd Floor,\nCochin Special Economic Zone, Kakkanad, Kochi – 682 037, Kerala, India.\nTel: +91-484-4060200, Fax: +91-484-4060201"""
                else:
                    company_address = """EM Softech LLP\nUnit 1:Plot No.43/ A, D Block, 2nd floor,\nCochin Special Economic Zone(CSEZ), Kakkanad, Kochi-682037, Kerala, India.\nTel:+91-484-2413280"""

                ws.merge_cells('A1:' + day_head[-1]+'1')
                ws.merge_cells('A3:' + day_head[-1]+'3')

                ws['A1'].value = company_address
                ws['A1'].font = bold
                ws['A1'].alignment = Alignment(horizontal='center')
                ws.row_dimensions[1].height = 95


                ws['A3'].value = 'Attendance Report for ' + str(temp_month)
                ws['A3'].font = bold
                ws['A3'].alignment = Alignment(horizontal='center')
                ws['A3'].fill = header_fill

                ws['A5'].value = 'Sl No.'
                ws['A5'].font = bold

                ws['B5'].value = 'Emp Code'
                ws['B5'].font = bold

                ws['C5'].value = 'Emp Name'
                ws['C5'].font = bold

                ws['D5'].value = 'M/F'
                ws['D5'].font = bold

                ws['E5'].value = 'DOJ'
                ws['E5'].font = bold

                ws['F5'].value = 'Designation'
                ws['F5'].font = bold

                ws[work_hrs_col + "5"].value = 'Hrs'
                ws[work_hrs_col + "5"].font = bold

                head_row = '5'
                index_counter = 0
                for col in day_head:
                    index_counter += 1
                    ws[col+head_row].value = index_counter
                    ws[col+head_row].font = bold
                    ws[col+head_row].alignment = Alignment(horizontal='center')

                row = 7
                counter = 1
                for each_item in log_list:
                    ws['A'+str(row)].value = counter
                    ws['B'+str(row)].value = each_item.emp_code
                    ws['C'+str(row)].value = each_item.emp_name
                    ws['D'+str(row)].value = str(each_item.gender)[0]
                    ws['E'+str(row)].value = Utility().convert_date_time_to_string(each_item.doj)
                    ws['F'+str(row)].value = each_item.designation


                    """
                    Start date  llop
                    """
                    emp_day_list = each_item.day_list
                    att_day_counter = 1
                    for col in day_head:
                        #ws[col+str(row)].value = each_item.att_status
                        ws[col+str(row)].alignment = Alignment(horizontal='center')
                        #ws[col+str(row)].font = bold

                        if att_day_counter in holidays:
                            ws.column_dimensions[col].width = 3
                            ws[col + str(row)].value = 'H'
                            ws[col + str(row)].font = Font(color="228B22")
                        elif is_current_month and att_day_counter >= current_day:
                            ws[col + str(row)].value = '-'
                            ws.column_dimensions[col].width = 3
                        elif att_day_counter in emp_day_list:
                            ws[col + str(row)].value = 'x'
                            ws.column_dimensions[col].width = 3
                        else:
                            ws[col + str(row)].value = 'A'
                            ws[col + str(row)].font = Font(color="ff0000")
                            ws.column_dimensions[col].width = 3

                        att_day_counter += 1

                    ws[work_hrs_col + str(row)].value = str(round(each_item.work_hours/3600, 0))

                    row += 1
                    counter += 1

                ws.column_dimensions["A"].width = 8
                ws.column_dimensions["B"].width = 10
                ws.column_dimensions["C"].width = 20
                ws.column_dimensions["D"].width = 6
                ws.column_dimensions["E"].width = 12
                ws.column_dimensions["F"].width = 25
                upload_path = settings.UPLOAD_PATH['MONTHLY_ATT_REPORT'] + str(year)
                if not os.path.exists(upload_path):
                    os.makedirs(upload_path)

                #str_date = str_date.replace("/", "_")
                file_name = company_name + "_" + str_month + ".xlsx"
                temp_file_name = company_name + "_" + str_month + "_original.xlsx"
                path_to_file = upload_path + "/" + file_name
                wb.save(path_to_file)

                if work_hrs_col == "AI":
                    ws.delete_cols(35, 1)
                elif work_hrs_col == "AJ":
                    ws.delete_cols(36, 1)
                elif work_hrs_col == "AK":
                    ws.delete_cols(37, 1)
                elif work_hrs_col == "AL":
                    ws.delete_cols(38, 1)

                temp_file_name = company_name + "_" + str_month + "_original.xlsx"
                temp_path_to_file = upload_path + "/" + temp_file_name
                wb.save(temp_path_to_file)

                send_monthly_att_report.apply_async([path_to_file, str_month, company_name], queue=settings.CELERY_QUEUE['mail_sender'])
        except Exception as err:
            e = ExceptionHandler().getException()
            Utility().log("Error !!! : {0} ".format(str(e)))
            Utility().log("Error in the method format, Error is : {0} ".format(str(err)))



    def __procees_emp_attendance(self, att_data):
        work_hours = 0
        day_list = []
        if att_data:
            for each_item in att_data:
                work_hours += each_item.work_hours
                dt = each_item.attendance_date
                day_list.append(dt.day)
        return work_hours, day_list


    def get_last_date_of_the_month(self, month, year):
        any_date = datetime.datetime(year, month, 1)
        next_month = any_date.replace(day=28) + datetime.timedelta(days=4)
        last_day_of_month = next_month - datetime.timedelta(days=next_month.day)
        return last_day_of_month

    def generate_monthly_att_report(self, month, year):
        att_dict = {}
        dm_emp_att_list = []
        em_emp_att_list = []
        c_level_emps = []

        #month = "11_2019"

        try:
            start_date = datetime.datetime(year, month, 1)
            end_date = self.get_last_date_of_the_month(month, year)

            holidays = []
            temp = self.get_holidays_for_month(start_date, end_date)
            if temp:
                holidays = [int(i) for i in temp]

            start_date = start_date.strftime("%Y-%m-%d")
            end_date = end_date.strftime("%Y-%m-%d")

            days_in_month = calendar.monthrange(year, month)[1]

            working_days = days_in_month - len(holidays)



            employees = Employee().get_all_active_employees()
            results = Employee().get_att_exclude_employees_code()
            if results:
                for each_item in results:
                    c_level_emps.append(each_item.emp_code)

            att_logs = AttendanceDA().get_attendance_by_range(start_date, end_date)
            if att_logs:
                for each_item in att_logs:
                    if each_item.emp_code in att_dict:
                        temp_list = att_dict[each_item.emp_code]
                        temp_list.append(each_item)
                        att_dict[each_item.emp_code] = temp_list

                    else:
                        att_dict[each_item.emp_code] = [each_item]

            if employees:
                for emp_code in employees:
                    employee = employees[emp_code]
                    dto = att_dto()
                    dto.emp_code = emp_code
                    dto.emp_name = employee.emp_name
                    dto.gender = employee.gender
                    dto.doj = employee.doj
                    dto.designation = employee.designation
                    dto.day_list = []

                    if emp_code in c_level_emps:
                        dto.work_hours = 28800 * working_days
                        dto.day_list = list(range(1, 32))
                    else:
                        att_data = att_dict.get(emp_code, None)

                        if att_data:
                            work_hours, day_list = self.__procees_emp_attendance(att_data)
                            dto.work_hours = work_hours
                            dto.day_list = day_list
                        else:
                            dto.work_hours = 0
                            dto.day_list = []

                    if employee.company_id == settings.COMPANY['DM']['ID']:
                        dm_emp_att_list.append(dto)
                    else:
                        em_emp_att_list.append(dto)
                    del dto

            self.format_excel_report(dm_emp_att_list, month, year, 'Digitalmesh', holidays)
            self.format_excel_report(em_emp_att_list, month, year, 'EM_Softech', holidays)

        except Exception as err:
            Utility().log("Error in the method generate_daily_att_report, Error is : {0} ".format(str(err)))
