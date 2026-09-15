import json
import io
import os
import tempfile
import zipfile
import PyPDF2
import pikepdf
from types import SimpleNamespace
from cryptography.fernet import Fernet
from datetime import datetime, date, timedelta

from django.conf import Settings, settings
from django.db import  DatabaseError, transaction
from django.http import response, HttpResponse
from django.template import loader

from pTracker.common.logs import Logs
from pTracker.common.file_manager import FileManager
from pTracker.common.utility import Utility
from pTracker.common.exception_handler import ExceptionHandler
from pTracker.dataaccess.ptracker_access.user_da import UserDA
from pTracker.dataaccess.ptracker_access.finance_da import FinanaceDA
from pTracker.cronjobs.email_sender import send_email_notification

def new_dto():
    dto = SimpleNamespace()
    return dto

class FinanceBL():
    def __init__(self):
        self.__log = Logs()
        self.__exception = ExceptionHandler()
        self.__utility = Utility()


    def __is_show_action_button(self, num, start_year, end_year, obj_payslip_header):
        view_action =False
        current_day = datetime.now()
        if obj_payslip_header and obj_payslip_header.status == 3:
            view_action = False
        elif num>3:
            if current_day.month==num and current_day.year == start_year:
                view_action = True
            elif num<current_day.month and current_day.year == start_year:
                view_action = True
        elif num<4:
            if current_day.month==num and current_day.year == end_year:
                view_action = True
            elif num<current_day.month and current_day.year == end_year:
                view_action = True
        return view_action

    def manage_payslip(self, request, financial_year_id, organization):
        response = {"headers": [], "error": None}
        try:
            user_id = request.user.id
            is_permitted = self.__utility.is_permitted(user_id, 'can_process_payslip')
            if not is_permitted:
                response["error"] = settings.ERROR_MSG.get('access_denied')
                response['status'] = 403
                return response

            current_day = datetime.now()
            view_action =False
            financial_month_dict = settings.MONTHS
            financial_year_obj = FinanaceDA().get_financial_year_by_id(financial_year_id)
            start_year = financial_year_obj.start_date.year
            end_year = financial_year_obj.end_date.year

            params = new_dto()
            params.financial_year_id = financial_year_id
            params.organization = organization
            resultObj = FinanaceDA().get_payslip_headers(params)
            response['headers'] = []

            for num, month in financial_month_dict.items():
                payslip_head = resultObj.filter(month=num).last()
                view_action = self.__is_show_action_button(num, start_year, end_year, payslip_head)

                temp = {
                    'pageHeader': payslip_head.pay_header_id if payslip_head else 0,
                    'statusID': payslip_head.status if payslip_head and not payslip_head.is_reverted else 1,
                    'statusText': settings.FINANCE_STATUS.get(payslip_head.status) if payslip_head and not payslip_head.is_reverted else 'Pending',
                    'comment': payslip_head.comment if payslip_head else '',
                    'month': settings.MONTHS.get(int(payslip_head.month)) if payslip_head else month,
                    'monthID': payslip_head.month if payslip_head else num,
                    'year': payslip_head.year if payslip_head else (start_year if num > 3 else end_year),
                    'organization': organization,
                    'financial_year_id': financial_year_id,
                    'view_actions':view_action,
                    'logs': self.__get_todo_list(payslip_head.pay_header_id)  if payslip_head else []
                }
                response['headers'].append(temp)
                del temp
        except Exception as err:
            response["error"] = settings.ERROR_MSG['application_error']\
                .format(str(err), self.__log.error(self.__exception.get_exception()))
        return response

    def get_dropdown_prams(self, request):
        response = {"organizations": [], "Lastyears": []}
        user_da = UserDA()
        try:
            for k, v in settings.ORGANIZATION.items():
                response['organizations'].append({"id": k, "name": v})
            lastYears = FinanaceDA().get_last_years()
            for each in lastYears:
                current_day = datetime.now().date()
                current = True if current_day>=each.start_date.date() and current_day<=each.end_date.date() else False
                response['Lastyears'].append({'id': each.financial_year_id, 'name':  each.description, 'current': current})
            response["Lastyears"].reverse()
        except Exception as err:
            response["error"] = settings.ERROR_MSG['application_error']\
                .format(str(err), self.__log.error(self.__exception.get_exception()))
        return response

    def process_payslip(self, request):
        response = {"error":None, "success": False, 'msg': ''}
        user_dict = file_dict = {}
        log_summary = []
        try:
            user_id = request.user.id
            is_permitted = self.__utility.is_permitted(user_id, 'can_process_payslip')
            # role_id, role_name = UserDA().get_user_role_by_id(user_id)
            # if role_id in (2,3,4):
            #     is_permitted = True
            if not is_permitted:
                response["error"] = settings.ERROR_MSG.get('access_denied')
                response['status'] = 403
                return response

            organization = request.data.get('organization')
            processedFor = request.data.get('processedFor').split(' ')
            year = processedFor[1]
            month = self.get_month_number(processedFor[0])

            if FinanaceDA().is_payslip_header_exists(month,year,organization):
                msg = """The payslip for the month {0} - {1}
                has already been processed or under processing. If you wish to reprocess it,
                please revoke the same first.""".format(processedFor[0], year)
                response["error"] = msg
                response['status'] = 403
                return response

            active_employees = UserDA().get_all_active_users()
            for employee in active_employees:
                user_dict[employee.id] = employee

            file = request.data.get('zipFile')
            comment = request.data.get('comment')
            organization = request.data.get('organization')
            financial_year_id = request.data.get('financialYearId')


            files = self.extract_zip_file(file)
            employee_list = self.get_employee_ids_by_organization(organization)
            employee_ids = employee_list.values_list('user_id', flat=True)

            with transaction.atomic():
                #try:
                employee_pay_header_data = {
                    'financial_year_id': financial_year_id,
                    'month': self.get_month_number(processedFor[0]),
                    'year': processedFor[1],
                    'comment': comment,
                    'status': 2,
                    'organization': organization,
                    'processed_date_time': datetime.now(),
                    'published_date_time': None,
                    'processed_by': user_id,
                    'published_by': None,
                    'is_reverted':0,
                    'reverted_reason':'',
                    'reverted_by':None
                }

                header_data = FinanaceDA().create_or_update_employee_pay_header(employee_pay_header_data)
                self.__create_finanace_logs(request, 2, header_data.pay_header_id)

                for each in files:
                    try:
                        file_names = each[0].split("/")
                        file_name = file_names[1]
                        if file_name:
                            emp_code = file_name.split('_')[0]
                            file_dict[emp_code] = each[1]
                    except:
                        self.__log.error(self.__exception.get_exception())
                        continue

                for each_emp in employee_ids:
                    full_name = ''
                    emp_code = user_dict[each_emp].username
                    file_obj = file_dict.get(emp_code, None)
                    employee = user_dict.get(each_emp)
                    emp_id = each_emp
                    employee_profile = employee_list.get(user_id=emp_id)
                    password =  self.__generate_payslip_pwd(employee.first_name, employee_profile.dob)
                    full_name = employee.first_name +' '+employee.last_name

                    if emp_id not in employee_ids:
                        continue

                    if file_obj:
                        org_name = settings.ORGANIZATION[int(organization)]
                        file_name = f"{emp_code}_payslip_{processedFor[0]}_{processedFor[1]}.pdf"
                        folder_path = self.__get_payslip_folder(organization, processedFor[1], self.get_month_number(processedFor[0]))
                        file_path = folder_path + file_name

                        dummy_file_path = self.__get_payslip_dummy_folder(folder_path) + file_name
                        FileManager().upload_encrypted_file(dummy_file_path, file_obj)

                        protected_pdf = self.__create_password_protected_pdf(file_obj, password)
                        FileManager().upload_file(file_path, protected_pdf)
                        employee_pay_details_data = {
                            'financial_year_id': financial_year_id,
                            'pay_header_id': header_data.pay_header_id,
                            'emp_id': emp_id,
                            'emp_code': emp_code,
                            'month': self.get_month_number(processedFor[0]),
                            'year': processedFor[1],
                            'processed_date_time': datetime.now(),
                            'published_date_time': None,
                            'comment': comment,
                            'file_name': file_name,
                            'status': 2,  #Under Process
                        }
                        FinanaceDA().create_or_update_employee_pay_details(employee_pay_details_data)
                        response['success'] = True
                    else:
                        log_summary.append(f'Payslip not found for the employee {full_name}')
                if len(log_summary)>0:
                    user_email = request.user.email
                    self.__send_summary(user_email, log_summary)
                # except Exception as err:
                #     self.__log.error(self.__exception.get_exception())
                #     raise ValueError
                response['success'] = True

        except Exception as err:
            response["error"] = settings.ERROR_MSG['application_error']\
                .format(str(err), self.__log.error(self.__exception.get_exception()))
        return response

    def validate_payslip(self, request, header_id):
        response = {"pay_slips": [], "error": None, 'header': ''}
        user_dict = {}
        try:
            user_id = request.user.id
            is_permitted = self.__utility.is_permitted(user_id, 'can_validate_payslip')
            # role_id, role_name = UserDA().get_user_role_by_id(user_id)
            # if role_id in (2,3,4):
            #     is_permitted = True
            if not is_permitted:
                response["error"] = settings.ERROR_MSG.get('access_denied')
                response['status'] = 403
                return response

            active_employees = UserDA().get_all_active_users()
            for employee in active_employees:
                user_dict[employee.username] = employee.first_name +' '+employee.last_name

            payslip_header = FinanaceDA().get_payslip_header(header_id)
            if payslip_header:
                response['header'] = f'Payslips for the Month of {settings.MONTHS.get(int(payslip_header.month))} {payslip_header.year}'

            payslip_details = FinanaceDA().get_payslip_details_by_header_id(header_id)
            for each_slip in payslip_details:
                temp = {}
                temp['pay_detail_id'] = each_slip.pay_detail_id
                temp['pay_header_id'] = each_slip.pay_header_id
                temp['financial_year_id'] = each_slip.financial_year_id
                temp['emp_id'] = each_slip.emp_id
                temp['emp_code'] = each_slip.emp_code
                temp['month'] = each_slip.month
                temp['year'] = each_slip.year
                temp['emp_name'] = user_dict[each_slip.emp_code]

                if each_slip.processed_date_time is not None:
                    temp['processed_date_time'] = each_slip.processed_date_time.strftime("%d/%m/%Y")
                else:
                    temp['processed_date_time'] = None

                if each_slip.published_date_time is not None:
                    temp['published_date_time'] = each_slip.published_date_time.strftime("%d/%m/%Y")
                else:
                    temp['published_date_time'] = None

                temp['comment'] = each_slip.comment
                temp['file_name'] = each_slip.file_name
                temp['statusID'] = each_slip.status
                temp['statusText'] = settings.FINANCE_STATUS.get(payslip_header.status) if  not payslip_header.is_reverted else 'Pending',

                response['pay_slips'].append(temp)

        except Exception as err:
            response["error"] = settings.ERROR_MSG['application_error']\
                .format(str(err), self.__log.error(self.__exception.get_exception()))
        return response

    def __create_password_protected_pdf(self, file_data, password):
        pdf_in = io.BytesIO(file_data)
        pdf_out = io.BytesIO()
        with pikepdf.open(pdf_in) as pdf:
            pdf.save(pdf_out, encryption=pikepdf.Encryption(owner=password, user=password))
        return pdf_out.getvalue()


    def revoke_payslip(self, request):
        response = {"error": None, "success": False}
        is_success = False
        try:
            user_id = request.user.id
            is_permitted = self.__utility.is_permitted(user_id, 'can_revoke_payslip')
            if not is_permitted:
                response["error"] = settings.ERROR_MSG.get('access_denied')
                response['status'] = 403
                return response

            revert_type = request.data.get('type')
            reason = request.data.get('reason')

            if revert_type == '1':
                header_id = request.data.get('header_id')
                payslip_header = FinanaceDA().get_payslip_header(header_id)
                if payslip_header and payslip_header.status==3:
                    msg = "Unfortunately, it is not possible to revoke this payslip as it has already been published."
                    response["error"] = msg
                    response['status'] = 403
                    return response

                folder_path = self.__get_payslip_folder(payslip_header.organization, payslip_header.year, payslip_header.month)
                payslip_details = FinanaceDA().get_payslip_details_by_header_id(header_id)
                is_success = self.__revoke_payslip_process(user_id, header_id, reason)
                if is_success:
                    self.__physical_delete_files(folder_path, payslip_details)
                    self.__physical_delete_dummy_files(folder_path, payslip_details)
                self.__create_finanace_logs(request, 0, header_id, reason)
            elif revert_type == '2': #reuploading file
                zipinfo = request.data.get('zipFile')
                details_id = request.data.get('detail_id')
                payslip_details = FinanaceDA().get_payslip_by_id(details_id).last()

                employee_profile = UserDA().get_user_profile_by_id(payslip_details.emp_id)
                employee = UserDA().get_user_by_emp_id(payslip_details.emp_code)
                folder_path = self.__get_payslip_folder(employee_profile.company_id, payslip_details.year, payslip_details.month)
                file_path = folder_path + payslip_details.file_name
                pwd = self.__generate_payslip_pwd(employee.first_name, employee_profile.dob)

                file_data = zipinfo.read()
                dummy_file_path = self.__get_payslip_dummy_folder(folder_path) + payslip_details.file_name
                FileManager().upload_encrypted_file(dummy_file_path, file_data)

                protected_pdf = self.__create_password_protected_pdf(file_data, pwd)
                FileManager().upload_file(file_path, protected_pdf)
                is_success = FinanaceDA().update_payslip_details(details_id, {'comment': reason})

            if is_success:
                response['success'] = is_success
        except Exception as err:
            response["error"] = settings.ERROR_MSG['application_error']\
                .format(str(err), self.__log.error(self.__exception.get_exception()))
        return response

    def publish_payslip(self, request):
        response = {"error": None, "success": False}
        try:
            user_id = request.user.id
            is_permitted = self.__utility.is_permitted(user_id, 'can_publish_payslip')
            if not is_permitted:
                response["error"] = settings.ERROR_MSG.get('access_denied')
                response['status'] = 403
                return response

            header_id = request.data.get('header_id')
            messages = request.data.get('messages', '')
            headerDict = {}
            headerDict['published_date_time'] = datetime.now()
            headerDict['published_by'] = user_id
            headerDict['status'] = 3
            result = FinanaceDA().update_payslip_header(header_id, headerDict)
            header_obj = FinanaceDA().get_payslip_header(header_id)
            if result and header_obj:
                organization = int(header_obj.organization)
                detailDict = {}
                detailDict['status'] = 3
                detailDict['published_date_time'] = datetime.now()
                result = FinanaceDA().update_payslip_details_by_header(header_id, detailDict)
                if result:
                    self.__create_finanace_logs(request, 3, header_id)
                    emp_pay_header = FinanaceDA().get_payslip_header(header_id)
                    month = settings.MONTHS[int(emp_pay_header.month)]
                    year = emp_pay_header.year
                    user_profile = UserDA().get_user_profile_by_id(user_id)
                    job_title = UserDA().get_job_title_by_id(user_profile.job_title)
                    job_title = job_title.job_title
                    month_and_year = f"{month} {year}"

                    bcc_address = [settings.TEAM_EMAIL if organization==2 else settings.EM_TEAM_EMAIL]
                    email_dto = new_dto()
                    email_dto.heading = f"Payslip Notification: Your Payslip for {month_and_year} is Now Available"
                    email_dto.emp_name = request.user.first_name+' '+request.user.last_name
                    email_dto.emp_position = job_title
                    email_dto.emp_email = settings.EMAIL_ADDRESS['account_dm']['mailID'] if organization==2 else settings.EMAIL_ADDRESS['account_em']['mailID']
                    email_dto.month_and_year = month_and_year
                    email_dto.messages = messages
                    contents = self.generate_pay_slip_published_notification(email_dto)
                    self.send_pay_slip_published_notification(contents, email_dto.emp_email, email_dto.heading,\
                         organization=organization, bcc_address=bcc_address)
                    response['success'] = True

                    folder_path = self.__get_payslip_folder(organization, year, emp_pay_header.month)
                    payslip_details = FinanaceDA().get_payslip_details_by_header_id(header_id)
                    self.__physical_delete_dummy_files(folder_path, payslip_details)

        except Exception as err:
            response["error"] = settings.ERROR_MSG['application_error']\
                .format(str(err), self.__log.error(self.__exception.get_exception()))
        return response


    def download_payslip(self, request):
        result = {}
        is_permitted = False

        try:
            user_id = request.user.id
            is_permitted = self.__utility.is_permitted(user_id, 'can_validate_payslip')

            filename = request.GET.get('filename')
            emp_code = filename.split('_')[0]

            employee = UserDA().get_user_by_emp_id(emp_code)

            if not is_permitted:
                if user_id != employee.id:
                    response["error"] = settings.ERROR_MSG.get('access_denied')
                    response['status'] = 403
                    return response

            month = filename.split('_')[2]
            year = filename.split('_')[3].split('.')[0]

            employee_profile = UserDA().get_user_profile_by_id(employee.id)
            org_name = settings.ORGANIZATION[employee_profile.company_id]
            folder_path = self.__get_payslip_folder(employee_profile.company_id, year, self.get_month_number(month))
            filename = folder_path + filename

            file_content = FileManager().read_file(filename)
            if file_content:
                result = HttpResponse(content_type='application/pdf')
                result['Content-Disposition'] = f'attachment; filename="{filename}"'
                result.write(file_content)
                return result
            else:
                return HttpResponse(status=404)
        except Exception as err:
            result["error"] = settings.ERROR_MSG['application_error']\
                .format(err, self.__log.error(self.__exception.get_exception()))
        return result

    def get_my_pay_list(self, request, year):
        response = {"headers": [], "error": None}
        try:
            user_id = request.user.id

            financial_year_obj = FinanaceDA().get_financial_year_by_id(year)
            start_year = financial_year_obj.start_date.year
            end_year = financial_year_obj.end_date.year
            financial_year_id = financial_year_obj.financial_year_id
            resultObj = FinanaceDA().get_all_employee_details(financial_year_id, user_id)

            financial_month_dict = settings.MONTHS
            response['headers'] = []

            for num, month in financial_month_dict.items():
                view_button = False
                currentObj = resultObj.filter(month=num).last()
                current_year = currentObj.year if currentObj else (start_year if num > 3 else end_year)
                try:
                    date_joined = request.user.date_joined
                    current_date = datetime(current_year, num, 1)

                    if current_date.year > date_joined.year or (current_date.year == date_joined.year and current_date.month >= date_joined.month):
                        view_button = True
                except:
                    pass
                statusID = 1
                if not view_button:
                    statusID = 4 # 'NA'
                elif currentObj and currentObj.status:
                    statusID = int(currentObj.status)

                temp = {
                    'statusID': statusID,
                    'statusText': settings.FINANCE_STATUS.get(currentObj.status) if currentObj else 'Pending',
                    'month': settings.MONTHS.get(int(currentObj.month)) if currentObj else month,
                    'monthID': currentObj.month if currentObj else num,
                    'year': current_year,
                    'financial_year_id': financial_year_obj.financial_year_id,
                    'file_name': currentObj.file_name if currentObj else '',
                    'processed_date':currentObj.published_date_time.strftime("%d/%m/%Y %I:%M %p") if currentObj and currentObj.published_date_time else '-',
                    'logs': []
                }

                response['headers'].append(temp)
        except Exception as err:
            response["error"] = settings.ERROR_MSG['application_error']\
                .format(str(err), self.__log.error(self.__exception.get_exception()))
        return response

    def __create_finanace_logs(self, request, status, header_id, reason=''):
        response = False
        try:
            log_dict = {}
            user_id = request.user.id
            username = request.user.first_name +' '+request.user.last_name
            current_datetime = datetime.now()
            formatted_datetime = current_datetime.strftime("%d/%m/%y %I:%M %p")
            if status in (2,3):
                log_dict['log_message'] = settings.FINANCE_PAY_SLIP_LOG[status].format(username, formatted_datetime)
            else:#Revert Log
                log_dict['log_message'] = settings.FINANCE_PAY_SLIP_LOG[0].format(username, formatted_datetime, reason)
            log_dict['created_by'] = user_id
            log_dict['header_id'] = header_id
            log_dict['created_date'] = current_datetime
            FinanaceDA().create_finanace_log(log_dict)
        except Exception as err:
            self.__log.error(self.__exception.get_exception())
        return response



    def __physical_delete_files(self, folder_path, payslip_details):
        try:
            for payslip in payslip_details:
                FileManager().delete_file(folder_path + payslip.file_name)
        except Exception as e:
            self.__log.error(self.__exception.get_exception())


    def __physical_delete_dummy_files(self, folder_path, payslip_details):
        try:
            dummy_folder_path = self.__get_payslip_dummy_folder(folder_path)
            for payslip in payslip_details:
                FileManager().delete_file(dummy_folder_path + payslip.file_name)
        except Exception as e:
            self.__log.error(self.__exception.get_exception())






    def __revoke_payslip_process(self, user_id, header_id, reason):
        response = False
        try:
            with transaction.atomic():
                response = FinanaceDA().delete_payslip_details(header_id)

                if response:
                    revertDict = {}
                    revertDict['reverted_date_time'] = datetime.now()
                    revertDict['reverted_by'] = user_id
                    revertDict['reverted_reason'] = reason
                    revertDict['is_reverted'] = 1
                    response = FinanaceDA().update_payslip_header(header_id, revertDict)
        except Exception as err:
            self.__log.error(self.__exception.get_exception())
        return response


    def __get_todo_list(self, header_id):
        resultList = []
        try:
            Logs = FinanaceDA().get_finanace_log_by_header_id(header_id)
            for each_logs in Logs:
                resultList.append(each_logs.log_message)
        except Exception as err:
            self.__log.error(self.__exception.get_exception())
        return resultList


    def extract_zip_file(self, zip_file):
        """
        Download a ZIP file and extract its contents in memory
        yields (filename, file-like object) pairs
        """
        with zipfile.ZipFile(io.BytesIO(zip_file.read())) as thezip:
            for zipinfo in thezip.infolist():
                with thezip.open(zipinfo) as thefile:
                    yield zipinfo.filename, thefile.read()


    def get_employee_ids_by_organization(self, org_id):
        resultList = []
        try:
            active_employees_ids = UserDA().get_all_active_users().values_list('id', flat=True)
            user_profiles = UserDA().get_all_user_profiles()
            user_profiles = user_profiles.filter(company_id=org_id,user_id__in=active_employees_ids )
            resultList = user_profiles

        except Exception as err:
            self.__log.error(self.__exception.get_exception())
        return resultList

    def __send_summary(self, to_email, log_summary=[]):
        try:
            subject = 'Summary of Processed Pay Slips'
            email_dto = new_dto()
            email_dto.heading = subject
            email_dto.summary = log_summary
            email_conetent = self.generate_pay_slip_summary(
                email_dto
            )
            self.send_pay_slip_summary_notification(
                        email_conetent,
                        to_email,
                        subject)
        except Exception as err:
            settings.ERROR_MSG['application_error']\
                .format(err, self.__log.error(self.__exception.get_exception()))
        return None

    def send_pay_slip_summary_notification(self, message, to_email, subject, cc_addresses=[]):
        mail_dto = {}
        mail_dto["subject"] = subject
        mail_dto["from_address"] = settings.EMAIL_ADDRESS['do_not_reply']['name']
        mail_dto["body"] = message
        mail_dto["to_addresses"] = [to_email]
        mail_dto["cc_addresses"] = cc_addresses
        mail_dto["smtp_username"] = settings.EMAIL_ADDRESS['do_not_reply']['mailID']
        mail_dto["smtp_password"] = settings.EMAIL_ADDRESS['do_not_reply']['password']
        send_email_notification.apply_async(
            [mail_dto, 1], queue=settings.CELERY_QUEUE['mail_sender'])

    def generate_pay_slip_summary(self, email_dto):
        email_template = 'pay_slip_generator_summary.html'
        context = {
            "heading": email_dto.heading,
            "summary": email_dto.summary
        }
        html_email = loader.render_to_string(email_template, context)
        return html_email

    def send_pay_slip_published_notification(self, message, to_email, subject, organization, cc_address=[], bcc_address=[]):
        mail_dto = {}
        mail_dto["subject"] = subject
        mail_dto["body"] = message
        mail_dto["to_addresses"] = [to_email]
        mail_dto["bcc_address"] = bcc_address
        if organization==2:
            mail_dto["from_address"] = settings.EMAIL_ADDRESS['account_dm']['name']
            mail_dto["smtp_username"] = settings.EMAIL_ADDRESS['account_dm']['mailID']
            mail_dto["smtp_password"] = settings.EMAIL_ADDRESS['account_dm']['password']
            mail_dto['reply_to_address'] = settings.CONSTANT_EMAIL.get('dm_account_renjith')
        else:
            mail_dto['mail_host'] = 'office365'
            mail_dto["from_address"] = settings.EMAIL_ADDRESS['account_em']['name']
            mail_dto["smtp_username"] = settings.EMAIL_ADDRESS['account_em']['mailID']
            mail_dto["smtp_password"] = settings.EMAIL_ADDRESS['account_em']['password']
            mail_dto['reply_to_address'] = 'renjith@mydomain.com'
        send_email_notification.apply_async(
            [mail_dto, 1], queue=settings.CELERY_QUEUE['mail_sender'])

    def generate_pay_slip_published_notification(self, email_dto):
        email_template = 'pay_slip_published_notification.html'
        context = {
            "heading": email_dto.heading,
            "emp_name": email_dto.emp_name,
            "emp_position": email_dto.emp_position,
            "emp_email": email_dto.emp_email,
            "month_and_year": email_dto.month_and_year,
            "messages": email_dto.messages
        }
        html_email = loader.render_to_string(email_template, context)
        return html_email

    def get_month_number(self, month_name):
        for number, name in settings.MONTHS.items():
            if name.lower() == month_name.lower():
                return number
        return None


    def __generate_payslip_pwd(self, first_name, dob):
        try:
            name = str(first_name).upper()[:4]
            password = name.strip()+dob.strftime("%Y%m%d")
        except :
            password = "12dmdesk21"
        return password

    def __get_payslip_folder(self, org_id, year, month_id):
        org_name = settings.ORGANIZATION[int(org_id)]
        month_name = settings.MONTHS[int(month_id)]
        folder_path = f"{settings.CONFIDENTIAL_DOCS}employee_payslip/{org_name}/{year}/{month_name}/"
        return folder_path

    def __get_payslip_dummy_folder(self, payslip_folder):
        return payslip_folder + "dummy/"


    def download_dummy_payslip(self, request):
        result = {}
        is_permitted = False
        try:
            user_id = request.user.id
            is_permitted = self.__utility.is_permitted(user_id, 'can_validate_payslip')
            if not is_permitted:
                response["error"] = settings.ERROR_MSG.get('access_denied')
                response['status'] = 403
                return response

            filename = request.GET.get('filename')
            emp_code = filename.split('_')[0]
            employee = UserDA().get_user_by_emp_id(emp_code)

            month = filename.split('_')[2]
            year = filename.split('_')[3].split('.')[0]
            employee_profile = UserDA().get_user_profile_by_id(employee.id)
            org_name = settings.ORGANIZATION[employee_profile.company_id]
            folder_path = self.__get_payslip_folder(employee_profile.company_id, year, self.get_month_number(month))
            dummy_path = self.__get_payslip_dummy_folder(folder_path)
            filename = dummy_path + filename
            file_content = FileManager().read_encrypted_file(filename)
            if file_content:
                result = HttpResponse(content_type='application/pdf')
                result['Content-Disposition'] = f'attachment; filename="{filename}"'
                result.write(file_content)
                return result
            else:
                return HttpResponse(status=404)
        except Exception as err:
            result["error"] = settings.ERROR_MSG['application_error']\
                .format(err, self.__log.error(self.__exception.get_exception()))
        return result
