from functools import wraps
from multiprocessing.sharedctypes import Value
import pyotp
import base64
import os
import secrets
from io import BytesIO
from types import SimpleNamespace
from  datetime import datetime, timedelta

from django.conf import settings
from django.template.loader import get_template
from django.core.mail import EmailMessage

from django.db import DatabaseError, transaction
from django.core.files.storage import default_storage
from django.core.files.base import ContentFile

from pTracker.common.utility import Utility
from pTracker.common.exception_handler import ExceptionHandler
from pTracker.common.logs import Logs
from pTracker.common.file_manager import FileManager


from pTracker.notification_center.email_engine import Email
from pTracker.dataaccess.ptracker_access.user_da import UserDA
from pTracker.dataaccess.ptracker_access.project_da import  ProjectDA
from pTracker.dataaccess.ptracker_access.leave_da import LeaveDA
from pTracker.api.user.user_management_bl_v1 import UserManagementBL_V1
from pTracker.api.induction.induction_biz import InductionBL
from pTracker.wiki.data_access.master.logs_da import LogsDA
from pTracker.settings.constants import EMPLOYMENT_STATUS
from pTracker.dataaccess.ptracker_access.user_models import UserProfileProvisional


def new_dto():
    dto = SimpleNamespace()
    return dto

class UserManagementBL():
    def __init__(self):
        self.__exception = ExceptionHandler()
        self.__utility = Utility()
        self.__logs = Logs()
        self.__file_manager = FileManager()

    def __is_create_new_user_access(self, user_id):
        is_access = False
        role_id, role_name = UserDA().get_user_role_by_id(user_id)
        if role_id  in (1, 2, 3, "1", "2", "3"):
            is_access = True
        return is_access

    def __can_resend_qr_code(self, user_id):
        is_access = False
        role_id, role_name = UserDA().get_user_role_by_id(user_id)
        if role_id  in (2, "2"):
            is_access = True
        return is_access

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

    def __clean_profile_data(self, data):
        profile = data
        entries_to_remove = (
            'username', 'first_name', 'last_name',
            'email', 'date_joined','employee_id',
            'profile_data','is_valid','name',
            'mobile_no','relationship', 'induction')
        for k in entries_to_remove:
            profile.pop(k, None)
        return profile

    def __clean_auth_data(self, data):
        row = {}
        entries_to_add = ('username', 'first_name', 'last_name', 'email', 'date_joined')
        for k in entries_to_add:
            if data.get(k) :
                row[k] = (data.get(k))
        return row

    def __clean_emergency_data(self, data, user_id):
        row = {}
        entries_to_add = ('name', 'mobile_no', 'relationship')
        for k in entries_to_add:
            if data.get(k) :
                row[k] = (data.get(k))
        row['emp_id'] = user_id
        return row


    def create_new_user(self, data, user_id):
        result = {"error": "", "success": ""}
        try:
            #TODO  Permission checking
            if not self.__is_create_new_user_access(user_id):
                result["error"] = "You have no permission to create a user."
                return [result]

            #TODO Duplication checking EMPID, email , personal email, mobile
            dto = new_dto()
            dto.is_superuser = 0
            dto.is_staff = 0
            dto.is_active = 0
            dto.username = data.get('employee_id', 0)
            dto.first_name = data.get('first_name')
            dto.last_name = data.get('last_name')
            dto.email = data.get('email')
            reporting_person = data.get('reported_to', 0)
            date_joined = data.get('date_joined', '')
            dto.group_id = settings.USER_ROLES['DEVELOPER']
            date_joined = Utility().convert_string_to_date_time(date_joined, "%Y-%m-%d")
            # Random, unguessable temporary password (previously derived from
            # name+join date, which are both easily discoverable/guessable).
            dto.password = secrets.token_urlsafe(12)
            dto.date_joined = date_joined.strftime("%Y-%m-%d")
            initiate_induction = data.get('induction', False)

            obj_image_name = data.get('profile_photo')
            if obj_image_name is not None:
                if obj_image_name.lower().endswith('png'):
                    img_type = 'png'
                elif obj_image_name.lower().endswith('jpg'):
                    img_type = 'jpeg'
                else:
                    img_type = 'jpeg'
            with transaction.atomic():
                user = UserDA().create_user(dto)
                if user:
                    #TODO create user profile
                    obj_photo = str(data.get('profile_data')).replace(f"data:image/{img_type};base64,","")
                    file_path = os.path.join(settings.MEDIA_ROOT, f"employee_profile_photo/{user.username}.{img_type}")
                    self.__file_manager.upload_file(file_path, base64.b64decode(obj_photo))
                    emergency_data = self.__clean_emergency_data(data, user.id)
                    profile_data = self.__clean_profile_data(data)
                    secret_key = pyotp.random_base32()
                    dto.secret_key = secret_key
                    temp_data = {
                        'user_id':user.id,
                        'secret_key': secret_key,
                        'is_twofa_on':1
                    }
                    profile_data.update(temp_data)
                    user_profile = UserDA().create_user_profile(profile_data)
                    user_profile.profile_photo = f'{user.username}.{img_type}'
                    user_profile.save()
                    emergency_contact = UserDA().create_emergency_contacts(emergency_data)
                    emergency_contact.save()
                    #Assign reporting person
                    UserDA().create_employee_lead_mapping(user.id, reporting_person, datetime.today())
                    #Assign Projects
                    ProjectDA().create_project_employee_mapping(16, user.id)
                    ProjectDA().create_project_employee_mapping(17, user.id)
                    ProjectDA().create_project_employee_mapping(24, user.id)
                    self.create_user_leave_quota(user.id)
                    if initiate_induction:
                        InductionBL().create_induction_from_create_user(user_id, user.id)
                    self.send_welcome_email_to_employee(dto)
                    self.send_two_fa_qr_code_to_employee(dto)
                    msg = 'User created successfully !'
                    result['success'] = msg
                    return [result]
                else:
                    result["error"] = "We got an error while creating User."
                    return [result]

        except Exception as error:
            result["error"] = str(error)
            return [result]


    def update_user(self, data, user_id):
        result = {"error": None, "success": None}
        try:
            # Permission checking
            if not self.__is_create_new_user_access(user_id):
                result["error"] = "You have no permission to update details"
                return [result]
            with transaction.atomic():
                obj_image_name = data.get('profile_photo')
                if obj_image_name:
                    if obj_image_name.lower().endswith('png'):
                        img_type = 'png'
                    elif obj_image_name.lower().endswith('jpg'):
                        img_type = 'jpeg'
                    else:
                        img_type = 'jpeg'
                auth_data = self.__clean_auth_data(data)
                # Update auth user table
                user = UserDA().update_auth_user(auth_data, data.get('user_id'))
                if user:
                    obj_photo = str(data.get('profile_data')).replace(f"data:image/{img_type};base64,","")
                    img_name = data.get('employee_id')
                    file_path = os.path.join(settings.MEDIA_ROOT, f"employee_profile_photo/{img_name}.{img_type}")
                    self.__file_manager.upload_file(file_path, base64.b64decode(obj_photo))
                    report_to = data.get('reported_to', 0)
                    if report_to:
                        UserDA().update_employee_lead_mapping(data.get('user_id'), report_to)
                    emergency_data = self.__clean_emergency_data(data, user.id)
                    profile_data = self.__clean_profile_data(data)
                    # Update user profile table
                    UserDA().update_emergency_contact(emergency_data, user.id)
                    user_profile = UserDA().update_user_profile(int(profile_data['user_id']),profile_data)
                    user_profile.profile_photo = f'{img_name}.{img_type}'
                    user_profile.save()
                msg = 'User updated successfully !'
                result['success'] = msg
                return [result]
        except Exception as error:
            result["error"] = settings.ERROR_MSG['application_error']\
                .format(error, self.__logs.error(self.__exception.get_exception()))
            return [result]

    def resend_qr_code_by_user(self,login_user_id, user_id):
        result = {"error": "", "success": "", "status":200}
        try:
            if not self.__can_resend_qr_code(login_user_id):
                result['error'] = settings.ERROR_MSG['access_denied']
                result['status'] = 403
                return result
            user = UserDA().get_user_by_id(user_id)
            profile = UserDA().get_user_profile_by_id(user_id)
            user.secret_key = profile.secret_key
            self.send_two_fa_qr_code_to_employee(user)
            msg = 'QR Code sent to user email.'
            result['success'] = msg
        except Exception as error:
            result["error"] = str(error)
            result['status'] = 499
        return result

    def send_qr_code_test(self): #zzz
        user_ids = [69]
        for user_id in user_ids:

            profile_data = {
                'user_id':user_id,
                'secret_key': pyotp.random_base32(),
                'is_twofa_on':1
            }
            #UserDA().create_user_profile(profile_data)

            user = UserDA().get_user_by_id(user_id)
            profile = UserDA().get_user_profile_by_id(user_id)
            user.secret_key = profile.secret_key
            self.send_two_fa_qr_code_to_employee(user)


    def send_two_fa_qr_code_to_employee(self, user):
        employe_name = str(user.first_name) + ' ' + str(user.last_name)
        context = {'employe_name': employe_name}
        message = get_template('email/welcome_qr_code.html').render(context)
        secret_key = user.secret_key
        qr_code = Utility().qrcode_generator(user.secret_key, user.email)
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

    def is_user_two_fa_on(self, email):
        is_twofa_on = 0
        try:
            user = UserDA().get_user_by_email(email)
            profile = UserDA().get_user_profile_by_id(user.id)
            if profile:
                is_twofa_on = profile.is_twofa_on
        except :
            is_twofa_on = 0
        return is_twofa_on

    def verify_two_fa_token(self, email, token):
        is_valid = False
        try:
            user = UserDA().get_user_by_email(email)
            profile = UserDA().get_user_profile_by_id(user.id)
            if profile:
                secret_key = profile.secret_key
                is_valid = Utility().verify_time_based_otp(secret_key, token)
        except :
            is_valid = False
        finally:
            return is_valid


    def get_employee_detail_profile(self, emp_id, user_id):
        user_da = UserDA()
        result = {"error": None, "emp_profile": None, "status": 200}
        user_id = int(user_id)
        emp_id = int(emp_id)
        user_dict = {}
        mapping_dict = {}
        try:
            permitted = False  #xxx
            is_team_member = UserDA().is_team_member(emp_id, user_id)
            if emp_id == user_id:
                permitted = True
            elif(is_team_member):
                permitted = True
            if not permitted:
                permitted = self.__utility.is_permitted(user_id, 'view_employee_detail_profile')
            if not permitted:
                result["error"] = settings.ERROR_MSG.get('access_denied')
                result['status'] = 403
                return result
            active_users = user_da.get_all_active_users()
            for user in active_users:
                user_dict[user.id] = user.first_name  + " " + user.last_name
            lead_mappings = user_da.get_all_employee_lead_mapping()
            for each in lead_mappings:
                mapping_dict[each.emp_id] = each.lead_id
            employee = user_da.get_user_by_id(emp_id)
            profile = user_da.get_user_profile_by_id(emp_id)
            emergency = user_da.get_emergency_contacts_by_id(emp_id)

            if profile:
                obj_image_name = profile.profile_photo
                if obj_image_name:
                    try:
                        file_path = os.path.join(settings.MEDIA_ROOT, f'employee_profile_photo/{profile.profile_photo}')
                        image_data = self.__file_manager.read_file(file_path)
                        if not image_data:
                            raise FileNotFoundError("Image not found")
                        encoded_string = base64.b64encode(image_data)
                        profile.profile_photo = encoded_string
                    except Exception as e:
                        file_path = os.path.join(settings.MEDIA_ROOT, f'employee_profile_photo/avatar.jpeg')
                        image_data = self.__file_manager.read_file(file_path)
                        encoded_string = base64.b64encode(image_data) if image_data else b''
                        profile.profile_photo = encoded_string
                    if obj_image_name.lower().endswith('png'):
                        img_type = 'png'
                    elif obj_image_name.lower().endswith('jpg'):
                        img_type = 'jpeg'
                    else:
                        img_type = 'jpeg'
                    profile.profile_photo = encoded_string
                    profile.profile_data = img_type
                else:
                    file_path = os.path.join(settings.MEDIA_ROOT, f'employee_profile_photo/avatar.jpeg')
                    image_data = self.__file_manager.read_file(file_path)
                    encoded_string = base64.b64encode(image_data) if image_data else b''
                    profile.profile_photo = encoded_string
                    profile.profile_data = 'jpeg'
            if employee and profile:
                employee.date_joined = employee.date_joined.date()
                profile = profile.__dict__
                employee = employee.__dict__
                if emergency:
                    emergency  = emergency.__dict__
                else:
                    emergency = {'name':None, 'mobile_no':None, 'relationship':None}
                employee.update(emergency)
                employee.update(profile)
                entries_to_remove = ('_state', 'password', 'last_login', 'is_superuser', 'is_staff', 'secret_key', 'is_twofa_on', 'is_accout_blocked','reported_to')
                for k in entries_to_remove:
                    employee.pop(k, None)
                lead = { 'reported_to': user_dict.get(mapping_dict.get(emp_id, 0), '')}
                employee.update(lead)
                result['emp_profile'] = employee
        except Exception as err:
            result['status'] = 499
            result["error"] = settings.ERROR_MSG['application_error']\
                .format(err, self.__logs.error(self.__exception.get_exception()))
        finally:
            return result

    def get_employee_list(self, user_id):
        user_da = UserDA()
        result = {"error": None, "emp_list": None}
        mapping_dict = {}
        job_mapping_dict ={}
        user_dict = {}
        emp_list = []
        try:
            permitted = self.__utility.is_permitted(user_id, 'view_employee_list')
            if not permitted:
                result["error"] = settings.ERROR_MSG.get('access_denied')
                return result

            #filters Employee Name, 'Employment Status' Include, Supervisor Name, 'Job Title'
            emp_name=''
            job_status = ''
            job_title = ''
            reported_to = ''
            include = -1

            active_users = user_da.get_all_active_users()
            for user in active_users:
                user_dict[user.id] = user.first_name  + " " + user.last_name

            lead_mappings = user_da.get_all_employee_lead_mapping()
            job_title_mapping = user_da.get_all_job_titles()
            for each in lead_mappings:
                mapping_dict[each.emp_id] = each.lead_id
            for each in job_title_mapping:
                job_mapping_dict[each.id] = each.job_title

            employees, error = user_da.get_all_employees(include)

            if employees:
                for employee in employees:
                    employee_name = str(employee[1]).lower()
                    employee_job_status = str(employee[4])
                    employee_job_title = str(employee[3])
                    employee_id = int(employee[0])
                    employee_date_joined = employee[5]

                    if emp_name and not employee_name.startswith(emp_name.lower()):
                        continue
                    if job_status and job_status != employee_job_status:
                        continue
                    if job_title and job_title != employee_job_title:
                        continue
                    if reported_to and reported_to != mapping_dict[employee_id]:
                        continue
                    try:
                        emp_job_title = job_mapping_dict.get(int(employee_job_title))
                    except:
                        emp_job_title = 'None'
                        pass
                    try:
                        emp_job_status = EMPLOYMENT_STATUS.get(int(employee_job_status))
                    except:
                        emp_job_status = 'None'
                        pass

                    row = {
                        "user_id": employee_id,
                        "emp_name": f"{employee[1]} {employee[2]}",
                        "job_title": emp_job_title,
                        "employment_status": emp_job_status,
                        "supervisor": user_dict.get(mapping_dict.get(employee_id, 0), ''),
                        "date_joined":employee_date_joined,
                        "emp_id":employee[6],
                        "is_active":employee[7]
                    }
                    emp_list.append(row)
                    del row
                result['emp_list'] = emp_list
        except Exception as err:
            result["error"] = settings.ERROR_MSG['application_error']\
                .format(err, self.__logs.error(self.__exception.get_exception()))
        finally:
            return result


    def get_employee_list_filters(self, user_id):
        user_da = UserDA()
        result = {"error": None, "job_titles": [], "supervisors": [], "employment_status": []}
        employment_status = []
        supervisor_list = []
        job_title_list = []
        user_dict = {}
        try:
            permitted = self.__utility.is_permitted(user_id, 'view_employee_list')
            if not permitted:
                result["error"] = settings.ERROR_MSG.get('access_denied')
                return result

            job_titles = user_da.get_all_job_titles()
            for job_title in job_titles:
                job_title_list.append({"id": job_title.id, "title": job_title.job_title})
            result['job_titles'] = job_title_list

            for k, v in settings.EMPLOYMENT_STATUS.items():
                employment_status.append({"id": k, "status": v})
            result['employment_status'] = employment_status

            supervisors, error = user_da.get_all_supervisors()
            if supervisors:
                for supervisor in supervisors:
                    supervisor_list.append({"id": supervisor[0], "name": supervisor[1] + " " + supervisor[2]})
                result['supervisors'] = supervisor_list
        except Exception as err:
            result["error"] = settings.ERROR_MSG['application_error']\
                .format(err, self.__logs.error(self.__exception.get_exception()))
        finally:
            return result


    def get_create_new_user_dropdowns(self, user_id):
        user_da = UserDA()
        result = {
            "error": None,
            "organizations": [],
            "job_titles": [],
            "supervisors": [],
            "employment_status": [],
            "states":[],
            "districts": []
        }

        employment_status = []
        try:
            permitted = self.__utility.is_permitted(user_id, 'view_employee_list')
            if not permitted:
                result["error"] = settings.ERROR_MSG.get('access_denied')
                return result

            temp_list = []
            for k, v in settings.ORGANIZATION.items():
                temp_list.append({"id": k, "name": v})
            result['organizations'] = temp_list

            temp_list = []
            job_titles = user_da.get_all_job_titles()
            for job_title in job_titles:
                temp_list.append({"id": job_title.id, "title": job_title.job_title})
            result['job_titles'] = temp_list
            del temp_list

            temp_list = []
            for k, v in settings.EMPLOYMENT_STATUS.items():
                temp_list.append({"id": k, "status": v})
            result['employment_status'] = temp_list
            del temp_list

            supervisors, error = user_da.get_all_supervisors()
            if supervisors:
                temp_list = []
                for supervisor in supervisors:
                    temp_list.append({"id": supervisor[0], "name": supervisor[1] + " " + supervisor[2]})
                result['supervisors'] = temp_list
                del temp_list

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
            result["error"] = settings.ERROR_MSG['application_error']\
                .format(err, self.__logs.error(self.__exception.get_exception()))
        finally:
            return result

    def verify_employee_id(self, emp_id):
        user_da = UserDA()
        result = False
        query = user_da.get_verify_employee(emp_id)
        if not query:
            result = True
        return result

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

    def create_audit_log(self, request, status):
        email = request.data["email"]
        user = UserDA().get_user_by_email(email)
        log_dic = self.__utility.get_audit_logs_dict()
        log_dic['user_id'] = user.id
        log_dic['organization_id'] = UserDA().get_user_organization(user.id)
        if status==0:
            event = user.email
        else:
            event = user.username
        log_dic['event'] = "User Login"
        log_dic['event_details'] = settings.AUDIT_LOG_EVENT_DETAILS[status].format(event)
        LogsDA().create_audit_logs(log_dic)

    def save_employee_profile_changes(self, user_id, profile_changes):
        result = {"error": '', 'status': ''}
        edit_data_list = []
        editing_fields = []
        try:
            emp_id = profile_changes.get("emp_id", None)
            employee = UserDA().get_user_by_id(emp_id)

            if employee is None:
                result["error"] = "User does not exist ."
                result['status'] = 499
                return result
            role_id, role_name = UserDA().get_user_role_by_id(user_id)
            is_permitted = self.is_permmitted_to_edit(user_id,emp_id,role_id)
            if not is_permitted:
                result["error"] = settings.ERROR_MSG.get('access_denied')
                result['status'] = 403
                return result

            edited_fields = profile_changes.keys()

            if role_id == 2:
                UserManagementBL_V1().update_user_profile_changes(profile_changes)

            elif int(user_id) == int(emp_id):
                for each_key in edited_fields:
                    is_editable_field = self.is_editable_field(each_key)
                    if not is_editable_field:
                        result["error"] = "Invalid field"
                        result['status'] = 499
                        return result
                    field = ''
                    value = ''

                    if (each_key.upper() == "EMP_ID"):
                        continue

                    elif (each_key.upper() == "EMERGENCY_CONTACT"):
                        emergency_contact = profile_changes.get(each_key, None)
                        for edited_emergency_key in emergency_contact.keys():

                            is_editable_sub_node = self.is_editable_subnode(each_key,edited_emergency_key)
                            if not is_editable_sub_node:
                                result["error"] = "Invalid field"
                                result['status'] = 499
                                return result

                            field = edited_emergency_key
                            value = emergency_contact.get(edited_emergency_key, None)
                            user_profile_provisional_obj = UserDA().create_user_profile_provisional_object(user_id,emp_id,field,value)
                            edit_data_list.append(user_profile_provisional_obj)
                            editing_fields.append(field)


                    elif (each_key.upper() == "PERMANENT_ADDRESS"):
                        permanent_address = profile_changes.get(each_key, None)
                        permanent_address_keys = self.__clean_edited_profile_fields(permanent_address, each_key)
                        for edited_permanent_address_key in permanent_address_keys.keys():

                            is_editable_sub_node = self.is_editable_subnode(each_key,edited_permanent_address_key)
                            if not is_editable_sub_node:
                                result["error"] = "Invalid field"
                                result['status'] = 499
                                return result

                            field = self.__get_database_field_of_user_profile(edited_permanent_address_key,each_key)
                            if field:
                                value = permanent_address.get(edited_permanent_address_key, None)
                                user_profile_provisional_obj = UserDA().create_user_profile_provisional_object(user_id, emp_id, field, value)
                                edit_data_list.append(user_profile_provisional_obj)
                                editing_fields.append(field)



                    elif (each_key.upper() == "CURRENT_ADDRESS"):
                        current_address = profile_changes.get(each_key, None)
                        current_address_keys = self.__clean_edited_profile_fields(current_address, each_key)
                        for edited_current_address_key in current_address_keys.keys():

                            is_editable_sub_node = self.is_editable_subnode(each_key,edited_current_address_key)
                            if not is_editable_sub_node:
                                result["error"] = "Invalid field"
                                result['status'] = 499
                                return result

                            field = self.__get_database_field_of_user_profile(edited_current_address_key,each_key)
                            if field:
                                value = current_address.get(edited_current_address_key, None)
                                user_profile_provisional_obj = UserDA().create_user_profile_provisional_object(user_id, emp_id, field, value)
                                edit_data_list.append(user_profile_provisional_obj)
                                editing_fields.append(field)



                    else:
                        field = each_key
                        value = profile_changes.get(each_key, None)
                        user_profile_provisional_obj = UserDA().create_user_profile_provisional_object(user_id, emp_id, field, value)
                        edit_data_list.append(user_profile_provisional_obj)
                        editing_fields.append(field)
                with transaction.atomic():
                    UserDA().delete_user_profile_provisional_entries_field_list(emp_id,editing_fields)
                    UserDA().create_emp_profile_changes(edit_data_list)


            result['message'] = "Employee Profile Updated Successfully ."
            result['status'] = 200
        except Exception as err:
            result['status'] = 499
            result["error"] = settings.ERROR_MSG['application_error']\
                .format(err, self.__logs.error(self.__exception.get_exception()))
        return result


    def __clean_edited_profile_fields(self, edited_fields, node):
        if node.upper() == "PERMANENT_ADDRESS":
            entries_to_remove = ('provin_code', 'district', 'state' )
            for k in entries_to_remove:
                edited_fields.pop(k, None)
            return edited_fields
        if node.upper() == "CURRENT_ADDRESS":
            entries_to_remove = ('provin_code', 'district', 'state')
            for k in entries_to_remove:
                edited_fields.pop(k, None)
            return edited_fields



    def __get_database_field_of_user_profile(self, field, node):
        if node.upper() == "PERMANENT_ADDRESS":
            if field.upper() == "ADDRESS_1":
                return "permanent_address_1"
            if field.upper() == "ADDRESS_2":
                return "permanent_address_2"
            if field.upper() == "DISTRICTID":
                return "permanent_district_code"
            if field.upper() == "STATEID":
                return "permanent_provin_code"
            if field.upper() == "ZIPCODE":
                return "permanent_zipcode"
            if field.upper() == "CITY":
                return "permanent_city_code"

        if node.upper() == "CURRENT_ADDRESS":
            if field.upper() == "ADDRESS_1":
                return "address_1"
            if field.upper() == "ADDRESS_2":
                return "address_2"
            if field.upper() == "DISTRICTID":
                return "district_code"
            if field.upper() == "STATEID":
                return "provin_code"
            if field.upper() == "ZIPCODE":
                return "zipcode"
            if field.upper() == "CITY":
                return "city_code"



    def __get_active_emp_dict(self):
        emp_dict = {}
        users = UserDA().get_all_active_users()
        for user in users:
            emp_dict[user.id] = user
        return emp_dict

    def is_permmitted_to_edit(self, user_id, emp_id, role_id):
        permitted = False
        if int(user_id) == int(emp_id):
            permitted = True
            return permitted
        elif int(role_id) == 2:
            permitted = True
            return permitted
        return permitted

    def is_already_pending_profile_changes_exist(self, emp_id):
        exist = False
        pending_profile_change = UserDA().get_pending_profile_changes_by_emp_id(emp_id)

        if pending_profile_change:
            exist = True
            return exist
        return exist

    def __get_organization_by_org_id(self, organization_id):
        organization = ''
        if organization_id == 2:
            organization = 'Digitalmesh'
        else:
            organization = "EM Softech"
        return  organization

    def __get_profile_change_status(self, status):
        if status == 1:
            status_string = "Pending"
        elif status == 2:
            status_string = "Approved"
        else:
            status_string = "Rejected"
        return status_string

    def __get_image_url(self, user_id):
        try:
            img_url = UserDA().get_user_profile_by_id(user_id)
            if img_url:
                return f"{settings.DEFAULT_SITE_MEDIA_URL}{img_url.profile_photo}"
            else:
                return ""
        except:
            return ""

    def _format_permanant_adress(self, profile_changes):
        permanant_address = {}

        permanent_adress_dict = {"permanent_address_1": "address_1", "permanent_address_2": "address_2", "permanent_district_code": "districtId",
                                "permanent_provin_code": "stateId", "permanent_city_code": "city", "permanent_zipcode": "zipcode"}

        for each_change in profile_changes:
            if each_change.field in permanent_adress_dict.keys():
                permanant_address[permanent_adress_dict.get(each_change.field)] = each_change.value
                if each_change.field == "permanent_provin_code":
                    permanant_address['provin_code'] = each_change.value
                    permanant_address['state'] = settings.STATES.get(int(each_change.value), None)
                if each_change.field == "permanent_district_code":
                    permanant_address['district'] = settings.DISTRICTS.get(int(each_change.value), None)
        return permanant_address

    def _format_current_adress(self, profile_changes):
        current_address = {}

        current_adress_dict = {"address_1": "address_1", "address_2": "address_2", "district_code": "districtId",
                                "provin_code": "stateId", "city_code": "city", "zipcode": "zipcode"}

        for each_change in profile_changes:
            if each_change.field in current_adress_dict.keys():
                current_address[current_adress_dict.get(each_change.field)] = each_change.value
                if each_change.field == "provin_code":
                    current_address['provin_code'] = each_change.value
                    current_address['state'] = settings.STATES.get(int(each_change.value), None)
                if each_change.field == "district_code":
                    current_address['district'] = settings.DISTRICTS.get(int(each_change.value), None)
        return current_address

    def __format_profile_info_awaiting_approval(self, profile_changes):
        entries_to_remove = ["address_1", "address_2", "city_code", "provin_code",
        "district_code","zipcode","permanent_address_1","permanent_address_2",
        "permanent_city_code","permanent_coun_code","permanent_district_code",
        "permanent_provin_code","permanent_zipcode","name","mobile_no",
        "relationship","image","contact_person","phone_number"
         ]
        for k in entries_to_remove:
            profile_changes.pop(k, None)
        return profile_changes

    def __format_emergency_contact(self, profile_changes):
        emergency_contact = {}

        emergency_contact_dict = {"contact_person": "contact_person", "relationship": "relationship", "phone_number": "phone_number"}

        for each_change in profile_changes:
            if each_change.field in emergency_contact_dict.keys():
                emergency_contact[each_change.field] = each_change.value
        return emergency_contact


    def get_all_employee_details_waiting_action(self, user_id, is_mobile =0):
        result = {"error": '', "team_members": [], "status": 200}
        try:
            change_list = []
            role_id, role_name = UserDA().get_user_role_by_id(user_id)
            if role_id != 2:
                result["error"] = settings.ERROR_MSG.get('access_denied')
                result['status'] = 403
                return result
            status =1 # for pending approvals
            profile_changes = UserDA().get_all_profile_info_awaits_action(status)


            if profile_changes:
                emp_dict = self.__get_active_emp_dict()
                profile_changed_emp_list = []
                for profile_change in profile_changes:
                    temp = {}
                    employee = emp_dict.get(profile_change.emp_id, None)
                    if employee and employee.id not in profile_changed_emp_list:

                        profile_changed_emp_list.append(employee.id)

                        temp['emp_name'] = employee.first_name + \
                            " " + employee.last_name
                        temp['emp_id'] = employee.id
                        temp['emp_image'] =self.__get_image_url(employee.id)
                        # temp['profile_change_id'] = profile_change.id

                        change_list.append(temp)
                result['team_members'] = change_list

        except Exception as err:
            result['status'] = 499
            result["error"] = settings.ERROR_MSG['application_error']\
                .format(err, self.__logs.error(self.__exception.get_exception()))
        return result

    def get_employee_profile_info_waiting_action(self,user_id, emp_id, is_mobile=0 ):
        result = {"error": '', "status": 200}
        try:

            change_in_profile_info = UserDA().get_employee_profile_change_by_emp_id_and_status(emp_id)
            if change_in_profile_info:
                is_permitted = self.is_permitted_to_view_pending_profile_changes(user_id, change_in_profile_info)
                if not is_permitted:
                    result["error"] = settings.ERROR_MSG.get('access_denied')
                    result['status'] = 403
                    return result


                for each_change in change_in_profile_info:
                    if each_change.field == "emp_image":

                        profile_image_url = self.get_pending_profile_image_change_url(each_change.value)
                        result['emp_image'] = profile_image_url
                    else:
                        result[each_change.field] = each_change.value

                permanent_adress = self._format_permanant_adress(change_in_profile_info)
                if permanent_adress:
                    result['permanent_address'] = permanent_adress

                current_adress = self._format_current_adress(change_in_profile_info)
                if current_adress:
                    result['current_address'] = current_adress

                emergency_contact = self.__format_emergency_contact(change_in_profile_info)
                if emergency_contact:
                    result['emergency_contact'] = emergency_contact

                result = self.__format_profile_info_awaiting_approval(result)
            else:
                result["error"] ="No changes found."
                result['status'] = 499
                return result


        except Exception as err:
            result['status'] = 499
            result["error"] = settings.ERROR_MSG['application_error']\
                .format(err, self.__logs.error(self.__exception.get_exception()))
        return result

    def apply_action_on_profile_changes(self, user_id, request):
        result = {}

        try:
            emp_id = request.get("emp_id", None)
            action = request.get("action", None)
            field = request.get("field", None)


            if (action.upper() == "CANCELLED" and emp_id == user_id):
                pass
            else:
                role_id, role_name = UserDA().get_user_role_by_id(user_id)
                if role_id != 2:
                    result["error"] = settings.ERROR_MSG.get('access_denied')
                    result['status'] = 403
                    return result


            update_data = {}
            action = action.upper()
            employee =  UserDA().get_user_by_id(emp_id)

            change_in_profile_info = UserDA().get_employee_profile_change_by_emp_id_and_status_and_field(emp_id, field)



            if employee and action and change_in_profile_info:
                if action == "APPROVED":

                    update_data['status'] = 2 #for approve

                    auth_user_edit_data = self._format_auth_user_update_data(change_in_profile_info)

                    user_profile_edit_data = self._format_user_profile_update_data(change_in_profile_info)

                    emergency_details_edit_data = self._format_emergency_contact_update_data(change_in_profile_info)


                    with transaction.atomic():
                        if auth_user_edit_data:
                            UserDA().update_auth_user(auth_user_edit_data, emp_id)
                        if user_profile_edit_data:
                            UserDA().update_user_profile(emp_id, user_profile_edit_data )
                        if emergency_details_edit_data:
                            UserDA().update_emergency_contact( emergency_details_edit_data, emp_id)
                        if "profile_photo" in user_profile_edit_data.keys():
                            self.replace_old_profile_image_with_new(user_profile_edit_data['profile_photo'], emp_id)

                    UserDA().delete_user_profile_provisional_entries(emp_id,field)

                if action == "REJECTED":
                    UserDA().delete_user_profile_provisional_entries(emp_id,field)

                if action == "CANCELLED":
                    UserDA().delete_user_profile_provisional_entries(emp_id,field)
                result['message'] = "Changes applied"
            else:
                result['message'] = "Nothing to Change"
        except Exception as err:
            result['status'] = 499
            result["error"] = settings.ERROR_MSG['application_error']\
                .format(err, self.__logs.error(self.__exception.get_exception()))
        return result

    def _format_auth_user_update_data(self, profile_changes):

        auth_user_update_data = {}
        editable_fields = ['first_name', 'last_name']
        for profile_change in profile_changes:
            if profile_change.field in editable_fields:
                auth_user_update_data[profile_change.field] = profile_change.value
        return auth_user_update_data

    def _format_emergency_contact_update_data(self, profile_changes):

        emergency_contact_update_data = {}
        editable_fields = ['contact_person', 'relationship', 'phone_number']
        for profile_change in profile_changes:

            if profile_change.field in editable_fields:
                if profile_change.field == "contact_person":
                    emergency_contact_update_data["name"] = profile_change.value
                elif profile_change.field == "phone_number":
                    emergency_contact_update_data["mobile_no"] = profile_change.value
                else:
                    emergency_contact_update_data[profile_change.field] = profile_change.value
                emergency_contact_update_data['emp_id'] = profile_change.emp_id
        return emergency_contact_update_data

    def _format_user_profile_update_data(self, profile_changes):
        user_profile_update_data = {}

        fields_to_remove = ['contact_person', 'relationship', 'phone_number','first_name', 'last_name']
        for profile_change  in profile_changes:
            if profile_change.field  not in fields_to_remove:
                if profile_change.field == "emp_image":
                    user_profile_update_data['profile_photo'] = profile_change.value
                else:
                    user_profile_update_data[profile_change.field] = profile_change.value

        return user_profile_update_data

    def get_pending_profile_image_change_url(self, image_name):
        try:
            return f"{settings.PROFILE_IMAGE_PROVISIONAL}/{image_name}"
        except:
            return ""

    def replace_old_profile_image_with_new(self, new_image, emp_id):

        user_profile = UserDA().get_user_profile_by_id(emp_id)
        try:
            try:
                self.__file_manager.delete_file(f'{settings.MEDIA_ROOT}employee_profile_photo/{user_profile.profile_photo}')
            except:
                pass
            
            provisional_path = f'{settings.MEDIA_ROOT}confidential_docs/profile_image_provisional/{new_image}'
            image_data = self.__file_manager.read_file(provisional_path)
            
            if image_data:
                target_path = f"{settings.MEDIA_ROOT}employee_profile_photo/{new_image}"
                self.__file_manager.upload_file(target_path, image_data)
                
            self.__file_manager.delete_file(provisional_path)

        except Exception as err:
            settings.ERROR_MSG['application_error']\
                .format(err, self.__logs.error(self.__exception.get_exception()))

    def pending_profile_field_change(self, emp_id, field):
        profile_change = UserDA().get_pending_profile_field_change(emp_id, field)
        return profile_change


    def is_permitted_to_view_pending_profile_changes(self, user_id, pending_change_obj):
        permitted = False
        role_id, role_name = UserDA().get_user_role_by_id(user_id)
        if role_id == 2:
            permitted = True
            return permitted
        if pending_change_obj[0].emp_id == user_id:
            permitted = True
            return permitted

        return permitted

    def is_editable_field(self, field):
        permitted = True
        fields_updatable = ['emp_id', 'company_id', 'first_name', 'last_name', 'dob', 'gender', 'marital_status', 'job_status_id', 'job_title_id', 'marital_status',
                            'current_address', 'permanent_address', 'home_telephone', 'mobile', 'personal_email', 'blood_group', 'emergency_contact']
        if field not in fields_updatable:
            permitted = False
        return permitted

    def is_editable_subnode(self, node, subnode):

        is_editable = False

        permanent_adreess_nodes = ['address_1', 'address_2', 'provin_code', 'districtId', 'city', 'stateId', 'zipcode']

        current_address_nodes = ['address_1', 'address_2', 'provin_code', 'districtId', 'city', 'stateId', 'zipcode']

        emergency_contact_nodes = ['contact_person', 'relationship', 'phone_number']

        if node.upper() == "PERMANENT_ADDRESS":
            if subnode  in permanent_adreess_nodes:
                is_editable = True

        if node.upper() == "CURRENT_ADDRESS":
            if subnode  in current_address_nodes:
                is_editable = True

        if node.upper() == "EMERGENCY_CONTACT":
            if subnode  in emergency_contact_nodes:
                is_editable = True

        return is_editable









