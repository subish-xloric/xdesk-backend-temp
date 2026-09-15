import json
from types import SimpleNamespace
from datetime import datetime
import uuid
import os
import base64
from cryptography.fernet import Fernet

from io import BytesIO

from django.conf import settings
from django.core.files.storage import default_storage
from django.core.files.base import ContentFile
from django.db import transaction


from django.template.loader import get_template
import pyotp

from pTracker.notification_center.email_engine import Email
from pTracker.common.utility import Utility
from pTracker.common.exception_handler import ExceptionHandler
from pTracker.common.logs import Logs
from pTracker.common.file_manager import FileManager
from pTracker.dataaccess.ptracker_access.user_da import UserDA
from pTracker.dataaccess.ptracker_access.onboarding_da import OnboardingDA
from pTracker.api.onboarding.onboarding_notification import OnBoardingNotificationBL
from pTracker.dataaccess.ptracker_access.project_da import ProjectDA
from pTracker.dataaccess.ptracker_access.leave_da import LeaveDA


def new_dto():
    dto = SimpleNamespace()
    return dto


class OnboardingBL():

    def __init__(self):
        self.__log = Logs()
        self.__exception = ExceptionHandler()
        self.__utility = Utility()
        self.__fernet = Fernet(settings.FERNET_KEY)

    def is_phone_and_email_unique(self, phone, email):
        is_exist = False
        candidate_obj = OnboardingDA().get_onboarding_candidate_by_email_or_phone(email, phone)
        if candidate_obj:
            is_exist = True
        return is_exist

    def upload_pre_employment_docs(self, doc, name):
        file_path = f"{settings.CONFIDENTIAL_DOCS}pre_employmet_docs/{name}"
        FileManager().upload_file(file_path, doc.read())
        return name

    def __get_offer_letter_url(self, file_name):
        encoded_string = ''
        if file_name:
                try:
                    file_path = os.path.join(settings.CONFIDENTIAL_DOCS, f'pre_employmet_docs/{file_name}')
                    file_content = FileManager().read_file(file_path)
                    if file_content:
                        encoded_string = base64.b64encode(file_content)
                except Exception as e:
                    pass
        return encoded_string

    def onboarding_dates_validation(self, offer_released_date, offer_accepted_date, expected_joining_date):
        message = ''
        is_valid = True
        offer_released_date = datetime.strptime(offer_released_date,"%Y-%m-%d")
        offer_accepted_date = datetime.strptime(offer_accepted_date,"%Y-%m-%d")
        expected_joining_date = datetime.strptime(expected_joining_date,"%Y-%m-%d")

        if (offer_released_date > offer_accepted_date):
            message = "Offer released date should be less than offer accepted date"
            is_valid = False
            return message, is_valid

        if (offer_accepted_date > expected_joining_date):
            message = "Offer Accepted date should be less than expected joining date"
            is_valid = False
            return message, is_valid
        return message, is_valid



    def create_onboarding_candidate(self, user_id, candidate_data):
        result = {"error": '', }
        try:
            is_alredy_exist = False
            candidate_data_dict = {}
            role_id, role_name = UserDA().get_user_role_by_id(user_id)
            if role_id not in [2] :
                result['error'] = settings.ERROR_MSG['access_denied']
                result['status'] = 403
                return result

            user_profile = UserDA().get_user_profile_by_id(user_id)
            job_title = UserDA().get_job_title_by_id(user_profile.job_title)
            job_title = job_title.job_title

            user = UserDA().get_user_by_id(user_id)
            hr_name = user.first_name+ ' '+ user.last_name
            first_name = candidate_data.data.get("first_name", None)
            last_name = candidate_data.data.get("last_name", None)
            email = candidate_data.data.get("email", None)
            phone = candidate_data.data.get("phone", None)
            offer_released_date = candidate_data.data.get("offer_released_date", None)
            offer_accepted_date = candidate_data.data.get("offer_accepted_date", None)
            expected_joining_date = candidate_data.data.get("expected_joining_date", None)
            organization_id = candidate_data.data.get("organization_id", None)
            doc = candidate_data.FILES['offer_letter']
            if email and phone:
              is_alredy_exist = self.is_phone_and_email_unique(email,phone)
            else:
                result['error'] = "Invalid Phone or Email Adress ."
                result['status'] = 499
                return result
            if is_alredy_exist:
                result['error'] = "A candidate with this email or phone number already exists."
                result['status'] = 499
                return result

            candidate_data_dict['onboarding_code'] = str(uuid.uuid4())
            candidate_data_dict['first_name'] = first_name
            candidate_data_dict['last_name'] = last_name
            candidate_data_dict['email'] = email
            candidate_data_dict['phone'] = phone
            candidate_data_dict['offer_released_date'] = offer_released_date
            candidate_data_dict['offer_accepted_date'] = offer_accepted_date
            candidate_data_dict['expected_joining_date'] = expected_joining_date
            candidate_data_dict['status'] = 1 #pending
            candidate_data_dict['organization_id'] = organization_id
            with transaction.atomic():
                name = self.upload_pre_employment_docs(doc,candidate_data_dict['onboarding_code'])
                candidate_data_dict['offer_letter'] = name
                OnboardingDA().create_new_candidate(candidate_data_dict)
                result['message'] = "New Candidate Created Successfully ."
                result['status'] = 200
            company_name = Utility().get_organization_name(int(organization_id))
            company_name_short_form = self.get_company_name_shortform(int(organization_id))
            email_content_dto = new_dto()
            email_content_dto.company_name = company_name
            email_content_dto.company_name_short = company_name_short_form
            email_content_dto.designation = job_title
            email_content_dto.hr_name = hr_name
            email_content_dto.candidate_name = first_name+ ' '+ last_name
            email_content_dto.heading = "Pre-Employment Details"
            email_content_dto.link =  f"{settings.BASE_URL}candidate-details/{candidate_data_dict['onboarding_code']}"
            email_msg = OnBoardingNotificationBL()\
                .generate_on_boarding_email_message(email_content_dto)

            candidate_name =  first_name+ ' '+ last_name
            to_email = email
            email_subject = company_name+'-Candidate Details Required'
            OnBoardingNotificationBL()\
                .send_on_boarding_request_notification(email_msg, candidate_name, to_email, email_subject)
        except Exception as err:
            result["error"] = settings.ERROR_MSG['application_error']\
                .format(err, self.__log.error(self.__exception.get_exception()))
        return result

    def get_all_onboarding_candidates(self, user_id):
        result = {"error": '',"data": []}
        try:
            role_id, role_name = UserDA().get_user_role_by_id(user_id)
            if role_id not in [2] :
                result['error'] = settings.ERROR_MSG['access_denied']
                result['status'] = 403
                return result
            onboarding_candidates = OnboardingDA().get_all_onboarding_candidates()
            if onboarding_candidates:
                for candidate in onboarding_candidates:
                    temp = {}
                    temp['first_name'] = candidate.first_name
                    temp['last_name'] = candidate.last_name
                    temp['phone'] = candidate.phone
                    temp['email'] = candidate.email
                    temp['offer_released_date'] = candidate.offer_released_date
                    temp['expected_joining_date'] = candidate.expected_joining_date
                    temp['onboarding_code'] = candidate.onboarding_code
                    temp['offer_accepted_date'] = candidate.offer_accepted_date
                    temp['status'] = candidate.status
                    temp['offer_letter'] = self.__get_offer_letter_url(candidate.offer_letter)
                    temp['candidate_id'] = candidate.candidate_id
                    temp['organization_id'] = candidate.organization_id
                    temp['organization'] = Utility().get_organization_name(int(candidate.organization_id))
                    result['data'].append(temp)

        except Exception as err:
            result["error"] = settings.ERROR_MSG['application_error']\
                .format(err, self.__log.error(self.__exception.get_exception()))
        return result

    def edit_onboarding_candidate_details(self, user_id, edit_request):
        result = {}
        try:
            candidate_data_dict = {}
            role_id, role_name = UserDA().get_user_role_by_id(user_id)
            if role_id not in [2] :
                result['error'] = settings.ERROR_MSG['access_denied']
                result['status'] = 403
                return result
            candidate_id = edit_request.data.get("candidate_id", None)

            onboarding_candidate = OnboardingDA().get_onboarding_candidate_by_candidate_id(candidate_id)
            if onboarding_candidate:
                first_name = edit_request.data.get("first_name", None)
                last_name = edit_request.data.get("last_name", None)
                email = edit_request.data.get("email", None)
                phone = edit_request.data.get("phone", None)
                offer_released_date = edit_request.data.get("offer_released_date", None)
                offer_accepted_date = edit_request.data.get("offer_accepted_date", None)
                expected_joining_date = edit_request.data.get("expected_joining_date", None)
                organization_id =  edit_request.data.get("organization_id", None)
                message, is_dates_valid  = self.onboarding_dates_validation(offer_released_date, offer_accepted_date, expected_joining_date )
                if not is_dates_valid:
                    result['error'] = message
                    result['status'] = 499
                    return result
                try:
                    doc = edit_request.FILES['offer_letter']
                except:
                    doc = None
                onboarding_code = edit_request.data.get("onboarding_code", None)


                candidate_data_dict['onboarding_code'] = onboarding_code
                candidate_data_dict['first_name'] = first_name
                candidate_data_dict['last_name'] = last_name
                candidate_data_dict['email'] = email
                candidate_data_dict['email'] = email
                candidate_data_dict['phone'] = phone
                candidate_data_dict['offer_released_date'] = offer_released_date
                candidate_data_dict['offer_accepted_date'] = offer_accepted_date
                candidate_data_dict['expected_joining_date'] = expected_joining_date
                candidate_data_dict['organization_id'] = organization_id
                with transaction.atomic():
                    if doc:
                        name = self.upload_pre_employment_docs(doc,onboarding_code)
                    OnboardingDA().update_onboarding_candidate(candidate_data_dict, candidate_id)

                result['message'] = "Candidate Details Updated Successfully ."
                result['status'] = 200
            else:
                result['message'] = "Candidate Does Not Exist ."
                result['status'] = 499
        except Exception as err:
             result["error"] = settings.ERROR_MSG['application_error']\
                .format(err, self.__log.error(self.__exception.get_exception()))
        return result

    def onboarding_link_validation(self,on_boarding_code):
        result= { "error": '', "candidate_name": "", "status": 200 , "is_valid": False}
        try:
            candidates = OnboardingDA().get_onboarding_candidate_by_onboarding_code(on_boarding_code)

            if candidates:
                candidate = candidates[0]
                if candidate.status != 1:
                    result['error'] =  "Sorry, Either the link is expired or it is not valid."
                    result['status'] = 499
                    result['is_valid'] = False
                    return result
                result['candidate_name'] = candidate.first_name+" "+ candidate.last_name
                result['company'] = candidate.organization_id
                result['is_valid'] = True
            else:
                result['error'] =  "Sorry, Either the link is expired or it is not valid. "
                result['status'] = 499
                result['is_valid'] = False
        except Exception as err:
            result["error"] = settings.ERROR_MSG['application_error']\
                    .format(err, self.__log.error(self.__exception.get_exception()))
        return result

    def get_dropdowns_for_onboarding(self):
        result = {"error": ''}
        try:
            temp_list = []
            for k, v in settings.STATES.items():
                temp_list.append({"id": k, "name": v})
            result['states'] = temp_list
            del temp_list

            temp_list = []
            for k, v in settings.DISTRICTS.items():
                temp_list.append({"id": k, "name": v})
            result['districts'] = temp_list
            del temp_list
        except Exception as err:
            result['status'] = 499
            result["error"] = settings.ERROR_MSG['application_error']\
                .format(err, self.__logs.error(self.__exception.get_exception()))
        return result

    def get_KYC_document_types(self):
        result = {"error": '', "doc_types": []}
        try:
            doc_types = OnboardingDA().get_all_kyc_doc_types()
            for each_doc_type in doc_types:
                temp = {}
                temp['doc_type'] = each_doc_type.doc_name
                temp['doc_type_id'] = each_doc_type.id
                result['doc_types'].append(temp)

        except Exception as err:
            result['status'] = 499
            result["error"] = settings.ERROR_MSG['application_error']\
                .format(err, self.__log.error(self.__exception.get_exception()))
        return result

    def is_candidate_details_already_updated(self, onboarding_code):
        is_already_updated = False
        candidate_list = OnboardingDA().get_onboarding_candidate_by_onboarding_code(onboarding_code)
        if candidate_list[0]:
            if candidate_list[0].status != 1: #for pending TODO
                is_already_updated = True
        return is_already_updated


    def is_on_boarding_candidate_exist(self, onboarding_code):
        is_exist = False
        candidate_list = OnboardingDA().get_onboarding_candidate_by_onboarding_code(onboarding_code)
        if candidate_list:
                is_exist = True
        return is_exist



    # def save_candidate_details
    def fill_onboarding_candidate_details(self, request):
        result = {}
        try:

            onboarding_code = request.data.get("onboarding_code", None)
            is_candidate_exist = self.is_on_boarding_candidate_exist(onboarding_code)
            if not is_candidate_exist:
                result['error'] =  "Candidate does not exist. "
                result['status'] = 499
                result['is_valid'] = False
                return result


            is_already_filled = self.is_candidate_details_already_updated(onboarding_code)
            if is_already_filled:
                result['error'] =  "Candidate details already updated. "
                result['status'] = 499
                result['is_valid'] = False
                return result

            candidate_list = OnboardingDA().get_onboarding_candidate_by_onboarding_code(onboarding_code)

            onboarding_candidate = candidate_list[0]

            update_data = {}
            update_data["candidate_data"] =  json.dumps(request.data)
            update_data['status'] = 2  #TODO for details entered


            OnboardingDA().update_onboarding_candidate(update_data,onboarding_candidate.candidate_id)
            result['message'] = "Candidate details submitted succefully."
            result['is_valid'] = False
        except Exception as err:
            result['status'] = 499
            result["error"] = settings.ERROR_MSG['application_error']\
                .format(err, self.__log.error(self.__exception.get_exception()))
        return result


    def get_details_filled_by_onboarding_candidate(self, user_id, onboarding_token):
        result = {"error": "", "data":None, "permission": True}
        try:
            is_candidate_exist = self.is_on_boarding_candidate_exist(onboarding_token)
            if not is_candidate_exist:
                result['error'] =  "Candidate does not exist. "
                result['status'] = 499
                result['permission'] = False
                return result

            role_id, role_name = UserDA().get_user_role_by_id(user_id)
            if role_id not in [2] :
                result['error'] = settings.ERROR_MSG['access_denied']
                result['status'] = 403
                result['permission'] = False
                return result

            onboarding_candidate_list = OnboardingDA().get_onboarding_candidate_by_onboarding_code(onboarding_token)
            if onboarding_candidate_list:
                onboarding_candidate = onboarding_candidate_list[0]
                if onboarding_candidate.status not in [2, 3, 4]:
                    result['error'] =  "Details does not exist. "
                    result['status'] = 499
                    result['permission'] = False
                    return result
                result['data'] = json.loads(onboarding_candidate.candidate_data)



            else:
                result['error'] =  "Candidate does not exist. "
                result['status'] = 499
                result['permission'] = False
                return result


        except Exception as err:
            result['status'] = 499
            result["error"] = settings.ERROR_MSG['application_error']\
                .format(err, self.__log.error(self.__exception.get_exception()))
        return result


    def update_onboarding_candidate_status(self, user_id, request):
        result = {"error": ''}
        try:
            role_id, role_name = UserDA().get_user_role_by_id(user_id)
            if role_id not in [2] :
                result['error'] = settings.ERROR_MSG['access_denied']
                result['status'] = 403
                return result

            action = request.data.get("action", None)
            comment = request.data.get("comment", None)
            candidate_id = request.data.get("candidate_id", None)

            onboarding_candidate = OnboardingDA().get_onboarding_candidate_by_candidate_id(candidate_id)
            if onboarding_candidate:
                if action.upper() in ['APPROVE', 'DELETE', 'REJECT' ]:

                    update_data = {}

                    if action.upper() == "APPROVE":
                        update_data['status'] = 3 #TODO approved
                        message = "Candidate details have been approved successfully."
                    if action.upper() == "REJECT":
                        update_data['status'] = 4 #TODO rejecetd
                        message = "Candidate details have been rejected successfully."
                    update_data['comment'] = comment

                    if action.upper() == "DELETE":
                        message = "Candidate details deleted successfully ."
                        delete_data = {}
                        str_date = datetime.today().strftime('%m%d%H%M%S%f')
                        delete_data['is_deleted'] = 1
                        delete_data['email'] = str(onboarding_candidate.email) + "_de_" + str_date
                        delete_data['phone'] = str(onboarding_candidate.phone) + "_de_" + str_date
                        OnboardingDA().update_onboarding_candidate(delete_data, candidate_id)
                    else:
                        OnboardingDA().update_onboarding_candidate(update_data, candidate_id )
                    result['message'] = message
            else:
                result['error'] = "Candidate does not exist"
                result['status'] = 499



        except Exception as err:
            result['status'] = 499
            result["error"] = settings.ERROR_MSG['application_error']\
                .format(err, self.__log.error(self.__exception.get_exception()))
        return result

    def get_onboard_user_dropdowns(self):
        result = {"error": ''}
        try:
            supervisors, error = UserDA().get_all_supervisors()
            if supervisors:
                temp_list = []
                for supervisor in supervisors:
                    temp_list.append({"id": supervisor[0], "name": supervisor[1] + " " + supervisor[2]})
                result['supervisors'] = temp_list
                del temp_list
                temp_list = []
            for k, v in settings.EMPLOYMENT_STATUS.items():
                temp_list.append({"id": k, "status": v})
            result['employment_status'] = temp_list
            del temp_list

            temp_list = []
            job_titles = UserDA().get_all_job_titles()
            for job_title in job_titles:
                temp_list.append({"id": job_title.id, "title": job_title.job_title})
            result['job_titles'] = temp_list
            del temp_list
        except Exception as err:
            result['status'] = 499
            result["error"] = settings.ERROR_MSG['application_error']\
                .format(err, self.__log.error(self.__exception.get_exception()))
        return result

    def is_emp_code_already_used(self, emp_code):
        result = False
        query = UserDA().get_verify_employee(emp_code)
        if not query:
            result = True
        return result

    def is_approved_onboarding_candidate_exist(self, candidate_id):
        is_exist = False
        candidate = OnboardingDA().get_onboarding_candidate_by_candidate_id(candidate_id)
        if candidate:
            is_exist = True
        return is_exist, candidate


    def load_onboarding_candidate_as_user(self, user_id, request):
        result = {"error": ''}
        try:
            role_id, role_name = UserDA().get_user_role_by_id(user_id)
            if role_id not in [2] :
                result['error'] = settings.ERROR_MSG['access_denied']
                result['status'] = 403
                return result

            candidate_id = request.data.get("candidate_id", None)
            emp_code = request.data.get("emp_id", None)
            date_joined = request.data.get("date_joined", None)
            job_title = request.data.get("job_title", None)
            job_status = request.data.get("job_status", None)
            email = request.data.get("email", None)
            reporting_person = request.data.get("reporting_person", None)

            if emp_code:
                is_emp_id_already_exist = self.is_emp_code_already_used(emp_code)
                if not is_emp_id_already_exist:
                    result['error'] = "Emp Id is alredy in use ."
                    result['status'] = 499
                    return result
            else:
                result['error'] = "Invalid Emp Id ."
                result['status'] = 499
                return result

            is_mail_id_already_exist = self.is_mail_id_already_exist(email)
            if is_mail_id_already_exist:
                result['error'] = "Mail Id is alredy in use ."
                result['status'] = 499
                return result

            is_exist,candidate = self.is_approved_onboarding_candidate_exist(candidate_id)
            if not is_exist:
                result['error'] = "Invalide Candidate_id ."
                result['status'] = 499
                return result

            candidate_details = json.loads(candidate.candidate_data)
            organization_id = candidate.organization_id

            work_experience = candidate_details.get("work_experience", None)
            kyc_details = candidate_details.get("kyc_details", None)
            skills = candidate_details.get("skills", None)
            educational_details = candidate_details.get("educational_details", None)
            work_experience = candidate_details.get("work_experience", None)
            basic_info = candidate_details.get("basic_info", None)
            permenant_address = candidate_details.get("permenant_address", None)
            current_address = candidate_details.get("current_address", None)
            contact_details = candidate_details.get("contact_details", None)
            additional_info = candidate_details.get("additional_info", None)


            with transaction.atomic():
                user_create_data = self.format_auth_user_data(emp_code, date_joined, email, job_title, basic_info )
                user = UserDA().create_user(user_create_data)

                emp_id = user.id

                secret_key = pyotp.random_base32()

                emergency_contact_create_data = self.format_emergency_contact_details(emp_id, additional_info) #TODO  remove hard coded emp_id

                user_profile_create_data = self.format_user_profile_details(
                    emp_id, basic_info, permenant_address, current_address, contact_details, additional_info, job_title, job_status, organization_id, secret_key, user.username)


                work_experience_create_data = self.format_work_exp_details(emp_id, work_experience)

                kyc_details_create_data = self.format_kyc_details(emp_id, kyc_details)

                educational_info_create_data = self.format_educational_details(emp_id, educational_details)

                skill_info =  self.format_skill_info(emp_id, skills)

                user_profile = UserDA().create_user_profile(user_profile_create_data)

                emergency_contact = UserDA().create_emergency_contacts(emergency_contact_create_data)

                for wrk_exp in work_experience_create_data:
                    OnboardingDA().create_employee_work_experience(wrk_exp)

                for educational_detail in educational_info_create_data:
                    OnboardingDA().create_employee_academic_details(educational_detail)

                for kyc_detail in kyc_details_create_data:
                    OnboardingDA().create_employee_kyc_documents(kyc_detail)

                for skill in skill_info:
                    OnboardingDA().create_employee_skills(skill)


                UserDA().create_employee_lead_mapping(user.id, reporting_person, datetime.today())
                ProjectDA().create_project_employee_mapping(16, user.id)
                ProjectDA().create_project_employee_mapping(24, user.id)

                self.create_user_leave_quota(user.id)
                self.send_welcome_email_to_employee(user_create_data)
                self.send_two_fa_qr_code_to_employee(user, secret_key)
                update_data = {"status": 4 } # complted
                OnboardingDA().update_onboarding_candidate(update_data,candidate.candidate_id)
                result['message'] = "User created Successfully"









        except Exception as err:
            result['status'] = 499
            result["error"] = settings.ERROR_MSG['application_error']\
                .format(err, self.__log.error(self.__exception.get_exception()))
        return result

    def format_auth_user_data(self,emp_code,date_joined, email, job_title,basic_info_dict):
        dto = new_dto()
        dto.is_superuser = 0
        dto.is_staff = 0
        dto.is_active = 0
        dto.username = emp_code
        dto.first_name = basic_info_dict[0].get("first_name")
        dto.last_name = basic_info_dict[0].get("last_name")
        dto.email = email
        date_joined = Utility().convert_string_to_date_time(date_joined, "%Y-%m-%d")
        dto.date_joined = date_joined.strftime("%Y-%m-%d")
        dto.password = str(dto.first_name[:4]).upper() + date_joined.strftime("%Y%m%d")
        dto.group_id = settings.USER_ROLES['DEVELOPER']

        return dto


    def format_emergency_contact_details(self,emp_id, additional_info):
        emergency_data = {}
        emergency_data['emp_id'] = emp_id
        emergency_data['name'] = additional_info[0].get("emergency_contact_person")
        emergency_data['relationship'] = additional_info[0].get("relationship")
        emergency_data['mobile_no'] = additional_info[0].get("emergency_contact")
        return emergency_data

    def format_user_profile_details(self,emp_id, basic_info,permenant_address,current_address,contact_details, additional_info, job_title, job_status, organization_id , secret_key,emp_code):
        user_profile_data = {}

        user_profile_data['user_id'] = emp_id
        user_profile_data['dob'] = basic_info[0].get("dob", None)
        user_profile_data['gender'] =  basic_info[0].get("gender", None)
        user_profile_data['marital_status'] = basic_info[0].get("marital_status", None)
        user_profile_data['job_status'] = job_status
        user_profile_data['job_title'] = job_title
        user_profile_data['address_1'] = current_address[0].get("address1", None)
        user_profile_data['address_2'] = current_address[0].get("address2", None)
        user_profile_data['city_code'] = current_address[0].get("city_code", None)
        user_profile_data['coun_code'] = 91 # TO DO remove hard code
        user_profile_data['provin_code'] = current_address[0].get("state_id", None)
        user_profile_data['district_code'] = current_address[0].get("district_id", None)
        user_profile_data['zipcode'] = current_address[0].get("zip_code", None)
        user_profile_data['permanent_address_1'] = permenant_address[0].get("address1", None)
        user_profile_data['permanent_address_2'] = permenant_address[0].get("address2", None)
        user_profile_data['permanent_city_code'] = permenant_address[0].get("city_code", None)
        user_profile_data['permanent_coun_code'] = 91 # TO DO remove hard code
        user_profile_data['permanent_provin_code'] = permenant_address[0].get("state_id", None)
        user_profile_data['permanent_district_code'] = permenant_address[0].get("district_id", None)
        user_profile_data['permanent_zipcode'] = permenant_address[0].get("zip_code", None)
        user_profile_data['mobile'] = contact_details[0].get("mobile", None)
        user_profile_data['personal_email'] = contact_details[0].get("personal_email", None)
        user_profile_data['blood_group'] = additional_info[0].get("blood_group", None)
        user_profile_data['company_id'] = organization_id
        user_profile_data['secret_key'] = secret_key
        user_profile_data['is_twofa_on'] = 1
        image_name =self.save_emp_profile_image(emp_code,basic_info)
        if image_name:
             user_profile_data['profile_photo'] = image_name

        return user_profile_data

    def save_emp_profile_image(self, emp_code, basic_info ):
        try:
            obj_image_name = basic_info[0].get('photo', None)
            if obj_image_name is not None:
                if obj_image_name.lower().endswith('png'):
                    img_type = 'png'
                elif obj_image_name.lower().endswith('jpg'):
                    img_type = 'jpeg'
                else:
                    img_type = 'jpeg'
            obj_photo = str(basic_info[0].get('photo')).replace(f"data:image/{img_type};base64,","")
            file_path = os.path.join(settings.MEDIA_ROOT, f"employee_profile_photo/{emp_code}.{img_type}")
            FileManager().upload_file(file_path, base64.b64decode((obj_photo)))
        except Exception as e:
            pass

        return str(emp_code)+'.'+str(img_type)

    def format_work_exp_details(self, emp_id, work_experiences):
        wrk_exps = []
        for wrk_exp_dict in work_experiences:
            temp = {}
            temp['emp_id'] = emp_id
            temp['company_name'] = wrk_exp_dict.get("company_name", None)
            temp['role'] = wrk_exp_dict.get("job_role", None)
            joining_date = wrk_exp_dict.get("joining_date", None)
            if joining_date:
                temp['joining_date'] = datetime.strptime(joining_date,"%Y-%m-%d")
            relieving_date = wrk_exp_dict.get("relieving_date", None)
            if relieving_date:
                temp['relieving_date'] = datetime.strptime(relieving_date,"%Y-%m-%d")

            base64_exp_certificate = wrk_exp_dict.get("exp_certificate", None)
            if base64_exp_certificate:
                exp_certificate = self.save_exp_certificate(emp_id,base64_exp_certificate)
                temp['experience_certificate'] = exp_certificate

            base64_relieving_letter = wrk_exp_dict.get("relieving_letter", None)
            if base64_relieving_letter:
                relieving_letter = self.save_relieving_letter(emp_id,base64_relieving_letter)
                temp['releiving_letter'] = relieving_letter

            base64_pay_slip = wrk_exp_dict.get("pay_slip", None)
            if base64_pay_slip:
                pay_slip = self.save_pay_slip(emp_id,base64_pay_slip)
                temp['pay_slip'] = pay_slip

            temp['last_ctc'] = wrk_exp_dict.get("last_ctc", None)

            wrk_exps.append(temp)

        return wrk_exps

    def save_exp_certificate(self, emp_id, base64_exp_certificate):
        obj_doc = str(base64_exp_certificate).replace("data:application/pdf;base64,","")
        fileName = uuid.uuid4()
        file_path = os.path.join(settings.CONFIDENTIAL_DOCS, f"experience_certificates/{fileName}.pdf")
        FileManager().upload_encrypted_file(file_path, obj_doc.encode())

        return str(fileName)+'.pdf'


    def save_relieving_letter(self, emp_id,base64_relieving_letter):
        obj_doc = str(base64_relieving_letter).replace("data:application/pdf;base64,","")
        fileName = uuid.uuid4()
        file_path = os.path.join(settings.CONFIDENTIAL_DOCS, f"relieving_letters/{fileName}.pdf")
        FileManager().upload_encrypted_file(file_path, obj_doc.encode())

        return str(fileName)+'.pdf'

    def save_pay_slip(self, emp_id,base64_pay_slip):
        obj_doc = str(base64_pay_slip).replace("data:application/pdf;base64,","")
        fileName = uuid.uuid4()
        file_path = os.path.join(settings.CONFIDENTIAL_DOCS, f"pay_slip/{fileName}.pdf")
        FileManager().upload_encrypted_file(file_path, obj_doc.encode())

        return str(fileName)+'.pdf'


    def format_kyc_details(self, emp_id, kyc_detail):
        kyc_details = []
        for each_kyc in kyc_detail:
            temp = {}
            temp['emp_id'] = emp_id
            temp['kyc_doc_type_id'] = each_kyc.get("doc_type", None)
            base64_kyc_doc = each_kyc.get("document", None)
            if base64_kyc_doc:
                file_name =self.save_kyc_document(emp_id, base64_kyc_doc)
                temp['kyc_document'] = file_name
            else:
                continue
            kyc_details.append(temp)
        return kyc_details

    def save_kyc_document(self, emp_id,base64_kyc_doc):
        obj_doc = str(base64_kyc_doc).replace("data:application/pdf;base64,","")
        fileName = uuid.uuid4()
        file_path = os.path.join(settings.CONFIDENTIAL_DOCS, f"kyc_documents/{fileName}.pdf")
        FileManager().upload_encrypted_file(file_path, obj_doc.encode())

        return str(fileName)+'.pdf'

    def format_educational_details(self, emp_id, educational_details):
        educational_info = []
        for each_educational_info in educational_details:
            temp = {}
            temp['emp_id'] = emp_id
            temp['course'] = each_educational_info.get("course", None)
            temp['percentage'] = each_educational_info.get("percentage", None)
            start_date = each_educational_info.get("start_date", None)
            end_date = each_educational_info.get("end_date", None)
            if start_date:
                temp['start_date'] = datetime.strptime(start_date, "%Y-%m-%d")

            if end_date:
                temp['end_date'] = datetime.strptime(end_date, "%Y-%m-%d")
            temp['year_of_passout'] = each_educational_info.get("year_of_passout", None)
            temp['university'] = each_educational_info.get("university", None)

            base64_certificate = each_educational_info.get("certificate", None)
            if base64_certificate:
                certificate_name = self.save_educational_certificates(emp_id, base64_certificate)
                temp['certificate'] = certificate_name
            educational_info.append(temp)
        return educational_info

    def save_educational_certificates(self, emp_id, base64_certificate):
        obj_doc = str(base64_certificate).replace("data:application/pdf;base64,","")
        fileName = uuid.uuid4()
        file_path = os.path.join(settings.CONFIDENTIAL_DOCS, f"educational_certificates/{fileName}.pdf")
        FileManager().upload_encrypted_file(file_path, obj_doc.encode())

        return str(fileName)+'.pdf'

    def format_skill_info(self, emp_id, skills):
        skill_info = []
        for skill in skills:
            temp = {}
            temp['emp_id'] = emp_id
            temp['skill'] = skill.get("skill", None)
            temp['rating'] = skill.get("rating", None)
            temp['months_of_experience'] =  skill.get("months_of_experience", None)
            skill_info.append(temp)
        return skill_info


    def create_user_leave_quota(self,user_id):
        leave_period = LeaveDA().get_leave_period_by__date(datetime.now())
        leave_types = LeaveDA().get_all_leave_types()
        for leave_type in leave_types:
            leave_quota_dict = {
                        "leave_type_id": 0,
                        "leave_period_id": leave_period.leave_period_id,
                        "employee_id": user_id,
                        "no_of_days_allotted": 0
                    }
            leave_quota_dict['leave_type_id'] = leave_type.leave_type_id
            if (leave_type.leave_type_name).lower() == 'general':
                leave_quota_dict['no_of_days_allotted'] = settings.PROBATION_GENERAL_LEAVE
            if (leave_type.leave_type_name).lower() == 'lop':
                leave_quota_dict['no_of_days_allotted'] = settings.PROBATION_LOP_LEAVE
            LeaveDA().create_leave_quota(leave_quota_dict)



    def send_welcome_email_to_employee(self, user):
        employe_name = str(user.first_name) + ' ' + str(user.last_name)
        context = {
            'employe_name': employe_name,
            'user_name': str(user.email) ,
            'password': str(user.password)}
        message = get_template('email/welcome_new_employee.html').render(context)
        mail_dto = new_dto()
        mail_dto.subject = "Welcome to DM Desk !!!"
        mail_dto.from_address = settings.EMAIL_ADDRESS['do_not_reply']['name']
        mail_dto.body = message
        mail_dto.to_addresses = [user.email, 'hr@mydomain.com']
        mail_dto.smtp_username = settings.EMAIL_ADDRESS['do_not_reply']['mailID']
        mail_dto.smtp_password = settings.EMAIL_ADDRESS['do_not_reply']['password']
        Email().send_html_mail(mail_dto)

    def send_two_fa_qr_code_to_employee(self, user, secret_key):
        employe_name = str(user.first_name) + ' ' + str(user.last_name)
        context = {'employe_name': employe_name}
        message = get_template('email/welcome_qr_code.html').render(context)
        # secret_key = user.secret_key
        qr_code = Utility().qrcode_generator(secret_key, user.email)
        temp = BytesIO()
        qr_code.save(temp, format="png")
        mail_dto = new_dto()
        mail_dto.subject = "DM Desk 2FA Setup"
        mail_dto.from_address = settings.EMAIL_ADDRESS['do_not_reply']['name']
        mail_dto.body = message
        mail_dto.to_addresses = [user.email]
        mail_dto.smtp_username = settings.EMAIL_ADDRESS['do_not_reply']['mailID']
        mail_dto.smtp_password = settings.EMAIL_ADDRESS['do_not_reply']['password']
        mail_dto.image = temp.getvalue()
        Email().send_html_mail_v1(mail_dto)

    def is_mail_id_already_exist(self, mail):
        is_exist = False
        user = UserDA().get_user_by_email(mail)
        if user:
            is_exist = True
        return is_exist

    def get_company_name_shortform(self, company_id):
        name = ''
        if int(company_id) == 2:
            name = "DM"
        else:
            name = "EM"
        return name






