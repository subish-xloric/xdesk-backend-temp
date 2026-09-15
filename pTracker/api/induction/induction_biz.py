import os
from io import BytesIO
from datetime import datetime
from django.http import HttpResponse
from reportlab.lib.pagesizes import letter
from reportlab.lib import colors
from reportlab.lib.styles import getSampleStyleSheet, ParagraphStyle
from reportlab.platypus import SimpleDocTemplate, Spacer, Table, TableStyle, Image, Paragraph
from reportlab.lib.units import inch
from PIL import Image as PILImage
from types import SimpleNamespace
from datetime import datetime, date, timedelta
import requests

import PyPDF2


from django.conf import Settings, settings
from django.db import  DatabaseError, transaction
from django.http import response, HttpResponse
from django.template import loader


from pTracker.common.utility import Utility
from pTracker.common.exception_handler import ExceptionHandler
from pTracker.common.logs import Logs

from pTracker.dataaccess.ptracker_access.user_da import UserDA
from pTracker.dataaccess.ptracker_access.induction_da import InductionDA

from pTracker.settings import constants

from pTracker.cronjobs.email_sender import send_email_notification



def new_dto():
    dto = SimpleNamespace()
    return dto

class InductionBL():
    def __init__(self):
        self.__log = Logs()
        self.__exception = ExceptionHandler()
        self.__utility = Utility()


    def __is_valid_date(self,date_string):
        try:
            today = datetime.today().date()
            given_date = datetime.strptime(date_string, "%Y-%m-%d").date()
            if given_date > today:
                return True
            else:
                return False
        except ValueError:
            return False


    def create_induction(self, request):
        response = {"error": None, "success": False, "msg": ""}
        induction_leads = []
        bcc_addresses = []
        try:
            user_id = request.user.id
            role_id, role_name = UserDA().get_user_role_by_id(user_id)
            if role_id not in (2, '2',):
                response["error"] = settings.ERROR_MSG.get("access_denied")
                response["status"] = 403
                return response

            user_name = request.user.first_name + ' ' + request.user.last_name
            data = request.data
            emp_id = int(data.get("employee"))
            due_on = data.get("dueDate")

            if not self.__is_valid_date(due_on):
                response["error"] = 'Invalid due date.'
                response["status"] = 400
                return response

            employee = UserDA().get_user_by_id(emp_id)
            employee_profile = UserDA().get_user_profile_by_id(emp_id)
            induction_obj = InductionDA().get_induction(employee_id=emp_id)

            if induction_obj:
                response["error"] = 'We regret to inform that the induction process has already begun, and we are unable to initiate a new induction program for this employee at this time.'
                response["status"] = 400
                return response

            with transaction.atomic():
                induction_dict = {}
                induction_dict["emp_id"] = emp_id
                induction_dict["status"] = 1  # initiated
                induction_dict["due_on"] = due_on
                induction_dict["created_by"] = user_id

                res = InductionDA().create_induction(induction_dict)
                if res:
                    supervisors, error = UserDA().get_all_supervisors_for_induction()
                    for supervisor in supervisors:
                        induction_leads.append(int(supervisor[0]))
                        bcc_addresses.append(supervisor[3])

                    for each_lead in induction_leads:
                        induction_details_dict = {}
                        induction_details_dict['induction_id'] = res.induction_id
                        induction_details_dict['lead_id'] = each_lead
                        induction_details_dict['status'] = 1  # pending
                        InductionDA().create_induction_details(induction_details_dict)
                        del induction_details_dict

                    self.__create_log('initiated', res.induction_id, user_id)

                    try:
                        user_profile = UserDA().get_user_profile_by_id(user_id)
                        designation = UserDA().get_job_title_by_id(user_profile.job_title).job_title
                    except:
                        designation = ''

                    template_name = 'induction_initaited.html'
                    organization = 'Digital Mesh' if employee_profile.company_id==2 else 'EM Softech'
                    subject = f"Welcome to {organization} Family - Induction Program Information"
                    mail_context = {}
                    mail_context['heading'] = subject
                    mail_context['emp_name'] = employee.first_name+' '+employee.last_name
                    mail_context['organization'] = organization
                    mail_context['hr_name'] = user_name
                    mail_context['hr_position'] = designation
                    mail_context['hr_contact_info'] = request.user.email
                    email_content = self.__generate_email_template(template_name, mail_context)
                    self.send_induction_email(subject, email_content, employee.email, bcc_address=bcc_addresses)
                    response["success"] = True

        except Exception as err:
            response["error"] = settings.ERROR_MSG["application_error"].format(
                str(err), self.__log.error(self.__exception.get_exception())
            )
        return response

    def create_induction_from_create_user(self, user_id, emp_id):
        response = {"error": None, "success": False, "msg": ""}
        induction_leads = []
        bcc_addresses = []
        try:
            user = UserDA().get_user_by_id(user_id)
            user_name = user.first_name+' '+user.last_name
            is_permitted = True  # self.__utility.is_permitted(user_id, 'can_process_payslip') TODO
            if not is_permitted:
                response["error"] = settings.ERROR_MSG.get("access_denied")
                response["status"] = 403
                return response

            employee = UserDA().get_user_by_id(emp_id)
            employee_profile = UserDA().get_user_profile_by_id(emp_id)
            induction_obj = InductionDA().get_induction(employee_id=emp_id)
            if induction_obj:
                response["error"] = 'Induction Process Already Started'
                response["status"] = 400
                return response
            with transaction.atomic():
                induction_dict = {}
                induction_dict["emp_id"] = emp_id
                induction_dict["status"] = 1  # initiated
                induction_dict["due_on"] = datetime.now()+timedelta(days=15) #TODO Verify
                induction_dict["created_by"] = user_id

                res = InductionDA().create_induction(induction_dict)
                if res:
                    supervisors, error = UserDA().get_all_supervisors_for_induction()
                    for supervisor in supervisors:
                        induction_leads.append(int(supervisor[0]))
                        bcc_addresses.append(supervisor[3])
                    for each_lead in induction_leads:
                        induction_details_dict = {}
                        induction_details_dict['induction_id'] = res.induction_id
                        induction_details_dict['lead_id'] = each_lead
                        induction_details_dict['status'] = 1  # pending
                        InductionDA().create_induction_details(induction_details_dict)
                    self.__create_log('initiated', res.induction_id, user_id)
                    try:
                        user_profile = UserDA().get_user_profile_by_id(user_id)
                        designation = UserDA().get_job_title_by_id(user_profile.job_title).job_title
                    except:
                        designation = ''
                    template_name = 'induction_initaited.html'
                    organization = 'Digital Mesh' if employee_profile.company_id==2 else 'EM Softech'
                    subject = f"Welcome to {organization} Family - Induction Program Information"
                    mail_context = {}
                    mail_context['heading'] = subject
                    mail_context['emp_name'] = employee.first_name+' '+employee.last_name
                    mail_context['organization'] = organization
                    mail_context['hr_name'] = user_name
                    mail_context['hr_position'] = designation
                    mail_context['hr_contact_info'] = user.email
                    email_content = self.__generate_email_template(template_name, mail_context)
                    try:
                        bcc_addresses.remove(user.email)
                    except:
                        pass
                    self.send_induction_email(subject, email_content, employee.email, bcc_address=bcc_addresses) #TODO bcc_adresses
                    response["success"] = True
                    del induction_dict, induction_details_dict

        except Exception as err:
            response["error"] = settings.ERROR_MSG["application_error"].format(
                str(err), self.__log.error(self.__exception.get_exception())
            )
        return response


    def get_induction(self, request, filter_status):
        response = {"error": None, "success": False, "data": []}
        induction_objects = list_type = None
        user_dict = {}
        induction_dict = {}
        induction_leads = []
        try:
            user_id = request.user.id
            # is_permitted = True  # self.__utility.is_permitted(user_id, 'can_process_payslip') TODO
            # if not is_permitted:
            #     response["error"] = settings.ERROR_MSG.get("access_denied")
            #     response["status"] = 403
            #     return response


            if filter_status in (0, '0'):
                filter_status = [3]
            elif filter_status in ('4', 4):
                filter_status = [4]
            else:
                filter_status = [1, 2]

            supervisors, error = UserDA().get_all_supervisors_for_induction()
            for supervisor in supervisors:
                induction_leads.append(int(supervisor[0]))

            if user_id in induction_leads:
                induction_objects = InductionDA().get_induction(status=filter_status)
                list_type = 'lead'
                active_users = UserDA().get_all_active_users()
                for each_user in active_users:
                    user_dict[each_user.id] = each_user.first_name+' '+each_user.last_name
                induction_details = InductionDA().get_induction_details_by_lead_id(lead_id=user_id)
                if induction_details:
                    for each_detail in induction_details:
                        induction_dict[each_detail.induction_id] = each_detail.status
            else:
                # user_profile = self.__check_user_emp_status(user_id)
                # if user_profile:
                induction_objects = InductionDA().get_induction(status=filter_status,employee_id=user_id)
                list_type = 'employee'
                user = UserDA().get_user_by_id(user_id)
                user_dict[user_id] = user.first_name+' '+user.last_name

            if induction_objects:
                for each_ind in induction_objects:
                    emp_name = user_dict.get(each_ind.emp_id, None)
                    if not emp_name:
                        continue
                    result_dict = {}
                    result_dict['emp_status'] = each_ind.status

                    result_dict['induction_id'] = each_ind.induction_id
                    result_dict['emp_id'] = each_ind.emp_id
                    result_dict['due_on'] = each_ind.due_on.strftime("%d/%m/%Y")
                    result_dict['due_on_status'] = self.__get_due_on_status(each_ind.due_on)
                    result_dict['initiated_on'] = each_ind.initiated_on.strftime("%d/%m/%Y %I:%M %p")
                    result_dict['created_by'] = each_ind.created_by
                    result_dict['list_type'] = list_type
                    result_dict['emp_name'] = user_dict[each_ind.emp_id]
                    result_dict['progress'] = self.__get_progress(each_ind.induction_id)
                    result_dict['logs'] = self.__get_logs(each_ind.induction_id)
                    result_dict['signed_status'] = induction_dict.get(each_ind.induction_id, 0)
                    response["data"].append(result_dict)

        except Exception as err:
            response["error"] = settings.ERROR_MSG["application_error"].format(
                str(err), self.__log.error(self.__exception.get_exception())
            )
        return response

    def get_induction_details(self, request, induction_id):
        response = {"error": None, "success": False, "data": []}
        induction_objects = list_type = None
        user_dict = {}
        profile_dict = {}
        job_title_dict = {}
        induction_leads = []
        induction_user = 0
        try:
            user_id = request.user.id
            role_id, role_name = UserDA().get_user_role_by_id(user_id)
            inductions = InductionDA().get_induction_by_induction_id(induction_id)
            if inductions:
                induction_user = inductions.emp_id

            if role_id not in (1,2,3,4,'1','2','3','4'):
                if not user_id ==induction_user:
                    response["error"] = settings.ERROR_MSG.get("no_permission")
                    response["status"] = 403
                    return response

            job_title_dict = self._get_job_title_dict()
            all_users = UserDA().get_all_users()
            for each_user in all_users:
                user_dict[each_user.id] = each_user
            supervisors, error = UserDA().get_all_supervisors_for_induction()
            for supervisor in supervisors:
                induction_leads.append(int(supervisor[0]))
            lead_profiles = UserDA().get_user_profiles_by_employee_ids(induction_leads)
            for each_profile in lead_profiles:
                profile_dict[each_profile.user_id] = job_title_dict.get(int(each_profile.job_title))

            induction_objects = InductionDA().get_induction_details_by_induction_id(induction_id)
            for each_detail in induction_objects:
                lead_obj =  user_dict.get(each_detail.lead_id)
                result_dict = {'sign_on' : '-'}
                result_dict['induction_id'] = each_detail.induction_id
                result_dict['lead_id'] = each_detail.lead_id
                result_dict['lead_name'] = lead_obj.first_name + ' ' + lead_obj.last_name if lead_obj.is_active else f'{lead_obj.first_name} {lead_obj.last_name} (Past Employee)'
                result_dict['designation'] = profile_dict.get(each_detail.lead_id) if profile_dict.get(each_detail.lead_id) else UserDA().get_employee_designation(each_detail.lead_id)
                result_dict['status'] = each_detail.status
                if each_detail.sign_on:
                    result_dict['sign_on'] = each_detail.sign_on.strftime("%d/%m/%y %I:%M %p") if each_detail.status == 2 else '-'

                response["data"].append(result_dict)

        except Exception as err:
            response["error"] = settings.ERROR_MSG["application_error"].format(
                str(err), self.__log.error(self.__exception.get_exception())
            )
        return response

    def print_induction_details(self, request):
        pdf_data = []
        induction_objects = list_type = None
        user_dict = {}
        profile_dict = {}
        job_title_dict = {}
        response = None
        induction_leads = []

        try:
            user_id = request.user.id
            emp_id = int(request.GET.get('emp_id'))
            induction_id = request.GET.get('induction_id')
            role_id, role_name = UserDA().get_user_role_by_id(user_id)
            if role_id not in (2, '2',):
                response["error"] = settings.ERROR_MSG.get("no_permission")
                response["status"] = 403
                return response

            job_title_dict = self._get_job_title_dict()

            all_users = UserDA().get_all_users()
            for each_user in all_users:
                user_dict[each_user.id] = each_user

            supervisors, error = UserDA().get_all_supervisors_for_induction()
            for supervisor in supervisors:
                induction_leads.append(int(supervisor[0]))

            lead_profiles = UserDA().get_user_profiles_by_employee_ids(induction_leads)
            for each_profile in lead_profiles:
                profile_dict[each_profile.user_id] = job_title_dict.get(int(each_profile.job_title))

            org_id = UserDA().get_user_organization(emp_id)
            logo_url = self.__get_logo_url(org_id)

            induction_objects = InductionDA().get_induction_details_by_induction_id(induction_id)
            for each_detail in induction_objects:
                lead_obj =  user_dict.get(each_detail.lead_id)
                result_dict = {'sign_on':'-'}
                result_dict['induction_id'] = each_detail.induction_id
                result_dict['lead_id'] = each_detail.lead_id
                result_dict['lead_name'] = lead_obj.first_name + ' ' + lead_obj.last_name if lead_obj.is_active else lead_obj.first_name + ' ' + lead_obj.last_name
                result_dict['designation'] = profile_dict.get(each_detail.lead_id) if profile_dict.get(each_detail.lead_id) else UserDA().get_employee_designation(each_detail.lead_id)
                result_dict['status'] = each_detail.status
                if each_detail.sign_on:
                    result_dict['sign_on'] = each_detail.sign_on.strftime("%d/%m/%Y %I:%M %p") if each_detail.status == 2 else '-'
                pdf_data.append(result_dict)
            emp_name = user_dict.get(emp_id).first_name+' '+user_dict.get(emp_id).last_name
            emp_joined_data = user_dict.get(emp_id).date_joined.strftime("%d/%m/%Y")
            emp_profile = UserDA().get_user_profile_by_id(emp_id)
            designation = job_title_dict.get(int(emp_profile.job_title))
            emp_data = {'name': emp_name, 'designation': designation, 'joined_date': emp_joined_data}

            response = self.generate_pdf_with_table(logo_url, pdf_data, emp_data, 'induction_details.pdf')

        except Exception as err:
            self.__log.error(self.__exception.get_exception())
        return response

    def generate_pdf_with_table(self, logo_url, data, additional_data, filename):
        result = None
        try:
            # Create a BytesIO object to hold the PDF file
            buffer = BytesIO()

            # Create the PDF
            doc = SimpleDocTemplate(buffer, pagesize=letter)

            # Define the styles
            styles = getSampleStyleSheet()
            table_style = TableStyle([
                ('BACKGROUND', (0, 0), (-1, 0), colors.white),
                ('TEXTCOLOR', (0, 0), (-1, 0), colors.black),
                ('ALIGN', (0, 0), (-1, 0), 'CENTER'),  # Align the heading at the center
                ('ALIGN', (0, 1), (1, -1), 'LEFT'),  # Align the first two columns to the left
                ('ALIGN', (2, 1), (-1, -1), 'CENTER'),  # Align the remaining columns to the center
                ('FONTNAME', (0, 0), (-1, 0), 'Helvetica-Bold'),
                ('FONTSIZE', (0, 0), (-1, 0), 12),
                ('BOTTOMPADDING', (0, 0), (-1, 0), 12),
                ('BACKGROUND', (0, 1), (-1, -1), colors.white),
                ('GRID', (0, 0), (-1, -1), 1, colors.black),
                ('WIDTH', (0, 0), (-1, -1), '100%')
            ])

            # Create the elements to add to the PDF
            elements = []

            logo_image = self.__load_image(logo_url)
            logo_image.hAlign = 'RIGHT'
            elements.append(logo_image)

            # Add more space between the first table and the logo
            elements.append(Spacer(1, 13))  # Increase the second parameter to adjust the space

            # Create the report title
            title_style = ParagraphStyle('TitleStyle', parent=styles['Normal'], fontName='Helvetica-Bold', fontSize=14, alignment=1)
            text = "Induction Status Report"
            paragraph = Paragraph(text, title_style)
            elements.append(paragraph)

            # Add more space between the first table and the logo
            elements.append(Spacer(1, 20))  # Increase the second parameter to adjust the space

            # Create the additional table data
            additional_table_data_formatted = [['Employee Name', 'Designation', 'Joining Date']]
            additional_table_data_formatted.append([additional_data['name'], additional_data['designation'], additional_data['joined_date']])

            # Create the additional table
            col_widths = [2.15 * inch, 2.80 * inch, 1.50 * inch]
            additional_table = Table(additional_table_data_formatted, colWidths=col_widths)
            additional_table.setStyle(table_style)
            elements.append(additional_table)

            # Add a spacer
            elements.append(Spacer(1, 22))

            # Create the table data
            table_data = [['Emp. Name', 'Designation', 'Met Date & Time', 'Status']]
            for item in data:
                if str(item['status']) == '1':
                    status_image = Image(os.path.join(settings.MEDIA_ROOT, f'assets/images/not-done.png'), width=15, height=15)
                else:
                    status_image = Image(os.path.join(settings.MEDIA_ROOT, f'assets/images/done.png'), width=15, height=15)
                table_data.append([item['lead_name'], item['designation'], item['sign_on'], status_image])

            # Create the table
            col_widths = [1.5 * inch, 2.5 * inch, 1.55 * inch, 0.85 * inch]
            table = Table(table_data, repeatRows=1, colWidths=col_widths)
            table.setStyle(table_style)
            elements.append(table)

            # Add a spacer
            elements.append(Spacer(1, 7))

            # Add the text "This is a computer-generated document. No signature is required."
            text = "This document is computer-generated. No signature is required."
            paragraph = Paragraph(text, styles['Normal'])
            elements.append(paragraph)

            # Build the PDF
            doc.build(elements)

            # Set the buffer's file pointer at the beginning
            buffer.seek(0)

            # Create an HttpResponse with the PDF file as an attachment
            result = HttpResponse(content_type='application/pdf')
            result['Content-Disposition'] = f'attachment; filename="{filename}"'
            result.write(buffer.getvalue())

            # Close the buffer
            buffer.close()
        except Exception as err:
            self.__log.error(self.__exception.get_exception())
        return result


    def update_induction_details(self, request):
        response = {"error": None, "success": False}
        res = None
        try:
            user_id = request.user.id
            request_data = request.data
            status = request_data.get('status') #4- cancel #2- completed
            induction_id = request_data.get('induction_id')

            role_id, role_name = UserDA().get_user_role_by_id(user_id)
            if status in ('4', 4):
                if role_id not in (2, '2',):
                    response["error"] = settings.ERROR_MSG.get("no_permission")
                    response["status"] = 403
                    return response
            else:
                if role_id not in (1,2,3,4,'1','2','3','4'):
                    response["error"] = settings.ERROR_MSG.get("no_permission")
                    response["status"] = 403
                    return response

            inductions = InductionDA().get_induction_by_induction_id(induction_id)
            if inductions.status == 4:
                response["error"] = 'The induction has regrettably been cancelled'
                response["status"] = 400
                return response

            if status=='4':
                status_text='cancel'
                InductionDA().delete_induction_details_by_induction_id(induction_id)
                InductionDA().update_induction(induction_id, {'status': int(status)})
            else:
                detail_obj = InductionDA().get_induction_details_by_induction_id(lead_id=user_id, induction_id=induction_id)

                if inductions.emp_id == user_id:
                    response["error"] = settings.ERROR_MSG.get("no_permission")
                    response["status"] = 403
                    return response

                if detail_obj.last().status == 2:
                    response["error"] = 'Your sign has already been recorded. No further action is required on your part'
                    response["status"] = 400
                    return response
                status_text='sign'

                res = InductionDA().update_induction_details(induction_id, {'status': int(status), 'sign_on': datetime.now()}, user_id)
                if res:
                    inductions = InductionDA().get_induction_details_by_induction_id(induction_id)
                    if len(inductions.filter(status=1))==0:
                        InductionDA().update_induction(induction_id, {'status': 3}) #set completed
                    else:
                        InductionDA().update_induction(induction_id, {'status': 2})

            self.__create_log(status_text, induction_id, user_id)
            response["success"] = True

        except Exception as err:
            response["error"] = settings.ERROR_MSG["application_error"].format(
                str(err), self.__log.error(self.__exception.get_exception())
            )
        return response

    def send_induction_reminder(self, request, induction_id):
        response = {"error": None, "success": False}
        template_name = subject = ''
        bcc_addresses = []
        try:
            user_id = request.user.id
            user_name = request.user.first_name + " " + request.user.last_name
            role_id, role_name = UserDA().get_user_role_by_id(user_id)
            if role_id not in (2, '2',):
                response["error"] = settings.ERROR_MSG.get("no_permission")
                response["status"] = 403
                return response

            induction_obj = InductionDA().get_induction_by_induction_id(induction_id)
            if not induction_obj:
                response["error"] = settings.ERROR_MSG.get("no_permission")
                response["status"] = 403
                return response

            if induction_obj.status in (3,4):
                if induction_obj.status == 3:
                    msg = "Induction has been successfully completed, rendering any reminder mail unnecessary."
                else:
                    msg = "Induction has been cancelled, rendering any reminder mail unnecessary."
                response["error"] = msg
                response["status"] = 403
                return response

            supervisors, error = UserDA().get_all_supervisors_for_induction()
            induction_detail_leads = InductionDA().get_induction_details_by_induction_id(induction_id, 2).values_list('lead_id', flat=True)
            for supervisor in supervisors:
                if int(supervisor[0]) in induction_detail_leads:
                    continue
                bcc_addresses.append(supervisor[3])
            emp_id = induction_obj.emp_id
            employee = UserDA().get_user_by_id(emp_id)
            employee_profile = UserDA().get_user_profile_by_id(emp_id)

            if datetime.now().date()>induction_obj.due_on.date():
                template_name = "induction_reminder_after_due.html"
                subject = "Urgent: Completion of Induction Program Required - Overdue Deadline"
            elif datetime.now().date()<=induction_obj.due_on.date():
                template_name = "induction_reminder_before_due.html"
                subject = "Urgent: Completion of Induction Program Required - Deadline Approaching"

            organization = 'Digital Mesh' if employee_profile.company_id==2 else 'EM Softech'
            mail_context = {}
            mail_context['heading'] = subject
            mail_context['emp_name'] = employee.first_name+' '+employee.last_name
            mail_context['organization'] = organization
            mail_context['hr_name'] = user_name
            mail_context['designation'] = self.__get_designation_emp_id(user_id)
            mail_context['hr_contact_info'] = request.user.email
            mail_context['due_on'] = induction_obj.due_on.strftime("%d/%m/%Y")
            email_content = self.__generate_email_template(template_name, mail_context)
            self.send_induction_email(subject, email_content, employee.email, bcc_address=bcc_addresses)
            response["success"] = True

        except Exception as err:
            response["error"] = settings.ERROR_MSG["application_error"].format(
                str(err), self.__log.error(self.__exception.get_exception())
            )
        return response

    def get_new_employees(self, request):
        response = {"error": None, "success": False, "data":[]}
        user_dict = {}
        user_ids = []
        try:
            user_id = request.user.id
            role_id, role_name = UserDA().get_user_role_by_id(user_id)
            if role_id not in (2, '2',):
                response["error"] = settings.ERROR_MSG.get("access_denied")
                response["status"] = 403
                return response

            active_users = UserDA().get_all_active_users()
            for each_user in active_users:
                user_dict[each_user.id] = each_user
                user_ids.append(each_user.id)
            probation_employees = UserDA().get_user_profiles_by_employee_ids(user_ids, 1) #1- Probation status
            if probation_employees:
                for each_employee in probation_employees:
                    user_obj = user_dict.get(each_employee.user_id)
                    emp_name = user_obj.first_name+' '+user_obj.last_name
                    response['data'].append({'id': each_employee.user_id, 'emp_name': emp_name})

        except Exception as err:
            response["error"] = settings.ERROR_MSG["application_error"].format(
                str(err), self.__log.error(self.__exception.get_exception())
            )
        return response

    def send_induction_email(self, subject, content, to_email, cc_addresses=[], bcc_address=[]):
        mail_dto = {}
        mail_dto["subject"] = subject
        mail_dto["from_address"] = settings.EMAIL_ADDRESS['do_not_reply']['name']
        mail_dto["body"] = content
        mail_dto["to_addresses"] = [to_email]
        mail_dto["cc_addresses"] = cc_addresses
        mail_dto["bcc_address"] = bcc_address
        mail_dto["smtp_username"] = settings.EMAIL_ADDRESS['do_not_reply']['mailID']
        mail_dto["smtp_password"] = settings.EMAIL_ADDRESS['do_not_reply']['password']
        send_email_notification.apply_async(
            [mail_dto, 1], queue=settings.CELERY_QUEUE['mail_sender'])

    def __generate_email_template(self, email_template, context):
        html_email = loader.render_to_string(email_template, context)
        return html_email

    def _get_job_title_dict(self):
        job_title_dict = {}
        job_titles = UserDA().get_all_job_titles()
        for job in job_titles:
            job_title_dict[job.id] = job.job_title
        return job_title_dict

    def __load_image(self, image_path):
        image_content = ''
        try:
            image_content = PILImage.open(image_path)
            logo_width, logo_height = image_content.size
            logo_aspect = logo_width / float(logo_height)
            image_content = Image(image_path, width=1.5 * inch, height=(1.5 * inch) / logo_aspect)
        except:
            pass
        return image_content

    def __get_logo_url(self, org_id):
        if org_id==2:
            #return settings.DEFUALT_API_URL + settings.STATIC_URL + "dm_desk/images/dm-logo.png"
            return os.path.join(settings.MEDIA_ROOT, f'logo/DMlogo.png')
        else:
            #return settings.DEFUALT_API_URL + settings.STATIC_URL + "dm_desk/images/em-logo.png"
            return os.path.join(settings.MEDIA_ROOT, f'logo/EMlogo.png')

    def __create_log(self, status, induction_id, user_id=0):
        action = None
        try:
            log_dict = {}
            user = UserDA().get_user_by_id(user_id)
            user_name = user.first_name+' '+user.last_name
            current_datetime = datetime.now()
            formatted_datetime = current_datetime.strftime("%d/%m/%y %I:%M %p")
            log_dict['induction_id'] = induction_id

            if status=='initiated':
                action = log_dict['action'] = f"Induction Initiated by {user_name} at {formatted_datetime}"
            elif status=='sign':
                action = log_dict['action'] = f"Induction Signed by {user_name} at {formatted_datetime}"
            elif status=='cancel':
                action = log_dict['action'] = f"Induction Cancelled by {user_name} at {formatted_datetime}"
            if action:
                InductionDA().create_induction_log(log_dict)
        except:
            pass

    def __check_user_emp_status(self, user_id):
        user = None
        try:
            user_profile = UserDA().get_user_profile_by_id(user_id)
            if user_profile.job_status == 1:  # probation employees only
                user = user_profile
        except Exception as err:
            pass
        return user

    def __get_progress(self, induction_id):
        completed = total = progress = 0
        total_induction_object = InductionDA().get_induction_details_by_induction_id(induction_id=induction_id)
        if total_induction_object:
            total = total_induction_object.count()
            induction_object = total_induction_object.filter(status=2)
            if induction_object:
                completed = induction_object.count()
        return f'{completed}/{total}'


    def __get_logs(self, induction_id):
        result = []
        try:
            induction_logs = InductionDA().get_induction_logs(induction_id)
            for each_logs in induction_logs:
                result.append(each_logs.action)
        except:
            pass
        return result

    def __get_due_on_status(self, due_date):
        result = False
        try:
            today = datetime.now().today()
            if due_date < today:
                result = True
        except:
            pass
        return result

    def __get_designation_emp_id(self, user_id):
        try:
            user_profile = UserDA().get_user_profile_by_id(user_id)
            designation = UserDA().get_job_title_by_id(user_profile.job_title).job_title
        except:
            designation = ''
        return designation



# TODO List
#1- Create permission
#2- check already created
#3- In- progress status?
