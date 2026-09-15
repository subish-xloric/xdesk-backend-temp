from reportlab.pdfgen import canvas
from reportlab.lib.pagesizes import letter
from datetime import datetime
from reportlab.lib.styles import getSampleStyleSheet, ParagraphStyle
from django.conf import settings
from reportlab.lib import colors
from reportlab.platypus import SimpleDocTemplate, Table, PageBreak, Paragraph, TableStyle
from pTracker.common.utility import Utility
from pTracker.common.exception_handler import ExceptionHandler
from pTracker.common.logs import Logs
from django.http import FileResponse, HttpResponse
from io import BytesIO
from reportlab.lib.units import inch

from pTracker.api.finance.tax_computation_engine import TaxComputationBL

from pTracker.dataaccess.ptracker_access.user_da import UserDA
from pTracker.dataaccess.ptracker_access.finance_da import FinanaceDA
from pTracker.dataaccess.ptracker_access.tax_da import TaxDA
from pTracker.common.utility import Utility
# decrypt_ctc_amount

from pTracker import settings

import locale



class TaxComputeBL():
    def __init__(self):

        self.__log = Logs()
        self.__exception = ExceptionHandler()
        self.__utility = Utility()
        locale.setlocale(locale.LC_ALL, 'en_IN.UTF-8')
        self.regime_type = None
        self.total_pages = None

    def format_amount(self, number):
        if number in ['']:
            return number
        return locale.format_string("%.2f", float(number), grouping=True)


    def __is_valid_user_id(self, user_id):
        is_user_valid = UserDA().get_user_by_id(user_id)
        if is_user_valid.is_active == 1:
            return True
        else:
            return False


    def generate_tax_computation(self,request,emp_id, fin_year_id, output_filename="income_tax_computation.pdf"):

        response = {
            "error": None,
            "success": None
        }
        month_list=[]
        try:
            user_id = request.user.id
            emp_id = int(emp_id)
            if not emp_id:
                emp_id = user_id

            if emp_id == user_id:
                is_permitted = True
            else:
                is_permitted = self.__utility.is_permitted(user_id, 'can_manage_ctc')

            if not is_permitted:
                response["error"] = settings.ERROR_MSG.get('access_denied')
                response['status'] = 403
                return response

            if not self.__is_valid_user_id(emp_id):
                response["error"] = settings.ERROR_MSG.get('access_denied')
                response['status'] = 403
                return response


            fin_year = FinanaceDA().get_financial_year_by_id(fin_year_id)
            if not fin_year:
                response["error"] = "You have tried an invalid financial year."
                response['status'] = 499
                return response

            ctc_employee = TaxDA().get_emp_ctc_by_user_id_and_fin_yr(emp_id, fin_year_id)
            if not ctc_employee:
                return {
                    "error": "CTC has not yet been updated to the DM Desk. For assistance, please contact the accounts manager",
                    "emp_list": [],
                    "status": 499
                }


            claim_type = True if request.GET.get('type') == 'declared' else False
            pdf_data_response = TaxComputationBL().tax_pdf_generation_data(emp_id, fin_year_id, claim_type)


            if pdf_data_response['error']:
                response["error"] = pdf_data_response['error']
                return response

            data = request.data

            first_half_months = [datetime(1, month_number, 1).strftime("%B") for month_number in settings.FIN_YEAR_MONTH_ORDER_LIST[:9]]
            second_half_months = [datetime(1, month_number, 1).strftime("%B") for month_number in settings.FIN_YEAR_MONTH_ORDER_LIST[9:]]
            current_fin_year = FinanaceDA().get_current_financial_year()
            fin_year_details = FinanaceDA().get_financial_year_by_id(fin_year_id)
            fin_year = fin_year_details.description
            start_year =current_fin_year.start_date.strftime("%Y")
            end_year =current_fin_year.end_date.strftime("%Y")
            first_half_months=map(lambda x:x[:3]+" "+start_year,first_half_months)
            second_half_months=map(lambda x:x[:3]+" "+end_year, second_half_months)

            month_list = list(first_half_months) + list(second_half_months)

            user_data = UserDA().get_user_by_id(emp_id)
            user_profile_data = UserDA().get_user_profile_by_id(emp_id)

            period_id = TaxDA().get_tax_period_from_financial_year_id(fin_year_id).id
            tax_batch = TaxDA().get_tax_batch_by_period_and_user(period_id, emp_id)

            self.regime_type = tax_batch.regime_type

            buffer = BytesIO()
            doc = SimpleDocTemplate(buffer, pagesize=letter, topMargin=30, bottomMargin=30, leftMargin=20, rightMargin=20,title="Tax Computation", author="DM Desk")
            c = canvas.Canvas(buffer, pagesize=letter)

            c.setFont("Helvetica", 10)
            story = []
            styles = getSampleStyleSheet()

            heading_style = styles['Heading4']
            heading_style.alignment = 1
            heading_style.textColor = colors.black
            heading_style.fontName = "Helvetica-Bold"

            if self.regime_type:
                heading_paragraph = Paragraph(f"Income Tax Computation ({'Old Regime' if self.regime_type == 1 else 'New Regime'})", heading_style)
            else:
                heading_paragraph = Paragraph("Income Tax Computation", heading_style)

            label_style = styles['Heading6']
            label_style.fontName = "Helvetica-Bold"

            heading_paragraph1 = Paragraph("Details of salary, other income and tax deduction (FY: "+ fin_year+")", heading_style)
            label_style = styles['Heading6']
            label_style.fontName = "Helvetica-Bold"

            #pdf_data_response = TaxComputationBL().tax_pdf_generation_data(emp_id, fin_year_id, claim_type)

            # if pdf_data_response['error'] is not None:
            #     try:
            #         raise Exception
            #     except Exception as err:
            #         response["error"] = settings.ERROR_MSG['application_error']\
            #             .format(pdf_data_response['error'], self.__log.error(self.__exception.get_exception()))
            #     return response

            pdf_data = pdf_data_response['data']

            head_table_data = [[heading_paragraph]]

            head_table_style = TableStyle(
                [
                    ("GRID", (0, 0), (-1, 0), 1, (0.75, 0.75, 0.75)),
                    ("GRID", (0, 1), (-1, -1), 1, (0.75, 0.75, 0.75)),
                    ("FONTSIZE", (0, 0), (-1, -1), 7.5),
                    ("GRID", (0, 0), (-1, -1), 1, colors.black),
                    ("ROWHEIGHT", (0, 0), (-1, -1), 40),
                    ("VALIGN", (0, 0), (-1, -1), "MIDDLE"),
                ]
            )

            head_table_col_widths = 560
            row_height = 20
            row_height_alt = 30
            head_table = Table(head_table_data, colWidths=head_table_col_widths, rowHeights=row_height, style=head_table_style)

            employee_detail_table_data = [[Paragraph("Employee Name",label_style),f"{user_data.first_name} {user_data.last_name}"],
            [Paragraph("Employee PAN",label_style),f"{user_profile_data.pan}"],]

            employee_detail_table_style = TableStyle(
                [
                    ("GRID", (0, 0), (-1, 0), 1, (0.75, 0.75, 0.75)),
                    ("GRID", (0, 1), (-1, -1), 1, (0.75, 0.75, 0.75)),
                    ("FONTSIZE", (0, 0), (-1, -1), 7.5),
                    ("GRID", (0, 0), (-1, -1), 1, colors.black),
                    ("ROWHEIGHT", (0, 0), (-1, -1), 40),
                    ("VALIGN", (0, 0), (-1, -1), "MIDDLE"),
                ]
            )

            employee_detail_table_col_widths = [380,180]
            employee_detail_table = Table(employee_detail_table_data, colWidths=employee_detail_table_col_widths, rowHeights=row_height, style=employee_detail_table_style)

            head_2_table_data = [[heading_paragraph1]]

            head_2_table_style = TableStyle(
                [
                    ("GRID", (0, 0), (-1, 0), 1, (0.75, 0.75, 0.75)),
                    ("GRID", (0, 1), (-1, -1), 1, (0.75, 0.75, 0.75)),
                    ("FONTSIZE", (0, 0), (-1, -1), 7.5),
                    ("GRID", (0, 0), (-1, -1), 1, colors.black),
                    ("ROWHEIGHT", (0, 0), (-1, -1), 40),
                    ("VALIGN", (0, 0), (-1, -1), "MIDDLE"),
                ]
            )

            head_2_table_col_widths = 560
            head_2_table = Table(head_2_table_data, colWidths=head_2_table_col_widths, rowHeights=row_height, style=head_2_table_style)

            story.append(head_table)
            story.append(employee_detail_table)
            story.append(head_2_table)


            section_heading_style = styles['Heading6']
            section_heading_style.textColor = colors.black
            section_heading_style.fontName = "Helvetica-Bold"

            heading_paragraph = Paragraph("Income Tax Computation", section_heading_style)


            for heading in pdf_data.values():
                table_data = []
                temp_list = []
                temp_list.extend([Paragraph(heading['serial_number'], section_heading_style), Paragraph(heading['desc'], section_heading_style)])
                if 'gross_amount' in heading.keys():
                    temp_list.append(self.format_amount(heading['gross_amount']))
                if 'qualifying_amount' in heading.keys():
                    temp_list.append(self.format_amount(heading['qualifying_amount']))
                if 'deductable_amount' in heading.keys():
                    temp_list.append(self.format_amount(heading['deductable_amount']))

                if 'column_1' in heading.keys() and 'gross_amount' not in heading.keys():
                    temp_list.append(heading['column_1'])
                if 'column_2' in heading.keys() and 'qualifying_amount' not in heading.keys():
                    temp_list.append(heading['column_2'])
                if 'column_3' in heading.keys() and 'qualifying_amount' not in heading.keys():
                    temp_list.append(heading['column_3'])

                table_data.append(temp_list)

                if heading['sub_items'] is None or 'column_1' in heading.keys() or 'column_2' in heading.keys() or 'column_3' in heading.keys():
                    col_widths = [23,357,60,60,60]
                else:
                    col_widths = [23,537]

                table_style = TableStyle(
                    [
                        ("GRID", (0, 0), (-1, 0), 1, (0.75, 0.75, 0.75)),
                        ("GRID", (0, 1), (-1, -1), 1, (0.75, 0.75, 0.75)),
                        ("FONTSIZE", (0, 0), (-1, -1), 7.5),
                        ("GRID", (0, 0), (-1, -1), 1, colors.black),
                        # ("ALIGN", (0, 0), (-1, -1), "RIGHT"),
                        ("ALIGN", (2, 0), (2, -1), "RIGHT"),
                        ("ALIGN", (2, 0), (3, -1), "RIGHT"),
                        ("ALIGN", (2, 0), (4, -1), "RIGHT"),
                        # ("FONTNAME", (0, 0), (-1, -1), "Helvetica"),
                        ("ROWHEIGHT", (0, 0), (-1, -1), 40),
                        ("VALIGN", (0, 0), (-1, -1), "MIDDLE"),
                    ]
                )
                if 'amount_bold' in heading.keys():
                    table_style = TableStyle(
                        [
                            ("GRID", (0, 0), (-1, 0), 1, (0.75, 0.75, 0.75)),
                            ("GRID", (0, 1), (-1, -1), 1, (0.75, 0.75, 0.75)),
                            ("FONTSIZE", (0, 0), (-1, -1), 7.5),
                            ("GRID", (0, 0), (-1, -1), 1, colors.black),
                            # ("ALIGN", (0, 0), (-1, -1), "RIGHT"),
                            ("ALIGN", (2, 0), (2, -1), "RIGHT"),
                            ("ALIGN", (2, 0), (3, -1), "RIGHT"),
                            ("ALIGN", (2, 0), (4, -1), "RIGHT"),
                            ("FONTNAME", (0, 0), (-1, -1), "Helvetica-Bold"),
                            ("ROWHEIGHT", (0, 0), (-1, -1), 40),
                            ("VALIGN", (0, 0), (-1, -1), "MIDDLE"),
                        ]
                    )

                #if 'not_amount_bold' in heading.keys():

                elif 'not_amount_bold' in heading.keys():
                    table_style = TableStyle(
                        [
                            ("GRID", (0, 0), (-1, 0), 1, (0.75, 0.75, 0.75)),
                            ("GRID", (0, 1), (-1, -1), 1, (0.75, 0.75, 0.75)),
                            ("FONTSIZE", (0, 0), (-1, -1), 7.5),
                            ("GRID", (0, 0), (-1, -1), 1, colors.black),
                            # ("ALIGN", (0, 0), (-1, -1), "RIGHT"),
                            ("ALIGN", (2, 0), (2, -1), "CENTER"),
                            ("ALIGN", (2, 0), (3, -1), "CENTER"),
                            ("ALIGN", (2, 0), (4, -1), "CENTER"),
                            ("FONTNAME", (0, 0), (-1, -1), "Helvetica-Bold"),
                            ("ROWHEIGHT", (0, 0), (-1, -1), 40),
                            ("VALIGN", (0, 0), (-1, -1), "MIDDLE"),
                        ]
                    )

                table = Table(table_data, colWidths=col_widths, rowHeights=row_height, style=table_style)
                story.append(table)

                if heading['sub_items'] is not None:
                    for sub_item in heading['sub_items'].values():
                        table_data = []
                        temp_list = []
                        temp_list.extend([sub_item['serial_number'], sub_item['desc']])

                        if 'gross_amount' in sub_item.keys():
                            temp_list.append(self.format_amount(sub_item['gross_amount']))
                        if 'qualifying_amount' in sub_item.keys():
                            temp_list.append(self.format_amount(sub_item['qualifying_amount']))
                        if 'deductable_amount' in sub_item.keys():
                            temp_list.append(self.format_amount(sub_item['deductable_amount']))
                        table_data.append(temp_list)

                        col_widths = [23,357,60,60,60]

                        if 'sub_items' in sub_item.keys():
                            temp_list.append('')
                            col_widths = [23,357,180]

                        table_style = TableStyle(
                            [
                                ("GRID", (0, 0), (-1, 0), 1, (0.75, 0.75, 0.75)),
                                ("GRID", (0, 1), (-1, -1), 1, (0.75, 0.75, 0.75)),
                                ("FONTSIZE", (0, 0), (-1, -1), 7.5),
                                ("GRID", (0, 0), (-1, -1), 1, colors.black),
                                # ("ALIGN", (0, 0), (-1, -1), "RIGHT"),
                                ("ALIGN", (2, 0), (2, -1), "RIGHT"),
                                ("ALIGN", (2, 0), (3, -1), "RIGHT"),
                                ("ALIGN", (2, 0), (4, -1), "RIGHT"),
                                ("ROWHEIGHT", (0, 0), (-1, -1), 40),
                                ("VALIGN", (0, 0), (-1, -1), "MIDDLE"),
                            ]
                        )

                        if 'two_line' in sub_item.keys():
                            table = Table(table_data, colWidths=col_widths, rowHeights=row_height_alt, style=table_style)
                        else:
                            table = Table(table_data, colWidths=col_widths, rowHeights=row_height, style=table_style)

                        story.append(table)


            fin_month_head_table_data = [[Paragraph("TDS Details", heading_style)]]

            fin_month_head_table_style = TableStyle(
                [
                    ("ALIGN", (0, 0), (-1, -1), "CENTER"),
                    ("VALIGN", (0, 0), (-1, -1), "MIDDLE"),
                    ("GRID", (0, 0), (-1, -1), 1, colors.black),
                    ("FONTSIZE", (0, 0), (-1, -1), 7.5),
                    ("ROWHEIGHT", (0, 0), (-1, -1), 40),
                ]
            )

            fin_month_head_table_col_widths = 560
            fin_month_head_table = Table(fin_month_head_table_data,style=fin_month_head_table_style, colWidths=fin_month_head_table_col_widths, rowHeights=row_height)

            story.append(fin_month_head_table)

            month_heading_style = styles['Normal']
            month_heading_style.fontSize = 7
            month_heading_style.textColor = colors.black
            month_heading_style.fontName = "Helvetica-Bold"

            month_list = list(map(lambda x: Paragraph(x, month_heading_style), month_list))

            tds_data = pdf_data_response['tds_data']
            tds_data = list(map(lambda x: self.format_amount(x), tds_data))

            fin_month_table_data = [
            [Paragraph("Month", month_heading_style)] + month_list,
            [Paragraph("TDS", month_heading_style)] + tds_data,
            ]

            fin_month_table_style = TableStyle(
                [
                    ("ALIGN", (0, 0), (-1, -1), "RIGHT"),
                    ("VALIGN", (0, 0), (-1, -1), "MIDDLE"),
                    ("GRID", (0, 0), (-1, -1), 1, colors.black),
                    ("FONTSIZE", (0, 0), (-1, -1), 7.5),
                    ("ROWHEIGHT", (0, 0), (-1, -1), 40),
                ]
            )

            fin_month_table_col_widths = [43.1]*12
            fin_month_table = Table(fin_month_table_data,style=fin_month_table_style, colWidths=fin_month_table_col_widths, rowHeights=row_height)

            story.append(fin_month_table)

            end_sentence = "Declaration : This report is provided solely for guidance purposes and should not be considered as a definitive tax computation.\
                            Please consult the Accounting Department before making any decisions or taking any actions based on this report."

            end_paragraph_style = styles['Heading5']
            end_paragraph_style.alignment = 0
            end_paragraph_style.textColor = colors.black
            end_paragraph_style.fontName = "Helvetica"
            end_paragraph = Paragraph(end_sentence, end_paragraph_style)
            story.append(end_paragraph)


            generated_date_data = f'Report Generated On : {datetime.today().strftime("%d/%m/%Y   %I:%M:%S %p")}'
            generated_date_style = styles['Heading5']
            generated_date_style.alignment = 0
            generated_date_style.textColor = colors.black
            generated_date_style.fontName = "Helvetica"
            generated_date = Paragraph(generated_date_data, generated_date_style)
            story.append(generated_date)

            story.append(PageBreak())

            self.total_pages = 2

            doc.build(story, onFirstPage=self.footer, onLaterPages=self.footer)

            self.__log.info("PDF generated successfully.")
            response["success"] = True
            response["message"] = "PDF generated Succesfully"
            buffer.seek(0)
            response = FileResponse(buffer)
            response['Content-Disposition'] = f'attachment; filename="{output_filename}"'
            #response['err'] = "Hello"

        except Exception as err:
            print(err)
            response["error"] = settings.ERROR_MSG['application_error']\
                .format(err, self.__log.error(self.__exception.get_exception()))
        return response


    def footer(self, canvas, doc):
        page_num = canvas.getPageNumber()
        text = f"Page {page_num} of {self.total_pages}"

    # def tax_compution_pdf(self, request, emp_id, fin_yr_id):
    #     response = {"error": None, "success": None}
    #     month_list=[]
    #     gross_salary = 0
    #     cess_amount = 0
    #     amounts_dict = {}
    #     try:
        width, height = letter

        bottom_margin = 10

        canvas.setFont("Helvetica", 10)
        text_width = canvas.stringWidth(text, "Helvetica", 10)

        x = (width - text_width) / 2
        y = bottom_margin + 10

        canvas.drawString(x, y, text)



    # def tax_compution_pdf(self, request, emp_id, fin_yr_id):
    #     response = {"error": None, "success": None}
    #     month_list=[]
    #     gross_salary = 0
    #     cess_amount = 0
    #     amounts_dict = {}
    #     try:

    #         ctc_employee = TaxDA().get_all_details_from_ctc_emp().filter(emp_id=emp_id,fin_yr_id=fin_yr_id)
    #         ctc_details_list = [{"ctc_name": ctc.name} for ctc in TaxDA().get_all_details_from_ctc()]
    #         for ctc_amount, ctc_details in zip(ctc_employee, ctc_details_list):
    #             amount = Utility().decrypt_ctc_amount(ctc_amount.amount)
    #             ctc_name = ctc_details["ctc_name"]
    #             amounts_dict[ctc_name] = amount
    #             gross_salary += amount

    #         hra_amount = amounts_dict.get('hra')
    #         st_amount = settings.STANDARD_TAX_AMOUNT
    #         taxable_income = gross_salary - hra_amount -amounts_dict.get('pf')-st_amount
    #         tax_period = TaxDA().get_tax_period_from_financial_year_id(fin_yr_id)
    #         regime_type = TaxDA().get_regime_type_by_tax_period_user_id(tax_period.id, emp_id)
    #         taxable_all_objs = TaxDA().get_taxable_amount_by_regime_type()
    #         if taxable_income > settings.MAXIMUM_TAX_AMOUNT:
    #             tax_amount = taxable_all_objs.filter(regime=regime_type.regime_type,amount_range1__lte=taxable_income).last()
    #             taxable_objs = taxable_all_objs.filter(regime=regime_type.regime_type,amount_range2__lte=taxable_income)
    #         else:
    #             tax_amount = taxable_all_objs.filter(regime=regime_type.regime_type,amount_range1__lte=taxable_income,amount_range2__gte=taxable_income).last()
    #             taxable_objs = taxable_all_objs.filter(regime=regime_type.regime_type,amount_range2__lte=taxable_income)
    #         for each in taxable_objs:
    #             cess_amount += each.taxable_amount
    #         cess_amount = (cess_amount + tax_amount.taxable_amount)*0.04
    #         output_filename="income_tax_computation.pdf"
    #         buffer = BytesIO()
    #         doc = SimpleDocTemplate(buffer, pagesize=letter, topMargin=30, bottomMargin=30)
    #         c = canvas.Canvas(buffer, pagesize=letter)

    #         c.setFont("Helvetica", 10)
    #         story = []
    #         styles = getSampleStyleSheet()
    #         heading_style = styles['Heading2']
    #         heading_style.alignment = 1  # Center alignment
    #         heading_style.textColor = colors.black  # Text color
    #         heading_style.fontName = "Helvetica-Bold"  # Bold font

    #         heading_paragraph = Paragraph("Calculating Income Tax with  Lower Tax Slab under new Regime", heading_style)
    #         label_style = styles['BodyText']
    #         label_style.fontName = "Helvetica-Bold"

    #         left_padding = 50  # Example value, adjust according to your actual padding
    #         right_padding = 50  # Example value, adjust according to your actual padding
    #         available_width = letter[0] - left_padding - right_padding
    #         available_height = 1000
    #         tax_surcharge_text = "Tax Surcharge @ 10%/15%/25%/37% (Income more than 50 Lakhs/1 cr/2 cr/5 cr respectively) (Budget 2019)"
    #         tax_surcharge_paragraph = Paragraph(tax_surcharge_text)

    #         # Enable word wrapping for the Paragraph object
    #         tax_surcharge_paragraph.wrapOn(c, available_height,available_width)


    #         col_widths = [450,70]
    #         table_data = [
    #             [heading_paragraph, ""],

    #             ["Gross Annual Income/Salary (with all allowances)", gross_salary],
    #             ["Income from Other Sources", 0.00],
    #             # ["Standard Deduction ", 50000.00],
    #             # ["Less: Deduction under Sec 80C", amounts_dict.get('pf')],
    #             ["Less: Deduction under Sec 80CCD(2) NPS (Employer Contribution)", 0.00],
    #             ["Total Income", taxable_income],
    #             ["Tax Rebate of Rs. 12,500 (For Income of less than 5 lakhs) (Budget 2019)", amounts_dict.get('pf')],
    #             ["Total Tax Payable", amounts_dict.get('pf')],
    #             [tax_surcharge_paragraph, amounts_dict.get('pf')],
    #             ["Add; Edn Cess + Health Cess @ 4%", cess_amount],
    #             ["Net Tax Payable", tax_amount.taxable_amount]

    #         ]


    #         table_style = TableStyle(
    #             [
    #                 ("ALIGN", (0, 0), (-1, -1), "LEFT"),  # Align all cells to the left
    #                 ("VALIGN", (0, 0), (-1, -1), "MIDDLE"),  # Align all cells to the middle
    #                 ("GRID", (0, 0), (-1, -1), 1, colors.black),  # Add gridlines
    #                 ("LEFTPADDING", (0, 0), (-1, -1), 2),  # Add left padding to all cells
    #                 ("RIGHTPADDING", (0, 0), (-1, -1), 2),  # Add right padding to all cells
    #                 ("FONTSIZE", (0, 0), (-1, -1), 10),  # Set font size for all cells
    #                 ("WORDWRAP", (0, 0), (-1, -1)),  # Enable word wrap for all cells
    #                 ("SPAN", (0, 0), (1, 0)),  # Merge first two columns of the first row
    #                 ("ALIGN", (1, 0), (1, -1), "RIGHT"),
    #             ]
    #         )

    #         table = Table(table_data, colWidths=col_widths, style=table_style)
    #         available_width = letter[0] - 50
    #         table.wrap(available_width, doc.pagesize[1])
    #         table_height = table._height
    #         if story and doc.pagesize[1] - table_height < 72:
    #             story.append(PageBreak())

    #         vertical_position = (doc.pagesize[1] - table_height) / 4

    #         story.append(table)

    #         doc.build(story)

    #         self.__log.info("PDF generated successfully.")
    #         response["success"] = "PDF generated successfully."
    #         buffer.seek(0)
    #         response = HttpResponse(buffer,  content_type='application/pdf')
    #         response['Content-Disposition'] = f'attachment; filename="{output_filename}"'

    #     except Exception as err:
    #         print(err)
    #         response["error"] = settings.ERROR_MSG['application_error']\
    #             .format(err, self.__log.error(self.__exception.get_exception()))
    #     return response