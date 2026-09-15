from types import SimpleNamespace
from datetime import datetime, timedelta
from unittest import result

from django.http import HttpResponse
#from httplib2 import Response
# from django.conf import settings
from django.conf import Settings, settings
from pTracker.settings import constants
from pTracker.common.utility import Utility
from pTracker.common.exception_handler import ExceptionHandler
from pTracker.common.logs import Logs

from pTracker.cronjobs.email_sender import send_email_notification
from pTracker.dataaccess.ptracker_access.appraisal_da import AppraisalDA
from pTracker.dataaccess.ptracker_access.user_da import UserDA
from pTracker.dataaccess.ptracker_access.tax_da import TaxDA
from pTracker.dataaccess.ptracker_access.finance_da import FinanaceDA

import openpyxl
from openpyxl.styles import PatternFill, Border, Side, Alignment, Protection, Font
from openpyxl import Workbook
from openpyxl.styles import Alignment
from openpyxl.styles.borders import Border, Side
from openpyxl.styles import Color, Fill
from openpyxl.styles import Font

import json

from pTracker import settings


def new_dto():
    dto = SimpleNamespace()
    return dto


class TaxReportBL():

    def __init__(self):
        self.__log = Logs()
        self.__exception = ExceptionHandler()
        self.__utility = Utility()


    def create_12bb_estimate_sheet(self,request, financial_year_id, emp_id):

        response = dict()
        try:
            if emp_id in (0, '0'):
                user_id = request.user.id
            else:
                user_id = int(emp_id)
            name, address, pan, gender, father_name = UserDA().get_name_address_pan_from_user_id(user_id)
            current_date = datetime.today()
            formatted_date = current_date.strftime("%d-%m-%Y")
            job_designation = UserDA().get_employee_designation(user_id)
            tax_period = TaxDA().get_tax_period_from_financial_year_id(financial_year_id)
            tax_period_id = tax_period.id
            financial_desc = FinanaceDA().get_financial_year_desc(financial_year_id)
            regime_type = TaxDA().get_regime_type_by_tax_period_user_id(tax_period_id,user_id)
            tax_plan = ""
            if regime_type:
                tax_plan = settings.REGIME_TYPE_MAPPING.get(regime_type.regime_type, "-")
            gen_variable = "son" if gender == "Male" else "daughter"

            rent_paid_to_the_landlord, name_of_landlord, address_of_landlord, pan_of_landlord = TaxDA().get_claim_detail_with_parties\
                (tax_period_id=tax_period_id, cat_id=1,user_id=user_id)

            workbook = Workbook()
            sheet = workbook.active

            full_border = Border(
            left=Side(style="thin"),
            right=Side(style="thin"),
            top=Side(style="thin"),
            bottom=Side(style="thin"),
            )
            no_bottom_border = Border(top=Side(style="thin"),left=Side(style="thin"),right=Side(style="thin"),)
            no_top_border = Border(bottom=Side(style="thin"),left=Side(style="thin"),right=Side(style="thin"),)

            left_side_border = Border(left=Side(style="thin"),)
            right_side_border = Border(right=Side(style="thin"),)
            left_right_border = Border(left=Side(style="thin"),right=Side(style="thin"),)

            no_left_border = Border(bottom=Side(style="thin"),top=Side(style="thin"),right=Side(style="thin"),)

            sheet.merge_cells('A1:D1')
            sheet[f'D1'].border = full_border

            heading_cell = sheet['A1']
            heading_cell.value = "FORM NO.12BB"
            heading_cell.alignment = Alignment(horizontal='center', vertical='center')
            heading_cell.font = Font(bold=True)

            sheet.merge_cells('A2:D2')
            sheet[f'A2'].border = full_border
            sheet[f'D2'].border = full_border
            rule_cell = sheet['A2']
            rule_cell.value = "See rule 26C"
            rule_cell.alignment = Alignment(horizontal='center', vertical='center')

            sheet.merge_cells('A3:C3')
            rule_cell = sheet['A3']
            rule_cell.value = "1. Name and address of the employee: "
            rule_cell.alignment = Alignment(horizontal='left', vertical='center')


            sheet['A3'].border = full_border
            sheet['D3'].border = full_border

            rule_cell = sheet['D3']
            rule_cell.value = f"{name},\n{address}"
            rule_cell.alignment = Alignment(horizontal='left', vertical='center', wrap_text=True)

            sheet.merge_cells('A4:C4')
            rule_cell = sheet['A4']
            rule_cell.value = "2. Permanent Account Number of the employee: "
            rule_cell.alignment = Alignment(horizontal='left')

            sheet['A4'].border = full_border
            sheet['D4'].border = full_border

            rule_cell = sheet['D4']
            rule_cell.value = pan
            rule_cell.alignment = Alignment(horizontal='left', vertical='center', wrap_text=True)


            sheet.merge_cells('A5:C5')
            rule_cell = sheet['A5']
            rule_cell.value = "3. Financial year"
            rule_cell.alignment = Alignment(horizontal='left')

            sheet['A5'].border = full_border
            sheet['D5'].border = full_border

            rule_cell = sheet['D5']
            rule_cell.value = f"{financial_desc}"
            rule_cell.alignment = Alignment(horizontal='left', vertical='center', wrap_text=True)

            sheet.merge_cells('A6:C6')
            rule_cell = sheet['A6']
            rule_cell.value = "4. Tax Regime"
            rule_cell.alignment = Alignment(horizontal='left')

            sheet['A6'].border = full_border
            sheet['D6'].border = full_border

            rule_cell = sheet['D6']
            rule_cell.value = tax_plan
            rule_cell.alignment = Alignment(horizontal='left', vertical='center', wrap_text=True)
            existing_font = rule_cell.font
            rule_cell.font = Font(color="FF0000", name=existing_font.name, bold=True)

            sheet.merge_cells('A8:D8')
            rule_cell = sheet['A8']
            rule_cell.value = "Details of claims and evidence thereof"
            rule_cell.alignment = Alignment(horizontal='center', vertical='center')
            rule_cell.font = Font(bold=True)

            sheet.merge_cells('A7:D7')
            sheet[f'D7'].border = full_border

            sheet['A8'].border = full_border
            sheet['D8'].border = no_left_border

            rule_cell = sheet['A9']
            rule_cell.value = "Sl No."
            rule_cell.alignment = Alignment(vertical='top')

            sheet['A9'].border = full_border

            rule_cell = sheet['B9']
            rule_cell.value = "Nature of claim"
            sheet.merge_cells('B9:C9')
            rule_cell.alignment = Alignment(horizontal='left', vertical='top')

            sheet['B9'].border = full_border

            sheet['C9'].border = full_border

            rule_cell = sheet['D9']
            rule_cell.value = "Amount (Rs.)"
            rule_cell.alignment = Alignment(horizontal='right', vertical='top')

            sheet['D9'].border = full_border

            row = 10
            categories = TaxDA().get_all_categories()
            category_dict = {}
            for each in categories:
                category_dict[each.id] = each.name
            claim_declarations = TaxDA().get_all_emplyee_declarations(tax_period_id, user_id)
            if claim_declarations:
                for count, declaration in enumerate(claim_declarations):
                    rule_cell = sheet[f'A{row}']
                    rule_cell.value = str(count+1)
                    rule_cell.alignment = Alignment(vertical='top')

                    sheet[f'A{row}'].border = full_border
                    sheet.merge_cells(f'B{row}:C{row}')
                    sheet[f'B{row}'].border = full_border
                    rule_cell = sheet[f'B{row}']
                    category_text = category_dict[declaration.cat_id]
                    if len(category_text) > 46:
                        # Split the text into two parts at the nearest space
                        split_index = category_text.rfind(' ', 0, 46)
                        if split_index == -1:
                            # If no space found, split at the 32nd character
                            split_index = 46

                        part1 = category_text[:split_index]
                        part2 = category_text[split_index+1:]

                        # Add a line break and dash between the two parts
                        rule_cell.value = f'{part1}-\n{part2}'
                        sheet.row_dimensions[row].height = 30
                    else:
                        rule_cell.value = f'{category_text}'

                    rule_cell.alignment = Alignment(vertical='top')

                    rule_cell = sheet[f'D{row}']
                    sheet[f'D{row}'].border = full_border
                    rule_cell.value = f'{declaration.amount}'
                    rule_cell.alignment = Alignment(horizontal='right', vertical='top')
                    rule_cell.font = Font(bold=True)

                    row+=1

            sheet.merge_cells(f'A{row}:D{row}')
            sheet[f'D{row}'].border = full_border
            sheet.row_dimensions[row].height = 30
            row+=1
            sheet.merge_cells(f'A{row}:D{row}')
            rule_cell = sheet[f'A{row}']
            rule_cell.value = f"I, {name}, {gen_variable} of {father_name} do hereby certify that the information given above is complete and correct."
            rule_cell.alignment = Alignment(vertical='center', wrap_text=True)
            sheet.row_dimensions[row].height = 40

            sheet[f'A{row}'].border = full_border
            sheet[f'D{row}'].border = no_left_border

            row += 1
            sheet.merge_cells(f'A{row}:C{row}')
            rule_cell = sheet[f'A{row}']
            rule_cell.value = "Place: Kakkanad"
            rule_cell.alignment = Alignment(vertical='top')

            sheet.merge_cells(f'D{row}:D{row}')


            sheet[f'A{row}'].border = no_bottom_border
            sheet[f'D{row}'].border = no_bottom_border

            # Apply left-right border to 'A45' and 'D45'
            sheet[f'A{row}'].border = left_right_border
            sheet[f'D{row}'].border = left_right_border

            row += 1
            sheet.merge_cells(f'A{row}:C{row}')
            rule_cell = sheet[f'A{row}']
            rule_cell.value = f"Date: {formatted_date}"
            rule_cell.alignment = Alignment(horizontal='left', vertical='center')

            sheet[f'A{row}'].border = left_right_border
            sheet[f'D{row}'].border = left_right_border


            row += 1
            sheet.merge_cells(f'A{row}:C{row}')
            rule_cell = sheet[f'A{row}']
            rule_cell.value = f"Designation: {job_designation}"
            rule_cell.alignment = Alignment(vertical='top')

            sheet[f'A{row}'].border = no_top_border
            sheet[f'D{row}'].border = no_top_border

            sheet.merge_cells(f'D{row - 2}:D{row}')
            merged_cell = sheet[f'D{row - 2}']
            merged_cell.value = "This is a computer-generated document.\nNo signature is required."
            merged_cell.alignment = Alignment(vertical='center', wrap_text=True)

            row += 1
            sheet.merge_cells(f'A{row}:D{row}')
            sheet[f'D{row}'].border = full_border

            row += 1
            sheet.merge_cells(f'A{row}:D{row}')
            rule_cell = sheet[f'A{row}']
            rule_cell.value = f"Please note that you are solely responsible for maintaining all original claim proof documents. These documents must be readily available for submission to the IT department upon request."
            rule_cell.alignment = Alignment(vertical='top', wrap_text=True)
            sheet.row_dimensions[row].height = 40

            sheet[f'A{row}'].border = full_border
            sheet[f'D{row}'].border = full_border


            sheet.column_dimensions['C'].width = 30
            sheet.column_dimensions['D'].width = 40
            sheet.row_dimensions[3].height = 59
            sheet.row_dimensions[9].height = 25

            response = HttpResponse(content_type='application/vnd.openxmlformats-officedocument.spreadsheetml.sheet')
            response['Content-Disposition'] = 'attachment; filename=Form12BB.xlsx'
            workbook.save(response)
        except Exception as err:
            response["error"] = settings.ERROR_MSG['application_error']\
                .format(err, self.__log.error(self.__exception.get_exception()))
        return response

    def create_12bb_actual_sheet(self,request, financial_year_id, emp_id):#Actual

        response = dict()
        try:
            if emp_id in (0, '0'):
                user_id = request.user.id
            else:
                user_id = int(emp_id)

            name, address, pan, gender, father_name = UserDA().get_name_address_pan_from_user_id(user_id)
            current_date = datetime.today()
            formatted_date = current_date.strftime("%d-%m-%Y")
            job_designation = UserDA().get_employee_designation(user_id)
            tax_period = TaxDA().get_tax_period_from_financial_year_id(financial_year_id)
            tax_period_id = tax_period.id
            regime_type = TaxDA().get_regime_type_by_tax_period_user_id(tax_period_id,user_id)
            tax_plan = ""
            if regime_type:
                tax_plan = settings.REGIME_TYPE_MAPPING.get(regime_type.regime_type, "-")
            gen_variable = "son" if gender == "Male" else "daughter"

            financial_desc = FinanaceDA().get_financial_year_desc(financial_year_id)

            rent_paid_to_the_landlord, name_of_landlord, address_of_landlord, pan_of_landlord = TaxDA().get_claim_detail_with_parties\
                (tax_period_id=tax_period_id, cat_id=1,user_id=user_id)

            workbook = Workbook()
            sheet = workbook.active

            full_border = Border(
            left=Side(style="thin"),
            right=Side(style="thin"),
            top=Side(style="thin"),
            bottom=Side(style="thin"),
            )
            no_bottom_border = Border(top=Side(style="thin"),left=Side(style="thin"),right=Side(style="thin"),)
            no_top_border = Border(bottom=Side(style="thin"),left=Side(style="thin"),right=Side(style="thin"),)

            left_side_border = Border(left=Side(style="thin"),)
            right_side_border = Border(right=Side(style="thin"),)
            left_right_border = Border(left=Side(style="thin"),right=Side(style="thin"),)

            no_left_border = Border(bottom=Side(style="thin"),top=Side(style="thin"),right=Side(style="thin"),)

            sheet.merge_cells('A1:D1')
            sheet[f'D1'].border = full_border

            heading_cell = sheet['A1']
            heading_cell.value = "FORM NO.12BB"
            heading_cell.alignment = Alignment(horizontal='center', vertical='center')
            heading_cell.font = Font(bold=True)

            sheet.merge_cells('A2:D2')
            sheet[f'A2'].border = full_border
            sheet[f'D2'].border = full_border
            rule_cell = sheet['A2']
            rule_cell.value = "See rule 26C"
            rule_cell.alignment = Alignment(horizontal='center', vertical='center')

            sheet.merge_cells('A3:C3')
            rule_cell = sheet['A3']
            rule_cell.value = "1. Name and address of the employee: "
            rule_cell.alignment = Alignment(horizontal='left', vertical='center')


            sheet['A3'].border = full_border
            sheet['D3'].border = full_border

            rule_cell = sheet['D3']
            rule_cell.value = f"{name},\n{address}"
            rule_cell.alignment = Alignment(horizontal='left', vertical='center', wrap_text=True)

            sheet.merge_cells('A4:C4')
            rule_cell = sheet['A4']
            rule_cell.value = "2. Permanent Account Number of the employee: "
            rule_cell.alignment = Alignment(horizontal='left')

            sheet['A4'].border = full_border
            sheet['D4'].border = full_border

            rule_cell = sheet['D4']
            rule_cell.value = pan
            rule_cell.alignment = Alignment(horizontal='left', vertical='center', wrap_text=True)


            sheet.merge_cells('A5:C5')
            rule_cell = sheet['A5']
            rule_cell.value = "3. Financial year"
            rule_cell.alignment = Alignment(horizontal='left')

            sheet['A5'].border = full_border
            sheet['D5'].border = full_border

            rule_cell = sheet['D5']
            rule_cell.value = f"{financial_desc}"
            rule_cell.alignment = Alignment(horizontal='left', vertical='center', wrap_text=True)

            sheet.merge_cells('A6:C6')
            rule_cell = sheet['A6']
            rule_cell.value = "4. Tax Regime"
            rule_cell.alignment = Alignment(horizontal='left')

            sheet['A6'].border = full_border
            sheet['D6'].border = full_border

            rule_cell = sheet['D6']
            rule_cell.value = tax_plan
            rule_cell.alignment = Alignment(horizontal='left', vertical='center', wrap_text=True)
            existing_font = rule_cell.font
            rule_cell.font = Font(color="FF0000", name=existing_font.name, bold=True)

            sheet.merge_cells('A7:D7')
            sheet[f'D7'].border = full_border

            sheet.merge_cells('A8:D8')
            rule_cell = sheet['A8']
            rule_cell.value = "Details of claims and evidence thereof"
            rule_cell.alignment = Alignment(horizontal='center', vertical='center')
            rule_cell.font = Font(bold=True)

            sheet['A8'].border = full_border
            sheet['D8'].border = no_left_border

            rule_cell = sheet['A9']
            rule_cell.value = "Sl No."
            rule_cell.alignment = Alignment(vertical='top',wrap_text=True)

            sheet['A9'].border = full_border

            rule_cell = sheet['B9']
            rule_cell.value = "Nature of claim"
            sheet.merge_cells('B9:C9')
            rule_cell.alignment = Alignment(horizontal='left', vertical='top')

            sheet['B9'].border = full_border

            sheet['C9'].border = full_border

            rule_cell = sheet['D9']
            rule_cell.value = "Amount (Rs.)"
            rule_cell.alignment = Alignment(horizontal='right', vertical='top',wrap_text=True)

            sheet['D9'].border = full_border



            row = 10
            categories = TaxDA().get_all_categories()
            category_dict = {}
            for each in categories:
                category_dict[each.id] = each.name
            claim_declarations = TaxDA().get_all_emplyee_declarations(tax_period_id, user_id)
            if claim_declarations:
                for count, declaration in enumerate(claim_declarations):
                    rule_cell = sheet[f'A{row}']
                    rule_cell.value = str(count+1)
                    rule_cell.alignment = Alignment(vertical='top')

                    sheet[f'A{row}'].border = full_border

                    sheet.merge_cells(f'B{row}:C{row}')
                    sheet[f'B{row}'].border = full_border
                    rule_cell = sheet[f'B{row}']
                    category_text = category_dict[declaration.cat_id]

                    if len(category_text) > 46:
                        split_index = category_text.rfind(' ', 0, 46)
                        if split_index == -1:
                            split_index = 46

                        part1 = category_text[:split_index]
                        part2 = category_text[split_index+1:]

                        rule_cell.value = f'{part1}-\n{part2}:'
                        sheet.row_dimensions[row].height = 30
                    else:
                        rule_cell.value = f'{category_text}:'

                    rule_cell.alignment = Alignment(vertical='top')


                    claims = TaxDA().get_claims_by_declaration_id(declaration_id=declaration.id).filter(status='Approved')
                    total_amount = 0
                    temp_row = row
                    if claims:
                        row += 1
                        party_list = []
                        category_list = []
                        cat_name = ''
                        for c,claim in enumerate(claims):
                            if claim.cat_id in (1, 3):
                                cat_name = 'landlord' if claim.cat_id == 1 else 'lender'
                                claim_party = None
                                hra_details = None
                                if cat_name == 'lender':
                                    claim_party = TaxDA().get_claim_parties_by_party_id(claim.party_id)

                                    if claim_party:

                                        existing_party_index = next((position for position, party in enumerate(party_list) if party["party_name"] == claim_party.name), None)

                                        if existing_party_index is not None:
                                            party_list[existing_party_index]["amount"] += claim.amount
                                        else:
                                            claim_parties = {
                                                "party_name": f"{claim_party.name}",
                                                "amount": claim.amount,
                                                "address": f'{claim_party.address_line1}\n'+f'{claim_party.city}\n'+f'{claim_party.district}\n'+f'{claim_party.state}, '+f'{claim_party.pincode}',
                                                "pan": f'{claim_party.pan_number}'
                                            }
                                            party_list.append(claim_parties)
                                elif cat_name == 'landlord':
                                    hra_details = TaxDA().get_hra_details_claim_id(claim.id)
                                    if hra_details:
                                        claim_party = TaxDA().get_claim_parties_by_party_id(claim.party_id)
                                    if claim_party:

                                        existing_party_index = next((i for i, party in enumerate(party_list) if party["party_name"] == claim_party.name), None)

                                        if existing_party_index is not None:
                                            party_list[existing_party_index]["amount"] += claim.amount
                                        else:
                                            claim_parties = {
                                                "party_name": f"{claim_party.name}",
                                                "amount": claim.amount,
                                                "address": f'{claim_party.address_line1}\n'+f'{claim_party.city}\n'+f'{claim_party.district}\n'+f'{claim_party.state}, '+f'{claim_party.pincode}',
                                                "pan": f'{claim_party.pan_number}'
                                            }
                                            party_list.append(claim_parties)
                            else:
                                # if declaration.cat_id != claim.cat_id:

                                existing_category_index = next((position for position, category in enumerate(category_list) if category["category_dict_name"] == category_dict[claim.cat_id]), None)

                                if existing_category_index is not None:
                                    category_list[existing_category_index]["category_amount"] += claim.amount
                                else:
                                    category_parties = {
                                        "category_dict_name": f"{category_dict[claim.cat_id]}",
                                        "category_amount": claim.amount,
                                    }
                                    category_list.append(category_parties)

                        if cat_name:
                            if cat_name == 'landlord' or cat_name == 'lender':

                                for party in party_list:

                                    sheet.merge_cells(f'B{row}:D{row}')
                                    sheet[f'D{row}'].border = full_border
                                    row+=1
                                    sheet.merge_cells(f'B{row}:C{row}')
                                    sheet[f'B{row}'].border = full_border
                                    rule_cell = sheet[f'B{row}']
                                    rule_cell.value = f'Name of the {cat_name}:'
                                    rule_cell.alignment = Alignment(vertical='top')

                                    rule_cell = sheet[f'D{row}']
                                    sheet[f'D{row}'].border = full_border
                                    rule_cell.value = party['party_name']

                                    row+=1
                                    sheet.merge_cells(f'B{row}:C{row}')
                                    sheet[f'B{row}'].border = full_border
                                    rule_cell = sheet[f'B{row}']
                                    rule_cell.value = f'Address of the {cat_name}:'
                                    rule_cell.alignment = Alignment(vertical='top')
                                    sheet.row_dimensions[row].height = 59

                                    rule_cell = sheet[f'D{row}']
                                    sheet[f'D{row}'].border = full_border
                                    rule_cell.alignment = Alignment(horizontal='left', vertical='center')
                                    rule_cell.value = party['address']

                                    row+=1
                                    sheet.merge_cells(f'B{row}:C{row}')
                                    sheet[f'B{row}'].border = full_border
                                    rule_cell = sheet[f'B{row}']
                                    rule_cell.value = f'PAN of the {cat_name}:'
                                    rule_cell.alignment = Alignment(vertical='top', wrap_text=True)

                                    rule_cell = sheet[f'D{row}']
                                    sheet[f'D{row}'].border = full_border
                                    rule_cell.alignment = Alignment(vertical='top')
                                    rule_cell.value = party['pan']
                                    row+=1

                                    sheet.merge_cells(f'B{row}:C{row}')
                                    sheet[f'B{row}'].border = full_border
                                    rule_cell = sheet[f'B{row}']
                                    rule_cell.value = f'Rent paid to the {cat_name}:'
                                    rule_cell.alignment = Alignment(vertical='top')

                                    rule_cell = sheet[f'D{row}']
                                    sheet[f'D{row}'].border = full_border
                                    rule_cell.value = f"{party['amount']}"
                                    rule_cell.alignment = Alignment(horizontal='right', vertical='top')
                                    sheet.merge_cells(f'A{temp_row}:A{row}')
                                    row+=1

                                    total_amount+=party['amount']

                        if category_list:
                            c=0
                            row-=2
                            sheet.merge_cells(f'A{row}:D{row}')
                            sheet[f'D{row}'].border = full_border
                            row+=2
                            sheet.merge_cells(f'B{row}:D{row}')
                            sheet[f'E{row}'].border = left_side_border
                            row+=1
                            for category in category_list:
                                c+=1
                                sheet.merge_cells(f'A{temp_row}:A{temp_row+len(category_list)+1}')
                                sheet.merge_cells(f'B{row}:C{row}')
                                sheet[f'B{row}'].border = full_border
                                rule_cell = sheet[f'B{row}']
                                category_text = f"{c}. {category['category_dict_name']}"

                                if len(category_text) > 46:
                                    split_index = category_text.rfind(' ', 0, 46)
                                    if split_index == -1:
                                        split_index = 46

                                    part1 = category_text[:split_index]
                                    part2 = category_text[split_index+1:]

                                    rule_cell.value = f'{part1}-\n{part2}:'
                                    sheet.row_dimensions[row].height = 30
                                else:
                                    rule_cell.value = f'{category_text}'

                                rule_cell.alignment = Alignment(vertical='top')


                                rule_cell = sheet[f'D{row}']
                                sheet[f'D{row}'].border = full_border
                                rule_cell.value = f"{category['category_amount']}"
                                rule_cell.alignment = Alignment(horizontal='right',vertical='top')
                                row+=1
                                # sheet.merge_cells(f'A{row}:D{row}')
                                # sheet[f'D{row}'].border = full_border
                                total_amount+=category['category_amount']


                    rule_cell = sheet[f'D{temp_row}']
                    sheet[f'D{temp_row}'].border = full_border
                    rule_cell.value = f'{total_amount}'
                    rule_cell.alignment = Alignment(horizontal='right', vertical='top')
                    rule_cell.font = Font(bold=True)
                    if temp_row==row:
                        row+=1
                    sheet.merge_cells(f'A{row}:D{row}')
                    sheet[f'D{row}'].border = full_border
                    row+=1

            row-=1
            sheet.row_dimensions[row].height = 30
            sheet.merge_cells(f'A{row}:D{row}')
            sheet[f'D{row}'].border = full_border
            row+=1
            sheet.merge_cells(f'A{row}:D{row}')
            rule_cell = sheet[f'A{row}']
            rule_cell.value = f"I, {name}, {gen_variable} of {father_name} do hereby certify that the information given above is complete and correct."
            rule_cell.alignment = Alignment(vertical='center', wrap_text=True)
            sheet.row_dimensions[row].height = 40

            sheet[f'A{row}'].border = full_border
            sheet[f'D{row}'].border = no_left_border

            row += 1
            sheet.merge_cells(f'A{row}:C{row}')
            rule_cell = sheet[f'A{row}']
            rule_cell.value = "Place: Kakkanad"
            rule_cell.alignment = Alignment(vertical='top')

            sheet.merge_cells(f'D{row}:D{row}')

            sheet[f'A{row}'].border = no_bottom_border
            sheet[f'D{row}'].border = no_bottom_border

            sheet[f'A{row}'].border = left_right_border
            sheet[f'D{row}'].border = left_right_border

            row += 1
            sheet.merge_cells(f'A{row}:C{row}')
            rule_cell = sheet[f'A{row}']
            rule_cell.value = f"Date: {formatted_date}"
            rule_cell.alignment = Alignment(vertical='center')

            sheet[f'A{row}'].border = left_right_border
            sheet[f'D{row}'].border = left_right_border


            row += 1
            sheet.merge_cells(f'A{row}:C{row}')
            rule_cell = sheet[f'A{row}']
            rule_cell.value = f"Designation {job_designation}"
            rule_cell.alignment = Alignment(vertical='top')

            sheet[f'A{row}'].border = no_top_border
            sheet[f'D{row}'].border = no_top_border

            sheet.merge_cells(f'D{row - 2}:D{row}')
            merged_cell = sheet[f'D{row - 2}']
            merged_cell.value = "This is a computer-generated document.\nNo signature is required."
            merged_cell.alignment = Alignment(vertical='center', wrap_text=True)

            row += 1
            sheet.merge_cells(f'A{row}:D{row}')
            sheet[f'D{row}'].border = full_border

            row += 1
            sheet.merge_cells(f'A{row}:D{row}')
            rule_cell = sheet[f'A{row}']
            rule_cell.value = f"Please note that you are solely responsible for maintaining all original claim proof documents. These documents must be readily available for submission to the IT department upon request."
            rule_cell.alignment = Alignment(vertical='top', wrap_text=True)
            sheet.row_dimensions[row].height = 40

            sheet[f'A{row}'].border = full_border
            sheet[f'D{row}'].border = full_border

            #(i) Interest payable/paid to the lender
            sheet.column_dimensions['C'].width = 30
            sheet.column_dimensions['D'].width = 40
            sheet.row_dimensions[3].height = 59
            sheet.row_dimensions[9].height = 25


            response = HttpResponse(content_type='application/vnd.openxmlformats-officedocument.spreadsheetml.sheet')
            response['Content-Disposition'] = 'attachment; filename=Form12BB.xlsx'
            workbook.save(response)
        except Exception as err:
            response["error"] = settings.ERROR_MSG['application_error']\
                .format(err, self.__log.error(self.__exception.get_exception()))
        return response


    def get_assessment_report(self, request, period_id):
        response = {"error": None, "success": False, "report_list": []}
        result_dict = {}
        try:
            user_id = request.user.id
            # role_id, name = UserDA().get_user_role_by_id(user_id)
            is_permitted = True #TODO
            if not is_permitted:
                response["error"] = settings.ERROR_MSG.get('access_denied')
                response['status'] = 403
                return response

            tax_batch_users = []
            threshold_value = request.GET.get('thresholdValue')
            org_id = request.GET.get('org_id')

            user_dict = self.__get_all_active_users_dict(False)
            user_ids = list(user_dict.keys())

            user_profiles = UserDA().get_all_user_profiles()
            user_profiles = user_profiles.filter(user_id__in = user_ids)

            org_users = user_profiles.filter(company_id=int(org_id)).values_list('user_id', flat=True)

            claim_declarations = TaxDA().get_claim_declarations_by_emp_id(tax_period_id=period_id)
            claim_declarations = claim_declarations.filter(user_id__in=org_users)

            claim_declarations_users = claim_declarations.values_list('user_id', flat=True)
            claim_declarations_users = set(list(claim_declarations_users))

            tax_batch_data = TaxDA().get_all_tax_batch_data_for_regime_type(period_id, org_id)
            tax_batch_users = set(list(tax_batch_data.values_list('user_id', flat=True)))

            tax_batch_data = { tax_batch[0] : { 'user_id': tax_batch[0], 'regime_type': tax_batch[1], 'org_id': tax_batch[2] } for tax_batch in tax_batch_data }
            if claim_declarations:

                for declaration in claim_declarations:

                    claims = TaxDA().get_claims_by_declaration_id(declaration.id)

                    if declaration.user_id in result_dict.keys():
                        result_dict[declaration.user_id]['estimated_amount']+=declaration.amount
                        result_dict[declaration.user_id]['submitted_amount']+=sum(claims.exclude(status="Rejected").values_list('amount', flat=True))
                    else:
                        result_dict[declaration.user_id] = {
                        "employee_name" : user_dict.get(declaration.user_id)[0],
                        "emp_code" : user_dict.get(declaration.user_id)[1],
                        "emp_id": declaration.user_id,
                        "estimated_amount": declaration.amount,
                        "submitted_amount":sum(claims.exclude(status="Rejected").values_list('amount', flat=True)),
                        "submitted_percentage":0,
                        "tax_type": tax_batch_data[declaration.user_id]['regime_type'],
                        "is_declared": True
                    }

            for key, entry in result_dict.items():
                estimated_amount = entry['estimated_amount']
                submitted_amount = entry['submitted_amount']

                # Avoid division by zero
                if estimated_amount != 0:
                    submitted_percentage = (submitted_amount / estimated_amount) * 100
                    if threshold_value!='All' and threshold_value:
                        if int(round(submitted_percentage)) > int(threshold_value):
                            continue
                    result_dict[key]['submitted_percentage'] = round(submitted_percentage,0)

                response['report_list'].append(result_dict[key])

            not_declared_users = list(set(tax_batch_users) - set(claim_declarations_users))

            for key in not_declared_users:
                temp_dict = {}
                temp_dict["employee_name"] = user_dict.get(key)[0]
                temp_dict["emp_code"] = user_dict.get(key)[1]
                temp_dict["emp_id"] = key
                temp_dict["estimated_amount"] = 0
                temp_dict["submitted_amount"] = 0
                temp_dict["submitted_percentage"] = 0
                temp_dict["tax_type"] = 0
                temp_dict["is_declared"] = False
                temp_dict["submitted_percentage"] = 0
                response['report_list'].append(temp_dict)
                del temp_dict


        except Exception as err:
            response["error"] = settings.ERROR_MSG["application_error"].format(
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
