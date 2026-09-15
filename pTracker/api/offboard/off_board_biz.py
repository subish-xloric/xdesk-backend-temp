import uuid
from types import SimpleNamespace
from datetime import datetime, timedelta

from django.conf import settings
from django.contrib.auth.models import User

from pTracker.common.utility import Utility
from pTracker.common.exception_handler import ExceptionHandler
from pTracker.common.logs import Logs
from pTracker.common.file_manager import FileManager

from pTracker.dataaccess.ptracker_access.user_da import UserDA
from pTracker.dataaccess.ptracker_access.off_board_da import OffBoardDA

from pTracker.api.offboard.off_board_notification_biz import OffBoardNotificationBL
from pTracker.api.offboard.off_board_helper import OffBoardHelperBL


from django.db.models import Q
import os

from django.core.files.base import ContentFile
from django.conf import settings

import json
import uuid
import base64

from pTracker.cronjobs.offboarding_final_process import offboard_final_process


def new_dto():
    dto = SimpleNamespace()
    return dto


class OffBoardBL():
    def __init__(self):
        self.__log = Logs()
        self.__exception = ExceptionHandler()
        self.__utility = Utility()

    def create_offboarding_request(self, user_id, data):
        response = {'error': None, 'message': ''}
        email_content_dto = new_dto()
        try:
            is_valid = OffBoardDA().check_eligible(user_id)
            if is_valid:
                response['error'] = 'Resignation request already exist '
                return response
            status_id = settings.OFF_BOARD_REQUEST_STATUS['Pending']
            emp = UserDA().get_user_by_id(user_id)
            if emp:
                subject = data.data.get('subject')
                content = data.data.get('content', None)
                lead = UserDA().get_lead_id_by_user(user_id)
                lead_obj = UserDA().get_user_by_id(lead)
                organization_id = UserDA().get_user_organization(user_id)
                relieving_date = Utility().get_next_n_working_days(settings.DEAFULT_NOTICE_PERIOD_LENGHT)[-1]
                data = {'user_id': user_id,
                        'emp_code': emp.username,
                        'subject': subject,
                        'content': content,
                        'status': status_id,
                        'relieving_date': relieving_date,
                        'approver_id': lead,
                        'comment': '',
                        'organization_id': organization_id,
                        'deleted': 0,
                        'off_boarding_type': 1 #for resigned
                        }

                result = OffBoardDA().create_offboard_request(data)
                if result:
                    emp_name = emp.first_name + ' ' + emp.last_name
                    action = settings.OFF_BOARD_ACTION_LOG[status_id].\
                        format(emp_name, datetime.now().strftime("%d/%m/%Y %I:%M %p"))
                    log_data = {
                        'off_boarding_id': result.id,
                        'action': action,
                        'emp_id': user_id
                    }
                    OffBoardDA().create_offboard_request_log(log_data)
                    response['message'] = action
                    email_content_dto.heading = emp_name + " - Resignation Request"
                    email_content_dto.lead_name = lead_obj.first_name + ' ' + lead_obj.last_name  # TODO
                    email_content_dto.request = action
                    email_content_dto.emp_name = emp_name
                    email_content_dto.reason = content  # html.escape(content)
                    email_content_dto.subject = subject
                    to_email = lead_obj.email
                    #cc_addresses = settings.OFF_BOARDING_CC_MAILS
                    if organization_id == 3:
                        cc_addresses = [settings.EM_HR_MAIL]
                    else:
                        cc_addresses = [settings.DM_HR_MAIL]

                    # TODO remove comment
                    #cc_addresses.append(lead_obj.email)
                    cc_addresses.append(settings.OPERATIONS_DEPT['email'])
                    email_msg = OffBoardNotificationBL().generate_off_board_email_message(email_content_dto)
                    OffBoardNotificationBL().send_off_board_request_create_notification(
                        email_msg, emp_name, to_email, subject, cc_addresses)

        except Exception as err:
            response["error"] = settings.ERROR_MSG['application_error']\
                .format(err, self.__log.error(self.__exception.get_exception()))
        return response

    def update_offboarding_request(self, user_id, data):
        response = {'error': None, 'message': ''}
        result = None
        try:
            email_content_dto = new_dto()
            role_id, role_name = UserDA().get_user_role_by_id(user_id)
            if role_id not in (2, '2'):
                response['error'] = settings.ERROR_MSG['access_denied']
                return response

            comment = data.get('comment', None)
            status = data.get('status', None)
            releiving_date = data.get('releiving_date')
            if releiving_date != None:
                obj_releiving_date = datetime.strptime(releiving_date, "%Y-%m-%d")
            else:
                obj_releiving_date = '-'
            offboard_request_id = data.get('offboard_request_id')
            offboard_request = OffBoardDA().get_offboarding_request_by_id(offboard_request_id)
            requested_emp = UserDA().get_user_by_id(offboard_request.user_id)
            emp_profile = UserDA().get_user_profile_by_id(offboard_request.user_id)
            job_title = UserDA().get_job_title_by_id(emp_profile.job_title)
            request_emp_name = requested_emp.first_name + ' ' + requested_emp.last_name

            emp = UserDA().get_user_by_id(user_id)
            lead = UserDA().get_lead_id_by_user(user_id)
            lead_obj = UserDA().get_user_by_id(lead)
            if status:
                off_data = {}
                off_data['status'] = status
                if status != 3:  # cancelled
                    off_data['relieving_date'] = obj_releiving_date
                off_data['approver_id'] = user_id
                off_data['comment'] = comment
                # 'relieving_date' : releiving_date
                result = OffBoardDA().update_offboard_request(offboard_request_id, off_data)  # TODO
                if result:
                    emp_name = emp.first_name + ' ' + emp.last_name
                    action = settings.OFF_BOARD_ACTION_LOG[status]\
                        .format(emp_name, datetime.now().strftime("%d/%m/%Y %I:%M %p"))
                    log_data = {
                        'off_boarding_id': offboard_request_id,
                        'action': action,
                        'emp_id': user_id
                    }
                    OffBoardDA().create_offboard_request_log(log_data)
                    response['message'] = action
                    if status in (2, 4, 3):
                        if status == 2:
                            status_name = 'Accepted'
                        elif status == 4:
                            status_name = 'Rejected'
                        else:
                            status_name = 'Cancelled'
                        email_content_dto.heading = request_emp_name + " - Resignation Request {0}".format(status_name)
                        email_subject = email_content_dto.heading
                        email_content_dto.lead_name = request_emp_name
                        email_content_dto.request = action
                        email_content_dto.emp_name = emp_name
                        if status == 3:
                            email_content_dto.relieving_date = '-'
                        else:
                            email_content_dto.relieving_date = obj_releiving_date.strftime("%d-%m-%Y")
                        email_content_dto.action = status_name
                        email_content_dto.comment = comment
                        to_email = requested_emp.email
                        cc_addresses = settings.OFF_BOARDING_CC_MAILS
                        cc_addresses.append(lead_obj.email)

                        email_content_dto.HR_name = emp_name #settings.HR_NAME
                        email_content_dto.employee_name = request_emp_name
                        email_content_dto.organization = settings.ORGANIZATION[emp_profile.company_id]
                        email_content_dto.job_title = job_title.job_title

                    if status == 2:
                        email_msg = OffBoardNotificationBL()\
                            .generate_off_board_accept_email_message(email_content_dto)
                    else:
                        email_msg = OffBoardNotificationBL().\
                            generate_off_board_update_email_message(email_content_dto)
                    OffBoardNotificationBL().send_off_board_request_notification(
                        email_msg, request_emp_name, to_email, email_subject, cc_addresses)

        except Exception as err:
            response["error"] = settings.ERROR_MSG['application_error']\
                .format(err, self.__log.error(self.__exception.get_exception()))
        return response

    def get_all_offboarding_requests(self, user_id, year, organization, from_date, to_date):
        response = {'error': None, 'off_baord_list': []}
        try:

            user_dic = {}
            emp_code_dic ={}
            role_id, role_name = UserDA().get_user_role_by_id(user_id)
            if role_id not in (2, '2'):
                response['error'] = settings.ERROR_MSG['access_denied']
                return response

            result = OffBoardDA().get_filtered_offboarding_requests(organization,year,from_date,to_date)

            if result:
                user_obj = UserDA().get_all_users()
                for user in user_obj:
                    user_dic[user.id] = user.first_name + " " + user.last_name
                    emp_code_dic[user.id] = user.username

                exit_interview_forms_dict = self.get_exit_interview_form_code_dict()
                exit_form_dict = self.get_offboarding_exit_form_code_dict()
                all_log = OffBoardDA().get_all_logs()

                for each in result:
                    temp = {}
                    temp_log_list = []
                    log_list = self.get_log_list(each.id,all_log)


                    # for log in log_list:
                    #     temp_log_list.append(log.action)
                    # log_list = self.get_log_list(each.id)
                    balance_working_days = Utility().get_date_range(datetime.now().date(), each.relieving_date)
                    temp['request_id'] = each.id
                    temp['date_applied'] = each.request_date.strftime('%Y-%m-%d')
                    temp['emp_name'] = user_dic.get(each.user_id)
                    temp['emp_code'] = emp_code_dic.get(each.user_id)
                    temp['subject'] = each.subject
                    temp['content'] = each.content
                    temp['status'] = each.status
                    temp['offboarding_type'] = settings.OFFBOARDING_TYPE.get(each.off_boarding_type, None)
                    if each.status in [3, 4]:
                        temp['days_left_to_relieve'] = 0
                    else:
                        temp['days_left_to_relieve'] = len(
                            balance_working_days)
                    temp['releiving_date'] = each.relieving_date
                    temp['approver'] = user_dic.get(each.approver_id, 0)
                    temp['comment'] = each.comment
                    temp['log_list'] = log_list
                    user = user_obj.get(id=each.user_id)
                    temp['date_of_join'] = user.date_joined
                    if each.status in [4, 5, 6]:
                        temp['exit_form_code'] = exit_form_dict.get(each.id, None)
                        temp['exit_interview_form_code'] = exit_interview_forms_dict.get(each.id, None)
                    else:
                        temp['exit_form_code'] = ''
                        temp['exit_interview_form_code'] = ''
                    today = datetime.now()
                    temp['years_of_service'] = datetime.now(
                    ).month - user.date_joined.month + 12*(datetime.now().year - user.date_joined.year)
                    response['off_baord_list'].append(temp)
                    del temp
                    del temp_log_list

        except Exception as err:
            response["error"] = settings.ERROR_MSG['application_error']\
                .format(err, self.__log.error(self.__exception.get_exception()))
        return response

    def date_after_n_working_days_from_custom_date(self, from_date, no_of_days):
        response = {
            "error": "",
            "date": None
        }
        try:
            request_date = datetime.strptime(from_date, '%Y-%m-%d')
            day = Utility().date_after_n_working_days(int(no_of_days), request_date)
            response['date'] = day[-1]
        except Exception as err:
            response["error"] = settings.ERROR_MSG['application_error']\
                .format(err, self.__log.error(self.__exception.get_exception()))
        return response

    def initiate_offboarding(self, user_id, request):
        result = {'error': "",
                  "message": ""
                  }
        email_content_dto = new_dto()
        try:
            role_id, role_name = UserDA().get_user_role_by_id(user_id)
            if role_id not in (2, '2'):
                result['error'] = settings.ERROR_MSG['access_denied']
                return result

            request_id = request.data.get("request_id", 0)
            off_boarding_request = OffBoardDA().get_offboarding_request_by_id(request_id)
            if not off_boarding_request:
                result['error'] = "Invalid request id."
                return result


            employee = UserDA().get_user_by_id(off_boarding_request.user_id)
            lead_id = UserDA().get_lead_id_by_user(off_boarding_request.user_id)
            lead = UserDA().get_user_by_id(lead_id)
            employee_org_id = UserDA().get_user_organization(employee.id)
            exit_form_template = OffBoardHelperBL().get_exit_form_template()
            exit_form = OffBoardHelperBL().off_boarding_exit_form()
            exit_employee_template = OffBoardHelperBL().get_exit_employee_template()

            reporting_manager = {
                "dept_id": '3',
                "name": 'Repoting Manager',
                "emp_name": lead.first_name + ' ' + lead.last_name,
                "res_emp_id": str(lead.id),
                "email": lead.email,
                "signature": 0,
                "checklist": [{"id": '1', "name": "Completed All Tasks & Tickets", "value": 0}],
                "signed": 0,
                "signed_date": "",
                "sign": ''
            }

            exit_employee_template['name'] = employee.first_name + ' ' + employee.last_name
            exit_employee_template['employee_id'] = employee.id
            exit_employee_template['employee_code'] = employee.username
            exit_employee_template['organization_id'] = off_boarding_request.organization_id

            exit_employee_template['off_board_request_date'] = datetime.strftime(
                off_boarding_request.request_date, "%Y-%m-%d")
            exit_employee_template['relieving_date'] = datetime.strftime(
                off_boarding_request.relieving_date, "%Y-%m-%d")
            exit_employee_template['off_boarding_id'] = off_boarding_request.id
            exit_form_template['employee'] = exit_employee_template
            temp_dept = []
            temp_dept.append(settings.ADMIN_DEPT)
            temp_dept.append(settings.OPERATIONS_DEPT)
            temp_dept.append(reporting_manager)
            temp_dept.append(settings.QA_DEPT)
            temp_dept.append(settings.SAG_DEPT)
            temp_dept.append(settings.ACCOUNTS_DEPT)
            temp_dept.append(settings.HR_DEPT)
            exit_form_template['department'] = temp_dept

            exit_form['off_boarding_id'] = off_boarding_request.id
            exit_form['emp_id'] = employee.id
            exit_form['exit_form_data'] = json.dumps(exit_form_template)
            exit_form['off_boarding_code'] = str(uuid.uuid4())

            exit_form['organization_id'] = employee_org_id
            exit_form['request_date'] = off_boarding_request.request_date
            exit_form['releiving_date'] = off_boarding_request.relieving_date

            user = UserDA().get_user_by_id(user_id)

            exit_form_obj = OffBoardDA().create_off_board_exit_form_data(exit_form)
            exit_interview_form = self.create_exit_interview_form(
                off_boarding_request, employee, user)

            temp = {}
            temp['status'] = settings.OFF_BOARD_REQUEST_STATUS['Initiated']
            OffBoardDA().update_offboard_request(off_boarding_request.id, temp)

            employee_name = employee.first_name + ' ' + employee.last_name
            email_subject = employee_name + " - Offboarding Checklist"
            email_content_dto.heading = employee_name + " - Offboarding Checklist"
            email_content_dto.emp_name = employee_name
            email_content_dto.date = datetime.now().strftime("%d/%m/%Y")
            email_content_dto.link = f"{settings.BASE_URL}offboarding/exit-form/{exit_form['off_boarding_code']}"
            email_content_dto.hr_name = user.first_name + ' ' + user.last_name
            cc_addresses = []
            cc_addresses.append(settings.ADMIN_DEPT['email'])
            cc_addresses.append(settings.OPERATIONS_DEPT['email'])
            cc_addresses.append(settings.SAG_DEPT['email'])
            cc_addresses.append(settings.QA_DEPT['email'])
            cc_addresses.append(settings.ACCOUNTS_DEPT['email'])
            cc_addresses.append(settings.HR_DEPT['email'])
            cc_addresses.append(lead.email)
            to_email = employee.email
            email_msg = OffBoardNotificationBL().generate_exit_form_initaiated_email_message(email_content_dto)
            OffBoardNotificationBL().\
                send_off_board_request_notification(email_msg, employee.first_name + ' ' + employee.last_name, to_email, email_subject, cc_addresses)

            action = settings.OFF_BOARD_FORM_ACTION_LOG[1].format(user.first_name + ' ' + user.last_name,
                                                                  datetime.now().strftime("%d/%m/%Y %I:%M %p"))
            log_data = {
                'off_boarding_id': off_boarding_request.id,
                'action': action, 'emp_id': user_id
            }
            OffBoardDA().create_offboard_request_log(log_data)
            result['message'] = action

        except Exception as err:
            result["error"] = settings.ERROR_MSG['application_error']\
                .format(err, self.__log.error(self.__exception.get_exception()))
        return result

    def get_off_boarding_exit_form(self, user_id, exit_form_id):
        result = {'error': '',
                  'data': None,
                  'permission': None}
        try:
            exit_form = OffBoardDA().get_off_boarding_exit_form_by_exit_form_id(exit_form_id)

            if exit_form:
                exit_form = json.loads(exit_form.exit_form_data)
                permission = self.is_perimitted_to_view_exit_form(
                    user_id, exit_form)
                if exit_form['employee']['employee_id'] == user_id:
                    permission = True
                if permission:
                    result['permission'] = True
                    result['data'] = exit_form
                    return result
                else:
                    result['permission'] = False
                    return result
        except Exception as err:
            result["error"] = settings.ERROR_MSG['application_error']\
                .format(err, self.__log.error(self.__exception.get_exception()))
        return result

    def is_perimitted_to_view_exit_form(self, user_id, exit_form):
        responsible_ids = []
        for each in exit_form['department']:
            responsible_ids.append(each['res_emp_id'])
        if str(user_id) in responsible_ids:
            return True
        return False

    def update_exit_form(self, user_id, request):
        result = {"error": '',
                  "message": ''
                  }
        try:
            permission = self.is_perimitted_to_view_exit_form(
                user_id, request.data['exit_form'])
            if permission:
                exit_form_code = request.data['off_boarding_code']
                exit_form_data = json.dumps(request.data['exit_form'])
                off_boarding_request = OffBoardDA().update_offboard_exit_form(
                    exit_form_code, exit_form_data)
                employee_id = off_boarding_request.emp_id

                user = UserDA().get_user_by_id(user_id)
                role_id, role_name = UserDA().get_user_role_by_id(user_id)
                if role_id == 2:
                # if str(user_id) == settings.HR_EMP_ID:
                    self.offboarding_end_process(employee_id, off_boarding_request.id)
                    #update_data = {"status": settings.OFF_BOARD_REQUEST_STATUS['Completed']}
                    #OffBoardDA().update_offboard_request(off_boarding_request.id, update_data)

                action = settings.OFF_BOARD_FORM_ACTION_LOG[2].format(user.first_name + ' ' + user.last_name,
                                                                      datetime.now().strftime("%d/%m/%Y %I:%M %p"))
                log_data = {'off_boarding_id': off_boarding_request.id,
                            'action': action, 'emp_id': user_id}
                OffBoardDA().create_offboard_request_log(log_data)
                result['message'] = "Exit Form Updated Succesfully"
            else:
                result['error'] = settings.ERROR_MSG['access_denied']
        except Exception as err:
            result["error"] = settings.ERROR_MSG['application_error']\
                .format(err, self.__log.error(self.__exception.get_exception()))
        return result

    def upload_relieving_documents(self, user_id, request):
        result = {"error": '',
                  "message": ''
                  }
        try:
            role_id, role_name = UserDA().get_user_role_by_id(user_id)
            if role_id not in (2, '2'):
                result['error'] = settings.ERROR_MSG['access_denied']
                return result
            doc_type = request.data['doc_type']
            off_boarding_id = request.data['off_boarding_id']
            is_uploaded = OffBoardDA().is_document_already_uploaded(
                settings.OFFBOARDING_DOC_TYPES[int(doc_type)], off_boarding_id)
            if is_uploaded:
                result['error'] = f"{settings.OFFBOARDING_DOC_TYPES[int(doc_type)]} Alredy Uploaded"
                return result
            doc = request.FILES['image']

            is_valid = self.is_relieving_docs_valid(doc)
            if not is_valid:
                result["error"] = "Invalid document"
                return result
            name = self.upload_relieving_docs(doc)
            off_boarding_request = OffBoardDA().get_offboarding_request_by_id(off_boarding_id)

            create_data = {
                "off_boarding_id": off_boarding_id,
                "emp_id": off_boarding_request.user_id,
                "document_name": settings.OFFBOARDING_DOC_TYPES[int(doc_type)],
                "document": name,  # doc.name,

            }

            OffBoardDA().upload_relieving_documents(create_data)

            result['message'] = "Documents Uploaded Successfully"

        except Exception as err:
            result["error"] = settings.ERROR_MSG['application_error']\
                .format(err, self.__log.error(self.__exception.get_exception()))
        return result

    def get_relieving_documents_by_off_boarding_id(self, user_id, off_boarding_id):
        result = {"error": '',
                  "data": [],
                  }
        doc_list = []
        try:
            role_id, role_name = UserDA().get_user_role_by_id(user_id)
            if role_id not in (2, '2'):
                result['error'] = settings.ERROR_MSG['access_denied']
                return result
            documents = OffBoardDA().get_relieving_docs_by_off_boarding_id(off_boarding_id)
            if documents:
                for each in documents:
                    temp = {}
                    temp['doc_id'] = each.id
                    temp['doc_name'] = each.document_name
                    temp['document'] = each.document
                    temp['created_date'] = each.created_date
                    temp['file'] = ''
                    file_path = os.path.join(settings.CONFIDENTIAL_DOCS, f'offboarding_documents/{each.document}')
                    file_content = FileManager().read_file(file_path)
                    if file_content:
                        encoded_string = base64.b64encode(file_content)
                        temp['file'] = encoded_string
                    else:
                        temp['file'] = ''
                    doc_list.append(temp)
                result['data'] = doc_list
        except Exception as err:
            result["error"] = settings.ERROR_MSG['application_error']\
                .format(err, self.__log.error(self.__exception.get_exception()))
        return result

    def delete_relieving_document(self, user_id, document_id):
        result = {
            "error": '',
            "message": ''
        }
        try:
            role_id, role_name = UserDA().get_user_role_by_id(user_id)
            if role_id not in (2, '2'):
                result['error'] = settings.ERROR_MSG['access_denied']
                return result
            OffBoardDA().delete_relieving_document(document_id)
            result['message'] = 'Document Deleted Successfully'
        except Exception as err:
            result["error"] = settings.ERROR_MSG['application_error']\
                .format(err, self.__log.error(self.__exception.get_exception()))
        return result

    def get_user_details_for_offboard_request(self, user_id):
        result = {'error': '',
                  'data': []
                  }
        temp_list = []
        obj_user_da = UserDA()
        try:
            user = obj_user_da.get_user_by_id(user_id)
            user_profile = obj_user_da.get_user_profile_by_id(user_id)

            if user_profile:
                lead_id = obj_user_da.get_lead_id_by_user(user_id)
                lead_name = settings.HR_NAME
                if lead_id:
                    lead = obj_user_da.get_user_by_id(lead_id)
                    lead_name = lead.first_name + ' ' + lead.last_name
                job_title = obj_user_da.get_job_title_by_id(user_profile.job_title)
                temp = {}
                temp['name'] = user.first_name + ' ' + user.last_name
                temp['email'] = user_profile.personal_email
                temp['HR_name'] = lead_name
                temp['job_title'] = job_title.job_title
                today = datetime.today()

                months_of_service = datetime.now().month -\
                    user.date_joined.month + 12 * \
                    (datetime.now().year - user.date_joined.year)
                years, months = divmod(months_of_service, 12)
                temp['experience'] = f"{years} Year and {months} Months"
                temp_list.append(temp)
            result['data'] = temp_list
        except Exception as err:
            result["error"] = settings.ERROR_MSG['application_error']\
                .format(err, self.__log.error(self.__exception.get_exception()))
        return result

    def upload_relieving_docs(self, doc):
        name = str(uuid.uuid4())+doc.name
        file_path = os.path.join(settings.CONFIDENTIAL_DOCS, f"offboarding_documents/{name}")
        FileManager().upload_file(file_path, doc.read())
        return name

    def create_exit_interview_form(self, off_boarding_request, employee, approver):
        self.__log.debug(os.getcwd())
        # print(os.path.dirname(os.path.abspath(__file__)))
        # print('pTracker/'+settings.JSON_TEMPLATE_PATH + 'exit_interview_form.json')
        #f = open('pTracker/'+settings.JSON_TEMPLATE_PATH + 'exit_interview_form.json')
        # f = open(settings.JSON_TEMPLATE_PATH + 'exit_interview_form.json')
        #TODO remove hardcode value
        f = open("/var/www/dm_ptracker/backend_app/pTracker/pTracker/json_templates/" + 'exit_interview_form.json')
        data = json.load(f)
        emp_name = employee.first_name + ' ' + employee.last_name
        user_profile = UserDA().get_user_profile_by_id(employee.id)
        job_title = UserDA().get_job_title_by_id(user_profile.job_title)
        if user_profile.company_id == 2:
            data['paragraph'] = settings.EXIT_INTERVIEW_NOTE.format(
                "Digital Mesh Softech India Pvt. Ltd")
        if user_profile.company_id == 3:
            data['paragraph'] = settings.EXIT_INTERVIEW_NOTE.format(
                "EM Softech LLP")
        data['contents']['employee']['employee_name']['value'] = emp_name
        data['contents']['employee']['employee_id']['value'] = employee.id
        data['contents']['employee']['designation']['value'] = job_title.job_title
        data['contents']['employee']['date_joined']['value'] = datetime.strftime(
            employee.date_joined, '%d/%m/%Y')
        data['contents']['employee']['last_day_of_work']['value'] = datetime.strftime(
            off_boarding_request.relieving_date, '%d/%m/%Y')
        data['contents']['employee']['date_resigned']['value'] = datetime.strftime(
            off_boarding_request.request_date, '%d/%m/%Y')
        data['contents']['hr_signature']['emp_id'] = settings.HR_EMP_ID
        data['contents']['ceo_signature']['emp_id'] = settings.CEO_EMP_ID
        data['contents']['cto_signature']['emp_id'] = settings.CTO_EMP_ID
        data['contents']['employee']['interviewed_by']['value'] = settings.HR_NAME
        data['contents']['employee']['date_interviewed']['value'] = datetime.strftime(datetime.now().date(),'%d/%m/%Y')

        exit_interview_data = {}
        exit_interview_data['off_boarding_id'] = off_boarding_request.id
        exit_interview_data['emp_id'] = employee.id
        exit_interview_data['exit_interview_code'] = str(uuid.uuid4())
        exit_interview_data['exit_interview_form_data'] = json.dumps(data)
        # created
        exit_interview_data['status'] = settings.OFF_BOARD_INTERVIEW_FORM_STATUS['created']
        exit_interview_data['organization_id'] = user_profile.company_id
        exit_interview_data['request_date'] = off_boarding_request.request_date
        exit_interview_data['releiving_date'] = off_boarding_request.relieving_date
        exit_interview_form = OffBoardDA().create_exit_interview_form(exit_interview_data)

        employee_name = employee.first_name + ' ' + employee.last_name
        email_subject = employee_name + " - Exit Interview"
        email_content_dto = new_dto()
        email_content_dto.heading = employee_name + " - Exit Interview"
        email_content_dto.emp_name = employee_name
        email_content_dto.date = datetime.now().strftime("%d/%m/%Y")
        email_content_dto.link = f"{settings.BASE_URL}offboarding/exit-interview-form/{exit_interview_data['exit_interview_code']}"
        email_content_dto.hr_name = approver.first_name + ' ' + approver.last_name
        to_email = employee.email
        cc_addresses = [approver.email]
        email_msg = OffBoardNotificationBL()\
            .generate_exit_interview_email_message(email_content_dto)
        OffBoardNotificationBL()\
            .send_off_board_request_notification(email_msg, employee_name, to_email, email_subject, cc_addresses)

        action = settings.OFF_BOARD_INTERVIEW_FORM_ACTION_LOG[1].format(approver.first_name + ' ' + approver.last_name,
                                                                        datetime.now().strftime("%d/%m/%Y %I:%M %p"))
        log_data = {'off_boarding_id': off_boarding_request.id,
                    'action': action, 'emp_id': approver.id}
        OffBoardDA().create_offboard_request_log(log_data)

        return exit_interview_form

    def get_exit_interview_form_by_code(self, user_id, exit_intrvw_code):
        result = {
            "error": "",
            "data": "",
            "permission": ""
        }
        try:
            exit_interview_form = OffBoardDA(
            ).get_exit_interviewform_by_exit_interview_code(exit_intrvw_code)
            if exit_interview_form:
                if exit_interview_form.emp_id != user_id:
                    role_id, role_name = UserDA().get_user_role_by_id(user_id)
                    if role_id not in (1, '1', 2, '2'):
                        result['error'] = settings.ERROR_MSG['access_denied']
                        result['permission'] = False
                        return result
                result['data'] = json.loads(
                    exit_interview_form.exit_interview_form_data)
                result['organization'] = exit_interview_form.organization_id
                result['permission'] = True
        except Exception as err:
            result["error"] = settings.ERROR_MSG['application_error']\
                .format(err, self.__log.error(self.__exception.get_exception()))
        return result

    def update_exit_interview_form(self, user_id, request):
        result = {
            "error": "",
            "message": ""
        }
        try:
            exit_code = request.get('exit_code')
            exit_interview_data = request.get('exit_interview_data')

            exit_interview_form = OffBoardDA(
            ).get_exit_interviewform_by_exit_interview_code(exit_code)
            if exit_interview_form:
                if exit_interview_form.emp_id != user_id:
                    role_id, role_name = UserDA().get_user_role_by_id(user_id)
                    if role_id not in (1, '1', 2, '2'):
                        result['error'] = settings.ERROR_MSG['access_denied']
                        return result
                update_data = {}
                update_data['exit_interview_form_data'] = json.dumps(
                    exit_interview_data)
                OffBoardDA().update_exit_interview_form_data(
                    update_data, exit_interview_form.id)

                user = UserDA().get_user_by_id(user_id)
                action = settings.OFF_BOARD_INTERVIEW_FORM_ACTION_LOG[2].format(user.first_name + ' ' + user.last_name,
                                                                                datetime.now().strftime("%d/%m/%Y %I:%M %p"))
                log_data = {'off_boarding_id': exit_interview_form.off_boarding_id,
                            'action': action, 'emp_id': user.id}
                OffBoardDA().create_offboard_request_log(log_data)
                result['message'] = 'Updated Succefully'
            else:
                result['error'] = "Invalid Request"

        except Exception as err:
            result["error"] = settings.ERROR_MSG['application_error']\
                .format(err, self.__log.error(self.__exception.get_exception()))
        return result

    def offboarding_end_process(self, user_id, off_boarding_id):
        offboard_final_process.apply_async([user_id, off_boarding_id], queue=settings.CELERY_QUEUE['offboarding'])

    def offboarding_end_process_for_inactive_employees(self):
        result = {
            "error":''
        }
        try:
            all_inactive_employees = UserDA().get_all_inactive_users()
            for user in all_inactive_employees:
                self.offboarding_end_process(user.id, 0)
        except Exception as err:
            result["error"] = settings.ERROR_MSG['application_error']\
                .format(err, self.__log.error(self.__exception.get_exception()))
        return result

    def is_relieving_docs_valid(self, file):
        is_valid = True

        allowed_image_types = ["application/pdf"]
        if file.content_type not in allowed_image_types:
            is_valid = False

        if file.size > 2000000 :
            is_valid = False

        return is_valid

    def get_offboarding_exit_form_code_dict(self):
        exit_form_dict = {}
        exit_forms = OffBoardDA().get_all_exit_forms()
        for exit_form in exit_forms:
            exit_form_dict[exit_form.off_boarding_id] = exit_form.off_boarding_code
        return exit_form_dict

    def get_exit_interview_form_code_dict(self):
        exit_interview_form_code_dict = {}
        exit_interview_forms = OffBoardDA().get_all_exit_interview_forms()
        for exit_interview_form in exit_interview_forms:
            exit_interview_form_code_dict[exit_interview_form.off_boarding_id] = exit_interview_form.exit_interview_code
        return exit_interview_form_code_dict

    def get_log_list(self, offboarding_id, all_log_obj):
        log_list = []
        for each_log in all_log_obj:
            if int(each_log.off_boarding_id) == int(offboarding_id):
                log_list.append(each_log.action)
        return log_list



    def terminate_employee(self, user_id, data, user):
        result = {
            "error":'',
            'msg':''
        }
        company_name = ''
        notify_list = []
        subject = ''
        try:
            role_id, role_name = UserDA().get_user_role_by_id(user_id)
            if role_id not in (1, '1', 2, '2'):
                result['error'] = settings.ERROR_MSG['access_denied']
                result['permission'] = False
                return result
            emp_id = data.get('emp_id', 0)
            employee = UserDA().get_user_by_id(emp_id)
            notify = data.get('notify', 0)
            if len(notify)>0:
                for each in notify:
                    notify_list.append(each.get('id'))
            disable_now = data.get('disable_now', False)
            offboarding_type = data.get('action', None)
            organization = UserDA().get_user_organization(emp_id)
            company_name = settings.ORGANIZATION[organization]

            username = user.first_name + ' ' + user.last_name

            if offboarding_type:
                if int(offboarding_type) == 2:
                    subject = 'Notice Of Relieving'
                    action = settings.TERMINATION_ACTION_LOG[2].format(username,
                datetime.now().strftime("%d/%m/%Y %I:%M %p"))
                else:
                    subject = 'Notice Of Termination'
                    action = settings.TERMINATION_ACTION_LOG[1].format(username,
                datetime.now().strftime("%d/%m/%Y %I:%M %p"))
            dto = {}

            dto['user_id'] = emp_id
            dto['emp_code'] = employee.username
            dto['organization_id'] = organization
            dto['content'] = data.get('reason', 0)
            dto['comment'] = data.get('comments', 0)
            dto['relieving_date'] = data.get('effect_date', 0)
            dto['is_terminated'] = 1
            dto['approver_id'] = user_id
            dto['status'] = settings.OFF_BOARD_REQUEST_STATUS['Initiated']
            dto['subject'] = subject
            dto['off_boarding_type'] = offboarding_type
            obj = OffBoardDA().create_offboard_request(dto)

            log_data = {
                        'off_boarding_id': obj.id,
                        'action': action,
                        'emp_id': user_id
                    }
            OffBoardDA().create_offboard_request_log(log_data)
            if disable_now:
                auth_user_update_data = {
                    "is_active": 0
                }
                UserDA().update_auth_user(auth_user_update_data, emp_id)
            email_content_dto = new_dto()
            email_content_dto.subject = subject
            email_content_dto.emp_name = employee.first_name + ' ' + employee.last_name
            email_content_dto.date = datetime.strptime(obj.relieving_date, '%Y-%m-%d').strftime('%d/%m/%Y')
            email_content_dto.company_name = company_name
            email_content_dto.reason = obj.content
            to_email = employee.email
            cc_addresses = UserDA().get_email_by_id_list(notify_list)
            cc_addresses = list(cc_addresses)
            if not obj:
                result['error'] = 'Something went wrong while terminating employee.'
                result['permission'] = False
                return result
            else:
                if int(offboarding_type) == 2:
                    email_msg = OffBoardNotificationBL()\
                        .generate_relieving_message(email_content_dto)
                    result['msg'] = "Employee Relieving process initiated succesfully."
                else:
                    email_msg = OffBoardNotificationBL()\
                        .generate_termination_message(email_content_dto)
                    result['msg'] = "Employee Termination Process initiated Succesfully."
                OffBoardNotificationBL()\
                    .send_off_board_request_notification(email_msg, 'employee_name', to_email, subject, cc_addresses)
        except Exception as err:
            result["error"] = settings.ERROR_MSG['application_error']\
                .format(err, self.__log.error(self.__exception.get_exception()))
        return result
    def check_termination_process(self, emp_id):
        result = {
            "error":''
        }
        try:
            status = [settings.OFF_BOARD_REQUEST_STATUS['Pending'], \
                    settings.OFF_BOARD_REQUEST_STATUS['Accepted'], \
                    settings.OFF_BOARD_REQUEST_STATUS['Initiated'],
                    settings.OFF_BOARD_REQUEST_STATUS['Completed'] ]
            obj = OffBoardDA().validate_termination_process(emp_id, status, 1)
            if obj:
                result['error'] = 'Termination Process Already in Progress'
                return result
        except Exception as err:
            result["error"] = settings.ERROR_MSG['application_error']\
                .format(err, self.__log.error(self.__exception.get_exception()))
        return result

    def update_pftransfer_grativity_dates(self, user_id, data):
        result = {"error": ''}
        try:
            pass
        except Exception as err:
            result["error"] = settings.ERROR_MSG['application_error']\
                .format(err, self.__log.error(self.__exception.get_exception()))
        return result

    def archive_inactive_employees(self):
        result = {
            "error":''
        }
        try:
            all_inactive_employees = UserDA().get_all_inactive_users()
            for user in all_inactive_employees:
                self.offboarding_end_process(user.id)

        except Exception as err:
            result["error"] = settings.ERROR_MSG['application_error']\
                .format(err, self.__log.error(self.__exception.get_exception()))
        return result

