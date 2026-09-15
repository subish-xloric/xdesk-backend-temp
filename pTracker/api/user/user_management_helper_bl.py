import base64
import os
import uuid
from cryptography.fernet import Fernet

from pTracker.common.utility import Utility
from pTracker.common.exception_handler import ExceptionHandler
from pTracker.common.logs import Logs
from pTracker.common.file_manager import FileManager

from django.conf import settings


from pTracker.dataaccess.ptracker_access.user_da import UserDA
from pTracker.dataaccess.ptracker_access.onboarding_da import OnboardingDA
from pTracker.dataaccess.ptracker_access.rewards_da import RewardsDA


class UserManagementHelperBL():
    def __init__(self):
        self.__exception = ExceptionHandler()
        self.__utility = Utility()
        self.__logs = Logs()
        self.__fernet = Fernet(settings.FERNET_KEY)
        self.__file_manager = FileManager()
    

    def is_permiitted_to_view_profile(self, user_id, emp_id):
        permitted = False
        is_team_member = UserDA().is_team_member(emp_id, user_id)
        if emp_id == user_id:
            permitted = True
        elif is_team_member:
            permitted = True
        else:
            permitted = self.__utility.is_permitted(user_id, 'view_employee_detail_profile')
        return permitted

    def get_active_employee_dict(self):
        user_dict = {}
        active_users = UserDA().get_all_active_users()
        for user in active_users:
            user_dict[user.id] = user

    def _get_job_title_dict(self):
        job_title_dict = {}
        job_titles = UserDA().get_all_job_titles()
        for job in job_titles:
            job_title_dict[job.id] = job.job_title
        return job_title_dict

    def format_basic_info(self, employee, user_profile, emp_lead_mapping):
        basic_info = {}
        if emp_lead_mapping:
            lead = UserDA().get_user_by_id(emp_lead_mapping.lead_id)
            if lead:
                basic_info['reporting_to'] = lead.first_name + ' ' + lead.last_name
        if employee:
            basic_info['first_name'] = employee.first_name
            basic_info['last_name'] = employee.last_name
        if user_profile:
            basic_info['gender'] = user_profile.gender
            basic_info['marital_status'] = user_profile.marital_status
            basic_info['dob'] = user_profile.dob
            basic_info['job_status_id'] = user_profile.job_status
            basic_info['job_status'] = settings.EMPLOYMENT_STATUS[int(user_profile.job_status)]
            basic_info['job_title_id'] = user_profile.job_title
            basic_info['pan'] = user_profile.pan
            job_titles = self._get_job_title_dict()
            basic_info['job_title'] = job_titles.get(int(user_profile.job_title), None)

            image_name = user_profile.profile_photo
            if image_name:
                    try:
                        file_path = os.path.join(settings.MEDIA_ROOT, f'employee_profile_photo/{user_profile.profile_photo}')
                        image_data = self.__file_manager.read_file(file_path)
                        if not image_data:
                            raise FileNotFoundError("Image not found")
                        encoded_string = base64.b64encode(image_data)
                        basic_info['photo']= encoded_string
                    except Exception as e:
                        file_path = os.path.join(settings.MEDIA_ROOT, f'employee_profile_photo/avatar.jpeg')
                        image_data = self.__file_manager.read_file(file_path)
                        encoded_string = base64.b64encode(image_data) if image_data else b''
                        basic_info['photo']= encoded_string
                    if image_name.lower().endswith('png'):
                        img_type = 'png'
                    elif image_name.lower().endswith('jpg'):
                        img_type = 'jpeg'
                    else:
                        img_type = 'jpeg'
                    basic_info['photo']= encoded_string
                    basic_info['img_type'] = img_type
        return basic_info

    def format_permananent_adress(self, user_profile):
        permananent_adress = {}
        if user_profile:
            permananent_adress['address1'] = user_profile.permanent_address_1
            permananent_adress['address2'] = user_profile.permanent_address_2
            permananent_adress['city_code'] = user_profile.permanent_city_code
            permananent_adress['district_id'] = user_profile.permanent_district_code
            permananent_adress['state_id'] = user_profile.permanent_provin_code
            permananent_adress['zip_code'] = user_profile.permanent_zipcode
        return permananent_adress

    def format_current_adress(self, user_profile):
        current_adress = {}
        if user_profile:
            current_adress['address1'] = user_profile.address_1
            current_adress['address2'] = user_profile.address_2
            current_adress['city_code'] = user_profile.city_code
            current_adress['district_id'] = user_profile.district_code
            current_adress['state_id'] = user_profile.provin_code
            current_adress['zip_code'] = user_profile.zipcode
        return current_adress

    def format_contact_details(self, user_profile):
        contact_details = {}
        if user_profile:
            contact_details['mobile'] = user_profile.mobile
            contact_details['home_telephone'] = user_profile.home_telephone
            contact_details['personal_email'] = user_profile.personal_email
        return contact_details

    def format_emergency_details(self, emergency_contacts, user_profile):
        emergency_details = {}
        if emergency_contacts:
            emergency_details['emergency_contact_person'] = emergency_contacts.name
            emergency_details['relationship'] = emergency_contacts.relationship
            emergency_details['emergency_contact'] = emergency_contacts.mobile_no
        if user_profile:
            emergency_details['blood_group'] = user_profile.blood_group
            emergency_details['father_name'] = user_profile.father_name
        return emergency_details

    def format_work_experiences(self, wrk_experiences):
        wrk_experience = []
        if wrk_experiences:
            for wrk_exp in wrk_experiences:
                temp = {}
                temp['wrk_exp_id'] = wrk_exp.id
                temp['company_name'] = wrk_exp.company_name
                temp['job_role'] = wrk_exp.role
                # temp['relieving_letter'] = wrk_exp
                # temp['exp_certificate'] = wrk_exp
                # temp['pay_slip'] = wrk_exp
                temp['joining_date'] = wrk_exp.joining_date
                temp['relieving_date'] = wrk_exp.relieving_date
                temp['last_ctc'] = wrk_exp.last_ctc

                exp_certificate = wrk_exp.experience_certificate
                if exp_certificate:
                    try:
                        file_path = os.path.join(settings.CONFIDENTIAL_DOCS, f'experience_certificates/{exp_certificate}')
                        decrypted_content = FileManager().read_encrypted_file(file_path)
                        temp['exp_certificate']= decrypted_content.decode() if decrypted_content else None
                    except Exception as e:
                        temp['exp_certificate']= None
                    temp['exp_certificate_type'] = 'pdf'

                releiving_letter = wrk_exp.releiving_letter
                if releiving_letter:
                    try:
                        file_path = os.path.join(settings.CONFIDENTIAL_DOCS, f'relieving_letters/{releiving_letter}')
                        decrypted_content = FileManager().read_encrypted_file(file_path)
                        temp['relieving_letter']= decrypted_content.decode() if decrypted_content else None
                    except Exception as e:
                        temp['relieving_letter']= None
                    temp['relieving_letter_type'] = 'pdf'

                pay_slip = wrk_exp.pay_slip
                if pay_slip:
                    try:
                        file_path = os.path.join(settings.CONFIDENTIAL_DOCS, f'pay_slip/{pay_slip}')
                        decrypted_content = FileManager().read_encrypted_file(file_path)
                        temp['pay_slip']= decrypted_content.decode() if decrypted_content else None
                    except Exception as e:
                        temp['pay_slip']= None
                    temp['pay_slip_type'] = 'pdf'

                wrk_experience.append(temp)
        return wrk_experience

    def format_kyc_details(self, kyc_details):
        kyc_info = []

        for each_kyc in kyc_details:
            file_extension = ''
            temp = {}
            temp['kyc_doc_id'] = each_kyc.id
            temp['doc_type'] = each_kyc.kyc_doc_type_id
            kyc_doc = each_kyc.kyc_document
            file_extension = kyc_doc.split('.')[1]

            if kyc_doc:
                try:
                    file_path = os.path.join(settings.CONFIDENTIAL_DOCS, 'kyc_documents', kyc_doc)
                    decrypted_content = FileManager().read_encrypted_file(file_path)
                    if decrypted_content:
                        doc = decrypted_content.decode()
                        if file_extension =='pdf':
                            doc = 'data:application/pdf;base64,'+doc
                        elif file_extension =='png':
                            doc = 'data:image/png;base64,'+doc
                        elif file_extension =='jpeg':
                            doc = 'data:image/jpeg;base64,'+doc
                            # data:image/png;base64
                            #data:image/jpeg;base64

                        temp['document'] = doc
                        temp['document_type'] = file_extension
                    else:
                        temp['document'] = None
                        temp['document_type'] = 'pdf'
                except Exception as e:
                    temp['document'] = None
                    temp['document_type'] = 'pdf'
            else:
                temp['document'] = None
                temp['document_type'] = 'pdf'

            kyc_info.append(temp)

        return kyc_info

    def format_educational_details(self, educational_details):
        educational_info = []
        for each_education in educational_details:
            temp = {}
            temp['edu_detail_id'] = each_education.id
            temp['course'] = each_education.course
            temp['start_date'] = each_education.start_date
            temp['end_date'] = each_education.end_date
            temp['year_of_passout'] = each_education.year_of_passout
            temp['percentage'] = each_education.percentage
            temp['university'] = each_education.university
            certificate = each_education.certificate
            if certificate:
                try:
                    file_path = os.path.join(settings.CONFIDENTIAL_DOCS, f'educational_certificates/{certificate}')
                    decrypted_content = FileManager().read_encrypted_file(file_path)
                    temp['certificate']= decrypted_content.decode() if decrypted_content else None
                except Exception as e:
                    temp['certificate']= None
                temp['doc_type'] = 'pdf'
            educational_info.append(temp)
        return educational_info

    def format_skill(self, skills):
        skill_list = []
        for each_skill in  skills:
            temp = {}
            temp['skill_id'] = each_skill.id
            temp['skill'] = each_skill.skill
            temp['rating'] = each_skill.rating
            temp['months_of_experience'] = each_skill.months_of_experience
            skill_list.append(temp)
        return skill_list


    def get_employee_detail_profile(self, user_id, emp_id, version='v1'):
        result = {"error": '', "status": 200, "rewards":[]}
        try:

            user_dict = {}
            
            if version == 'v2':
                emp_id = UserDA().get_user_id_by_secret_key(emp_id)
                if str(emp_id) != str(user_id):
                    result['error'] = settings.ERROR_MSG['access_denied']
                    result['status'] = 403
                    return result

            permitted =self.is_permiitted_to_view_profile(user_id, emp_id)
            if not permitted:
                result["error"] = settings.ERROR_MSG.get('access_denied')
                result['status'] = 403
                return result

            employee = UserDA().get_user_by_id(emp_id)

            user_profile = UserDA().get_user_profile_by_id(emp_id)

            emergency_contacts = UserDA().get_emergency_contacts_by_id(emp_id)

            kyc_details = OnboardingDA().get_kyc_details_by_emp_id(emp_id)

            wrk_experiences = OnboardingDA().get_work_experiences_by_emp_id(emp_id)

            educational_info = OnboardingDA().get_educational_details_by_emp_id(emp_id)

            skills = OnboardingDA().get_skills_by_emp_id(emp_id)

            emp_lead_mapping = UserDA().get_employee_lead_mapping_by_emp_id(emp_id)

            basic_info = self.format_basic_info(employee, user_profile,emp_lead_mapping )
            permananent_adress = self.format_permananent_adress(user_profile)
            current_adress = self.format_current_adress(user_profile)
            contact_details = self.format_contact_details(user_profile)
            emergency_details = self.format_emergency_details(emergency_contacts, user_profile)
            workExp = self.format_work_experiences(wrk_experiences)
            kyc_info = self.format_kyc_details(kyc_details)
            educational_details = self.format_educational_details(educational_info)
            skill_info = self.format_skill(skills)
            
            active_users = UserDA().get_all_users()
            for user in active_users:
                user_dict[user.id] = user.first_name  + " " + user.last_name
            
            user_rewards = RewardsDA().get_all_my_rewards(emp_id=emp_id)
            
            for each in user_rewards:
                temp_dict = {}
                temp_dict['nominated_by'] = user_dict[each.nominated_by]
                temp_dict['recieved_date'] = each.published_date.strftime('%m/%d/%Y')
                temp_dict['reward_type'] = each.reward_type.name
                temp_dict['title'] = each.title
                result['rewards'].append(temp_dict)

            result['basic_info'] = basic_info
            result['kyc_details'] = kyc_info
            result['permenant_address'] = permananent_adress
            result['current_address'] = current_adress
            result['contact_details'] = contact_details
            result['additional_info'] = emergency_details
            result['work_experience'] = workExp
            result['educational_details'] = educational_details
            result['skills'] = skill_info

        except Exception as err:
            result["error"] = settings.ERROR_MSG['application_error']\
                .format(err, self.__logs.error(self.__exception.get_exception()))
        return result

    def _clean_basic_info(self, basic_info_dict, emp_code):
        auth_update_data = {}
        user_prile_update_data = {}
        auth_update_data['first_name'] = basic_info_dict.get(
            "first_name", None)
        auth_update_data['last_name'] = basic_info_dict.get("last_name", None)

        user_prile_update_data['gender'] = basic_info_dict.get("gender", None)
        user_prile_update_data['marital_status'] = basic_info_dict.get(
            "marital_status", None)
        user_prile_update_data['job_status'] = basic_info_dict.get("job_status", None)
        user_prile_update_data['job_title'] = basic_info_dict.get("job_title", None)
        user_prile_update_data['dob'] = basic_info_dict.get("dob", None)
        user_prile_update_data['pan'] = basic_info_dict.get("pan", None)
        base64_image = basic_info_dict.get('photo', None)
        if base64_image:
            profile_image = self.save_emp_profile_image(emp_code, basic_info_dict)
            user_prile_update_data['profile_photo'] = profile_image


        return auth_update_data, user_prile_update_data

    def save_emp_profile_image(self, emp_code, basic_info):
        obj_image_name = basic_info.get('photo', None)
        if obj_image_name is not None:
            if obj_image_name.lower().endswith('png'):
                img_type = 'png'
            elif obj_image_name.lower().endswith('jpg'):
                img_type = 'jpeg'
            else:
                img_type = 'jpeg'
        obj_photo = str(basic_info.get('photo')).replace(
            f"data:image/{img_type};base64,", "")
        file_path = os.path.join(settings.MEDIA_ROOT, f"employee_profile_photo/{emp_code}.{img_type}")
        FileManager().upload_file(file_path, base64.b64decode((obj_photo)))

        return str(emp_code)+'.'+str(img_type)

    def _clean_contact_info(self, contact_info, emp_code):
        user_prile_update_data = {}
        permananent_adress = contact_info.get('permanent_adress', None)
        current_adress = contact_info.get('current_adress', None)
        contact_details = contact_info.get('contact_details', None)

        if current_adress:
            user_prile_update_data['address_1'] = current_adress.get("address1", None)
            user_prile_update_data['address_2'] = current_adress.get("address2", None)
            user_prile_update_data['city_code'] = current_adress.get("city_code", None)
            user_prile_update_data['district_code'] = current_adress.get("district_id", None)
            user_prile_update_data['provin_code'] = current_adress.get("state_id", None)
            user_prile_update_data['zipcode'] = current_adress.get("zip_code", None)

        if permananent_adress:
            user_prile_update_data['permanent_address_1'] = permananent_adress.get("address1")
            user_prile_update_data['permanent_address_2'] = permananent_adress.get("address2")
            user_prile_update_data['permanent_city_code'] = permananent_adress.get("city_code")
            user_prile_update_data['permanent_district_code'] = permananent_adress.get("district_id")
            user_prile_update_data['permanent_provin_code'] = permananent_adress.get("state_id")
            user_prile_update_data['permanent_zipcode'] = permananent_adress.get("zip_code")

        if contact_details:
            user_prile_update_data['mobile'] = contact_details.get("mobile")
            user_prile_update_data['home_telephone'] = contact_details.get("home_telephone")
            user_prile_update_data['personal_email'] = contact_details.get("personal_email")

        return user_prile_update_data

    def _clean_emergency_details(self, emergency_detail, emp_code ):
        user_profile_update_data = {}
        emergency_update_data = {}
        user_profile_update_data['blood_group'] = emergency_detail.get("blood_group", None)
        user_profile_update_data['father_name'] = emergency_detail.get("father_name", None)
        emergency_update_data['name'] = emergency_detail.get("emergency_contact_person", None)
        emergency_update_data['relationship'] = emergency_detail.get("relationship", None)
        emergency_update_data['mobile_no'] = emergency_detail.get("emergency_contact", None)
        return user_profile_update_data, emergency_update_data

    def _clean_kyc_details(self, kyc_details, emp_id):
        kyc_create_data = []
        for each_kyc in kyc_details:
            kyc_doc_id = each_kyc.get("kyc_doc_id", None)
            if kyc_doc_id:
                continue
            else:
                temp = {}
                temp['kyc_doc_type_id'] = each_kyc.get("doc_type", None)
                base64_kyc = each_kyc.get("document", None)
                kyc_doc_name = self.save_kyc_document(base64_kyc)
                temp['kyc_document'] = kyc_doc_name
                temp['emp_id'] = emp_id
                kyc_create_data.append(temp)
        return kyc_create_data

    def save_kyc_document(self, base64_kyc_doc):

        file_extension = '.pdf'
        if 'data:image/png;base64' in str(base64_kyc_doc):
            obj_doc = str(base64_kyc_doc).replace("data:image/png;base64,", "")
            file_extension = '.png'
        elif 'data:image/jpeg;base64' in str(base64_kyc_doc):
            obj_doc = str(base64_kyc_doc).replace("data:image/jpeg;base64,", "")
            file_extension = '.jpeg'
        else:
            obj_doc = str(base64_kyc_doc).replace("data:application/pdf;base64,", "")
        fileName = str(uuid.uuid4())
        file_path = os.path.join(settings.CONFIDENTIAL_DOCS, "kyc_documents", f"{fileName}{file_extension}")

        FileManager().upload_encrypted_file(file_path, obj_doc.encode())

        return fileName + file_extension


    def save_exp_certificate(self, base64_exp_certificate):
        obj_doc = str(base64_exp_certificate).replace("data:application/pdf;base64,","")
        fileName = str(uuid.uuid4())
        file_path = os.path.join(settings.CONFIDENTIAL_DOCS, "experience_certificates", f"{fileName}.pdf")
        try:
            FileManager().upload_encrypted_file(file_path, obj_doc.encode())
        except Exception as e:
            pass
        return fileName + ".pdf"


    def save_relieving_letter(self, base64_relieving_letter):
        obj_doc = str(base64_relieving_letter).replace("data:application/pdf;base64,","")
        fileName = str(uuid.uuid4())
        file_path = os.path.join(settings.CONFIDENTIAL_DOCS, f"relieving_letters/{fileName}.pdf")
        FileManager().upload_encrypted_file(file_path, obj_doc.encode())

        return fileName + ".pdf"

    def save_pay_slip(self, base64_pay_slip):
        obj_doc = str(base64_pay_slip).replace("data:application/pdf;base64,","")
        fileName = str(uuid.uuid4())
        file_path = os.path.join(settings.CONFIDENTIAL_DOCS, f"pay_slip/{fileName}.pdf")
        FileManager().upload_encrypted_file(file_path, obj_doc.encode())

        return fileName + '.pdf'

    def _clean_wrk_experiences(self, wrk_exps, emp_id):
        wrk_exp_create_data = []
        for each_wrk_exp in wrk_exps:
            wrk_exp_id = each_wrk_exp.get("wrk_exp_id", None)
            if wrk_exp_id:
                continue
            else:
                temp = {}
                temp['emp_id'] = emp_id
                temp['company_name'] = each_wrk_exp.get("company_name", None)
                temp['role'] = each_wrk_exp.get("job_role", None)
                temp['joining_date'] = each_wrk_exp.get("joining_date", None)
                temp['relieving_date'] = each_wrk_exp.get("relieving_date", None)
                temp['last_ctc'] = each_wrk_exp.get("last_ctc", None)
                base64_relieving_letter = each_wrk_exp.get("relieving_letter", None)
                if base64_relieving_letter:
                    relive_letter_name = self.save_relieving_letter(base64_relieving_letter)
                    temp['releiving_letter'] = relive_letter_name

                base64_exp_certificate = each_wrk_exp.get("exp_certificate", None)
                if base64_exp_certificate:
                    exp_certificate_name = self.save_exp_certificate(base64_exp_certificate)
                    temp['experience_certificate'] = exp_certificate_name

                base64_payslip = each_wrk_exp.get("pay_slip", None)
                if base64_payslip:
                    pay_slip_name = self.save_pay_slip(base64_payslip)
                    temp['pay_slip'] = pay_slip_name

                wrk_exp_create_data.append(temp)
        return wrk_exp_create_data

    def _clean_educational_details(self, educational_details, emp_id ):
        edu_info_create_data = []
        for each_edu_info in educational_details:
            edu_detail_id = each_edu_info.get("edu_detail_id", None)
            if edu_detail_id:
                continue
            else:
                temp = {}
                temp['course'] = each_edu_info.get("course", None)
                temp['start_date'] = each_edu_info.get("start_date", None)
                temp['end_date'] = each_edu_info.get("end_date", None)
                temp['year_of_passout'] = each_edu_info.get("year_of_passout", None)
                temp['percentage'] = each_edu_info.get("percentage", None)
                temp['university'] = each_edu_info.get("university", None)

                base64_certificate = each_edu_info.get("certificate", None)
                certificate_name = self.save_educational_certificates(base64_certificate)
                temp['certificate'] = certificate_name
                temp['emp_id'] = emp_id
                edu_info_create_data.append(temp)
        return edu_info_create_data

    def save_educational_certificates(self, base64_certificate):
        obj_doc = str(base64_certificate).replace("data:application/pdf;base64,","")
        fileName = str(uuid.uuid4())
        file_path = os.path.join(settings.CONFIDENTIAL_DOCS, f"educational_certificates/{fileName}.pdf")
        FileManager().upload_encrypted_file(file_path, obj_doc.encode())

        return fileName + '.pdf'

    def _clean_skills(self, skills, emp_id):
        skill_create_data = []
        for skill in skills:
            skill_id = skill.get("skill_id", None)
            if skill_id:
                continue
            else:
                temp = {}
                temp['skill'] = skill.get("skill", None)
                temp['rating'] = skill.get("rating", None)
                temp['months_of_experience'] = skill.get("months_of_experience", None)
                temp['emp_id'] = emp_id
                skill_create_data.append(temp)
        return skill_create_data


    def update_user(self, user_id, data, version='v1'):
        result = {"error": ''}
        emp_id = None
        try:
            role_id, role_name = UserDA().get_user_role_by_id(user_id)
            if version=='v2':
                emp_id = UserDA().get_user_id_by_secret_key(data.get("emp_id", None))
                data.update({'emp_id': emp_id})

                if str(emp_id) != str(user_id):
                    result['error'] = settings.ERROR_MSG['access_denied']
                    result['status'] = 403
                    return result

            elif role_id not in [2]:
                result['error'] = settings.ERROR_MSG['access_denied']
                result['status'] = 403
                return result

            if "emp_id" in  data.keys():
                emp_id = data.get("emp_id", None)
                employee = UserDA().get_user_by_id(emp_id)
            else:
                result["error"] = "Invalid request."
                result['status'] = 499
                return result
            if employee:
                if "basic_info" in  data.keys():
                    auth_update_data , user_prile_update_data = self._clean_basic_info(data['basic_info'],employee.username)
                    UserDA().update_auth_user(auth_update_data, emp_id)
                    UserDA().update_user_profile(emp_id, user_prile_update_data)

                if "contact_info" in  data.keys():
                    user_prile_update_data = self._clean_contact_info(data['contact_info'],employee.username)
                    UserDA().update_user_profile(emp_id, user_prile_update_data)

                if "emergency_details" in  data.keys():
                    user_prile_update_data ,emergency_update_data = self._clean_emergency_details(data['emergency_details'],employee.username)
                    UserDA().update_user_profile(emp_id, user_prile_update_data)
                    emergency_update_data['emp_id'] = emp_id
                    UserDA().update_emergency_contact(emergency_update_data, emp_id)

                if "kyc_details" in data.keys():
                    kyc_create_data = self._clean_kyc_details(data['kyc_details'], emp_id)
                    for each_kyc in kyc_create_data:
                        OnboardingDA().create_employee_kyc_documents(each_kyc)

                if "deleted_kyc_details" in data.keys():
                    deleted_kyc_list = data.get("deleted_kyc_details", None)
                    for each_deleted_kyc in deleted_kyc_list:
                        file_name = OnboardingDA().delete_kyc_document(each_deleted_kyc)
                        if file_name:
                            try:
                                os.remove(f'{settings.CONFIDENTIAL_DOCS}kyc_documents/{file_name}')
                            except:
                                pass

                if "wrk_experiences" in data.keys():
                    wrk_exp_create_data = self._clean_wrk_experiences(data['wrk_experiences'], emp_id)
                    for each_wrk_exp in wrk_exp_create_data:
                        OnboardingDA().create_employee_work_experience(each_wrk_exp)

                if "deleted_work_experiences" in data.keys():
                    deleted_wrk_exp_list = data.get("deleted_work_experiences", None)
                    for each_deleted_wrk_exp in deleted_wrk_exp_list:
                        wrk_exp = OnboardingDA().get_wrk_experience_by_id(each_deleted_wrk_exp)
                        if wrk_exp:
                            exp_letter_name = wrk_exp.experience_certificate
                            relieving_letter_name = wrk_exp.releiving_letter
                            pay_slip_name = wrk_exp.pay_slip
                            try:
                                if exp_letter_name:
                                    os.remove(f'{settings.CONFIDENTIAL_DOCS}experience_certificates/{exp_letter_name}')
                                if relieving_letter_name:
                                    os.remove(f'{settings.CONFIDENTIAL_DOCS}relieving_letters/{relieving_letter_name}')
                                if pay_slip_name:
                                    os.remove(f'{settings.CONFIDENTIAL_DOCS}pay_slip/{pay_slip_name}')
                            except:
                                pass
                            OnboardingDA().delete_wrk_experience(each_deleted_wrk_exp)

                if "educational_details" in data.keys():
                    edu_info_create_data= self._clean_educational_details(data['educational_details'], emp_id)
                    for each_edu_details in edu_info_create_data:
                        OnboardingDA().create_employee_academic_details(each_edu_details)

                if "deleted_educational_details" in data.keys():
                    deleted_educational_details = data.get("deleted_educational_details", None)
                    edu_detail_list = OnboardingDA().get_edu_details_by_list_of_id(deleted_educational_details)
                    for each_edu_info in edu_detail_list:
                        certifcate_name = each_edu_info.certificate
                        try:
                            os.remove(f'{settings.CONFIDENTIAL_DOCS}educational_certificates/{certifcate_name}')
                        except:
                            pass
                    OnboardingDA().delete_edu_details_by_list_of_id(deleted_educational_details)

                if "skills" in data.keys():
                    skill_info = self._clean_skills(data['skills'], emp_id)
                    for skill in skill_info:
                        OnboardingDA().create_employee_skills(skill)

                if "deleted_skills" in  data.keys():
                    deleted_skills = data.get("deleted_skills", None)
                    OnboardingDA().delete_skill_by_list_of_id(deleted_skills)

                result['message'] = "Employee profile details updated successfully ."



            else:
                result["error"] = "Employee does not exist ."
                result['status'] = 499
                return result
        except Exception as err:
            result["error"] = settings.ERROR_MSG['application_error']\
                .format(err, self.__logs.error(self.__exception.get_exception()))
        return result
