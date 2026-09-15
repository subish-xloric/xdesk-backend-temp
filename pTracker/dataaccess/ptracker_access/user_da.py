
from  datetime import datetime, date, timedelta
from datetime import date
from types import SimpleNamespace

from django.conf import settings
from django.db.models import query
from django.db.models import Q

from django.contrib.auth.models import User
from django.contrib.auth.models import Group
from django.contrib.auth.models import Permission

from pTracker.dataaccess.ptracker_access.time_sheet_models import TimeSheet
from pTracker.dataaccess.ptracker_access.time_sheet_models import TimeSheetActionLog
from pTracker.dataaccess.ptracker_access.time_sheet_models import TimeSheetItem
from pTracker.dataaccess.ptracker_access.user_models import EmpLeadMappingLog, EncryptedMobileData
from pTracker.dataaccess.ptracker_access.user_models import MobileDevices
from pTracker.dataaccess.ptracker_access.user_models import UsedBirthdayImage
from pTracker.dataaccess.ptracker_access.user_models import ResetPasswordModel
from pTracker.dataaccess.ptracker_access.user_models import EmployeeLeadMapping
from pTracker.dataaccess.ptracker_access.user_models import EmployeeJobTitle
from pTracker.dataaccess.ptracker_access.user_models import UserProfile
from pTracker.dataaccess.ptracker_access.user_models import EmployeeEmergencyContacts
from pTracker.dataaccess.ptracker_access.user_models import UserProfileProvisional
from pTracker.dataaccess.ptracker_access.user_models import AuthBiometric
from pTracker.dataaccess.ptracker_access.user_models import TimesheetExcludedEmployees
from pTracker.dataaccess.ptracker_access.user_models import EmployeeJobTitle
from pTracker.dataaccess.ptracker_access.user_models import DeactivatedEmployee

from pTracker.common.exception_handler import ExceptionHandler
from pTracker.common.logs import Logs

from pTracker.dataaccess.db import Connection

from io import BytesIO
import os

from PIL import Image

def new_dto():
    dto = SimpleNamespace()
    return dto

class UserDA():

    def __init__(self):
        self.__log = Logs()
        self.__exception = ExceptionHandler()



    def get_user_mail_from_user_id(self, user_id):
        user_mail = None
        try:
            user_profile = User.objects.filter(id=user_id).first()
            user_mail = user_profile.email
        except Exception as err:
            self.__log.error(self.__exception.get_exception())
        return user_mail


    def get_employee_designation(self, user_id):
        try:
            user_profile = UserProfile.objects.filter(user_id=user_id).first()
            job_title_id = user_profile.job_title
            job_designation = EmployeeJobTitle.objects.filter(id=job_title_id).first().job_title
        except Exception as e:
            job_designation = None
        return job_designation
    
    
    def get_name_address_pan_from_user_id(self, user_id):
        try:
            user = User.objects.filter(id=user_id).first()
            user_profile = UserProfile.objects.filter(user_id=user_id).first()
            name = user.first_name + " " + user.last_name
            address = f"{user_profile.address_1}\n{user_profile.address_2}\n{user_profile.city_code}"
            pan = user_profile.pan
            gender = user_profile.gender
            father_name = user_profile.father_name
        except Exception as e:
            name = None
            address = None
            pan = None
            father_name = None
        return name, address, pan, gender,father_name 
    
    # def get_permanent_account_number_from_user_id(self, user_id):
    #     try:
    #         permanent_account_number = 1
    #     except:
    #         permanent_account_number = None
    #     return permanent_account_number
    
    def check_user_id_is_valid(self, user_id):
        return User.objects.filter(id=user_id)

    def get_all_users(self):
        return User.objects.all()

    def get_all_active_users(self):
        try:
            user = User.objects.filter(is_active=1).order_by('first_name')
        except:
            user = None
        return user
    
    def get_all_non_active_users(self):
        try:
            user = User.objects.filter(is_active=0).order_by('first_name')
        except:
            user = None
        return user

    def get_user_by_id(self, user_id):
        try:
            user = User.objects.get(id=user_id)
        except:
            user = None
        return user
    

    def get_user_mails_from_user_ids(self, user_ids):
        try:
            active_users = User.objects.filter(is_active=1, id__in=user_ids)
            user_mail_list = [user.email for user in active_users]
        except Exception as e:
            user_mail_list = None
        return user_mail_list

    def get_is_taxable_from_user_id(self, user_id):
        try:
            user_profile = UserProfile.objects.filter(user_id=user_id)
        except:
            user_profile = None
        return user_profile[0]

    def get_user_role_by_id(self, user_id):
        try:
            role_id = ''
            role_name = ''
            user = User.objects.get(id=user_id)
            a = user.groups.all()
            role_name = a[0].name
            role_id = a[0].id
        except:
            role_id = ''
            role_name = ''
        return role_id, role_name

    def get_current_team_members_by_lead_id(self, user_id=0):
        try:
            team_list = []
            team_member_list = []
            if user_id:
                team_users = EmployeeLeadMapping.objects.filter(lead_id=user_id, is_deleted=0)
            else:
                team_users = EmployeeLeadMapping.objects.filter(is_deleted=0)
            if team_users:
                for each_item in team_users:
                    team_list.append(each_item.emp_id)

            if team_list:
                team_list = list(set(team_list))
                users = User.objects.filter(is_active=1).order_by('first_name')
                for user in users:
                    if user.id in team_list:
                        team_member_list.append(user)
        except Exception as err:
            team_member_list = []
        return team_member_list


    def get_my_lead(self, user_id):
        lead_user = EmployeeLeadMapping.objects.filter(emp_id=user_id, is_deleted=0)
        if lead_user:
            lead_user = lead_user[0]
        else:
            lead_user = None
        return lead_user

    def get_lead_id_by_user(self, user_id):
        lead_user = EmployeeLeadMapping.objects.filter(emp_id=user_id, is_deleted=0)
        try:
            lead_id = lead_user[0].lead_id
        except:
            lead_id = 0
        return lead_id

    def is_team_member(self, user_id, lead_id):
        try:
            is_member = False
            team_user = EmployeeLeadMapping.objects.filter(lead_id=lead_id, emp_id=user_id, is_deleted=0)
            if team_user:
                is_member = True
                return is_member
            else:
                role_id, role_name = self.get_user_role_by_id(lead_id)
                if role_id in (1, 2, 3):
                    is_member = True
                    return is_member
        except:
            is_member = False
        return is_member


    def get_current_team_members_by_emp_id(self, emp_id):
        try:
            team_list = []
            team_member_list = []
            lead_id = 0
            lead_users = EmployeeLeadMapping.objects.filter(emp_id=emp_id, is_deleted=0)
            if lead_users:
                lead_id = lead_users[0].lead_id

            team_users = EmployeeLeadMapping.objects.filter(lead_id=lead_id, is_deleted=0)
            team_list.append(lead_id)
            if team_users:
                for each_item in team_users:
                    if int(each_item.emp_id) != emp_id:
                        team_list.append(each_item.emp_id)
            if team_list:
                users = User.objects.filter(is_active=1).order_by('first_name')
                for user in users:
                    if user.id in team_list:
                        team_member_list.append(user)
        except Exception as err:
            team_member_list = []
        return team_member_list

    def get_user_profile_by_id(self, user_id):
        try:
            user = UserProfile.objects.get(user_id=int(user_id))
        except Exception as err:
            user = None
        return user

    def get_user_by_email(self, email):
        try:
            user = User.objects.filter(email=email, is_active=1).first()
        except:
            user = None
        return user

    def get_emergency_contacts_by_id(self, user_id):
        try:
            user = EmployeeEmergencyContacts.objects.get(emp_id=int(user_id))
        except Exception as err:
            user = None
        return user
    # def get_employee_work_anniversaries(self, days):
    #     # query = User.objects.filter(date_joined__gte=start_date, date_joined__lte=end_date, is_active=1)
    #     # print(query.query)
    #     # days = []
    #     work_anniversaries = []
    #     # while True:
    #     #     if start_date <= end_date:
    #     #         days.append(start_date)
    #     #     else:
    #     #         start_date = start_date + datetime.timedelta(days=1)
    #     #         if start_date > end_date:
    #     #             break

    #     for d in days:
    #         for p in User.objects.filter(date_joined__month=d.month, date_joined__day=d.day, is_active=1):
    #             work_anniversaries.append(p)
    #             print(p.query)
    #     return work_anniversaries


    def get_current_day_work_anniversary(self, date):
        work_anniversaries = []
        query = f"""select first_name,last_name,id,email,date_joined from auth_user
                where DAY(date_joined)={date.day}
                AND MONTH(date_joined)={date.month} AND is_active=1"""
        for p in User.objects.raw(query):
            work_anniversaries.append(p)
        return work_anniversaries

    def get_user_group(self, group_id):
        group = Group.objects.get(id=group_id)
        return group

    def create_user(self, data):
        try:
            user = User.objects.create_user(
                password = data.password,
                username = data.username,
                first_name = data.first_name,
                last_name = data.last_name,
                email = data.email,
                date_joined = data.date_joined,
                is_staff = 0,
                is_active = 1,
                is_superuser = 0)
            group = self.get_user_group(data.group_id)
            user.groups.add(group)
        except Exception as err:
            user = None
        return user

    def update_auth_user(self, auth_data, user_id):
        User.objects.filter(id = user_id).update(**auth_data)
        return User.objects.get(id = user_id)

    def create_employee_lead_mapping(self, emp_id, lead_id, from_date):
        obj = EmployeeLeadMapping(
            emp_id=emp_id,
            lead_id=lead_id,
            from_date=from_date)
        obj.save()
        return obj

    def update_employee_lead_mapping(self, emp_id, lead_id):
        EmployeeLeadMapping.objects.filter(emp_id = emp_id).update(lead_id = lead_id)

    def create_user_profile(self, profile_data):
        return UserProfile.objects.create(**profile_data)

    def create_emergency_contacts(self, data):
        return EmployeeEmergencyContacts.objects.create(**data)

    # def update_user_profile(self, profile_data):
    #     user_id= profile_data['user_id']
    #     UserProfile.objects.filter(user_id = int(user_id)).update(**profile_data)
    #     return UserProfile.objects.get(user_id = int(user_id))

    def update_emergency_contact(self, data, user_id):
        emergency = EmployeeEmergencyContacts.objects.filter(emp_id= user_id)
        if emergency:
            emergency.update(**data)
        else:
            EmployeeEmergencyContacts.objects.create(**data).save()

    def get_current_date_birthdays(self, date):
        birthdays = []
        query = f"""SELECT
        user_profile.dob,
        auth_user.first_name,
        auth_user.last_name,
        auth_user.email,
        user_profile.company_id,
        auth_user.id
        FROM user_profile
        inner join auth_user on(auth_user.id=user_profile.user_id)
        where day(dob)={date.day} and month(dob)={date.month} and auth_user.is_active=1"""

        conn = Connection('default')
        return  conn.execute(query)


    def get_upcoming_birthdays(self, date_range):
        birthdays = []
        for days in date_range:
            query = f"""select
                            user_profile.dob,
                            auth_user.first_name,
                            auth_user.last_name,
                            auth_user.id
                        from
                            user_profile
                        inner join
                            auth_user on(auth_user.id=user_profile.user_id)
                        where
                            day(dob)={days.day} and
                            month(dob)={days.month} and
                            auth_user.is_active=1"""
            conn = Connection('default')
            results, error = conn.execute(query)
            if results:
                birthdays.append(results)
            if error:
                results = None
                #Utility().log(error)
        return birthdays

    def get_all_used_images(self, max_number):
        send_images = UsedBirthdayImage.objects.all()
        if send_images:
            if len(send_images) >= max_number:
                send_images.delete()
                send_images = None
        return send_images

    def get_all_employee_lead_mapping(self):
        return EmployeeLeadMapping.objects.filter(is_deleted=0)

    def get_all_job_titles(self):
        return EmployeeJobTitle.objects.filter(is_deleted=0).order_by('job_title')

    def get_all_employees(self, is_active):
        if is_active == -1:
            where_clause = ''
        else:
            where_clause = """WHERE auth_user.is_active = {0} """.format(is_active)
        query = f"""SELECT
        auth_user.id,
        auth_user.first_name,
        auth_user.last_name,
        user_profile.job_title,
        user_profile.job_status,
        DATE(auth_user.date_joined),
        auth_user.username,
        auth_user.is_active
        FROM auth_user
        LEFT JOIN user_profile ON auth_user.id=user_profile.user_id {where_clause}
        order by auth_user.first_name;"""

        conn = Connection("default")
        return conn.execute(query)

    def get_all_supervisors(self):
        query = f"""SELECT DISTINCT
        auth_user.id,
        auth_user.first_name,
        auth_user.last_name
        FROM emp_lead_mapping
        JOIN auth_user ON(emp_lead_mapping.lead_id=auth_user.id)
        WHERE auth_user.is_active=1
        order by auth_user.first_name"""
        conn = Connection("default")
        return conn.execute(query)

    def get_group_permission(self, user_id, permission_code):
        permission = None
        group_id, role_name = self.get_user_role_by_id(user_id)
        if group_id:
            permission = Permission.objects.filter(group__id=group_id, codename=permission_code)
        return permission

    def get_user_permission(self, user_id, permission_code):
        permission = None
        permission = Permission.objects.filter(user__id=user_id, codename=permission_code)
        return permission

    def get_user_by_emp_id(self,emp_id):
        try:
            user=User.objects.get(username=emp_id)
        except:
            user=None
        return user


    def get_verify_employee(self, emp_id):
        return User.objects.filter(username=str(emp_id))

    def get_all_user_profiles(self):
        return UserProfile.objects.all()


    def get_all_supervisors_for_leave(self):
        query = ''' SELECT DISTINCT auth_user.id, auth_user.first_name,auth_user.last_name
                    FROM auth_user_groups
                    join auth_user on auth_user.id=auth_user_groups.user_id
                    where group_id != 5 and is_active=1 order by auth_user.first_name'''
        conn = Connection("default")
        return conn.execute(query)

    def get_user_organization(self,user_id):
        user_profile = UserProfile.objects.get(user_id = user_id)
        return user_profile.company_id
    
    
    def get_user_data_by_emp_id(self,emp_id):
        user = None
        try:
            user = User.objects.get(id=emp_id)
        except Exception as e:
            print(e)
        return user
    

    # def get_user_organization_logo(self, organization):
    #     logo_images = BytesIO()
    #     if organization == 2:
    #         logo = Image.open(os.path.join(
    #         settings.MEDIA_ROOT, f'logo/DMlogo.png'))
    #         logo.save(logo_images, format='png')
    #     else:
    #         logo = Image.open(os.path.join(
    #         settings.MEDIA_ROOT, f'logo/EMlogo.png'))
    #         logo.save(logo_images, format='png')
    #     return logo_images

    def get_all_mapped_employess(self):
        return EmployeeLeadMapping.objects.filter(is_deleted =0)

    def get_reset_token(self, email):
        try:
            return ResetPasswordModel.objects.filter(email=email).latest('id')
        except:
            return None

    def create_reset_password_token(self, data):
        return ResetPasswordModel.objects.create(**data)

    def get_reset_token_by_user_id(self, user_id, token):
        try:
            return ResetPasswordModel.objects.filter(req_code=token,\
                user_id=user_id).latest('id')
        except:
            return None

    def reset_user_password(self, user_id, password, token_id):
        try:
            user = User.objects.get(id=user_id)
            user.set_password(password)
            user.save()
            token_obj = ResetPasswordModel.objects.get(id=token_id)
            token_obj.deleted = True
            token_obj.save()
            return user
        except:
            return None

    def update_employee_lead_mapping_v2(self, employee_id, lead_id, data):
        mapping_obj = EmployeeLeadMapping.objects.filter(lead_id=lead_id, emp_id=employee_id, is_deleted=0)
        mapping_obj.update(**data)
        return mapping_obj

    def create_emp_lead_mapping_log(self, data):
        return EmpLeadMappingLog.objects.create(**data)

    def get_emp_lead_mapping_by_emp_id_and_lead_id(self,emp_id,lead_id):
        try:
            return EmployeeLeadMapping.objects.get(lead_id=lead_id, emp_id=emp_id, is_deleted=0)
        except Exception as err:
            return None

    def get_job_title_by_id(self, title_id):
        return EmployeeJobTitle.objects.get(id = title_id)

    def create_encrypted_mobile_data(self, encrpted="", token = ""):
        return EncryptedMobileData.objects.create(encrypted_text=encrpted, token_id=token)

    def get_encrypted_mobile_date(self, token):
        try:
            return EncryptedMobileData.objects.get(token_id=token)
        except:
            return None

    def create_or_update_mobile_common_headers(self, user_id, data):
        try:
            if data.get("device_identifier"):
                MobileDevices.objects.filter(device_identifier=data.get("device_identifier")).update(**{"device_identifier":""})
            headers = MobileDevices.objects.filter(user_id=user_id).update(**data)
            if not headers:
                headers = MobileDevices.objects.create(**data)
            return headers
        except Exception as err:
            return None

    def get_mobile_device_info_by_user_id(self, user_id):
        try:
            return MobileDevices.objects.get(user_id = user_id)
        except:
            return None

    def get_all_employees_by_doj(self, doj):
        return User.objects.filter(date_joined__lte=doj, is_active=1)

    def get_all_leads(self):
        qry = '''SELECT first_name,last_name,user_id FROM auth_user_groups
                join auth_user on auth_user.id = auth_user_groups.user_id
                where group_id != 5 and is_active =1 order by first_name'''
        conn = Connection("default")
        return conn.execute(qry)

    def get_all_managers(self):
        qry = '''SELECT first_name,last_name,user_id FROM auth_user_groups
                join auth_user on auth_user.id = auth_user_groups.user_id
                where group_id != 5 and group_id !=4  and is_active =1 order by first_name'''
        conn = Connection("default")
        return conn.execute(qry)

    def get_all_user_group_id(self):
        qry = '''SELECT user_id,group_id FROM auth_user_groups
                join auth_user on auth_user.id = auth_user_groups.user_id
                where is_active =1'''
        conn = Connection("default")
        return conn.execute(qry)

    def get_users_with_group_id(self):
        user_with_groups = {}
        user_groups, err = self.get_all_user_group_id()
        for each in user_groups:
            user_with_groups[each[0]] = each[1]
        return user_with_groups

    def get_emp_lead_mapping_by_emp_id(self, emp_id):
        return EmployeeLeadMapping.objects.filter(emp_id = emp_id, is_deleted = 1)


    def delete_lead_mapping_by_employee_id(self, user_id):

        return EmployeeLeadMapping.objects.filter(Q(emp_id = user_id)|Q(lead_id = user_id)).update(is_deleted = 1,to_date = datetime.now().date())

    def update_user_profile(self, user_id, data):
        UserProfile.objects.filter(user_id = user_id).update(**data)
        return  UserProfile.objects.get(user_id = user_id)

    def create_emp_lead_mapping_relieving_log(self, lead_mappings):
        data_list = []
        date = datetime.now().date().strftime("%d/%m/%Y")
        for each in lead_mappings:
            data_list.append(EmpLeadMappingLog(mapping_id = each.id,
            emp_id = each.emp_id,
            lead_id = each.lead_id,
            action = f"Relieved from the firm on {date}"
            ))
        return EmpLeadMappingLog.objects.bulk_create(data_list)

    def get_user_group_mapping_by_group_id(self, group_id):
        qry = '''SELECT user_id FROM auth_user_groups
                join auth_user on auth_user.id = auth_user_groups.user_id
                where auth_user.is_active =1 AND auth_user_groups.group_id={0} '''.format(group_id)
        conn = Connection("default")
        return conn.execute(qry)

    def get_all_inactive_users(self):
        return User.objects.filter(is_active=0)

    def get_pending_profile_changes_by_emp_id(self, emp_id):

        # status = 1 for pendig profile edits
        return UserProfileProvisional.objects.filter(emp_id=emp_id, status=1)

    def create_emp_profile_changes(self, emp_edit_data):
        return UserProfileProvisional.objects.bulk_create(emp_edit_data)

    def get_all_profile_info_awaits_action(self, status=1):
        return UserProfileProvisional.objects.filter(status=status)

    def get_employee_profile_change_by_emp_id_and_status(self, emp_id, status=1):
        return UserProfileProvisional.objects.filter(status= status, emp_id = emp_id)

    def update_user_profile_provisional(self, update_data, emp_id, field):

        status = 1 # pending changes status

        nodes = ['current_address', 'permanent_address', 'emergency_contact']
        if field in nodes:
            if field == "permanent_address":
                field_list = ["permanent_address_1","permanent_address_2",
                "permanent_city_code","permanent_coun_code","permanent_district_code",
                "permanent_zipcode"]

            if field == "current_address":
                field_list = ["address_1","address_2",
                "city_code","coun_code","district_code","zipcode"]

            if field == "emergency_contact":
                    field_list = ["contact_person","relationship",
                                "phone_number"]
            return UserProfileProvisional.objects.filter(status= status, emp_id = emp_id, field__in= field_list).update(**update_data)
        return UserProfileProvisional.objects.filter(status= status, emp_id = emp_id, field = field).update(**update_data)


    def create_or_update_auth_biometric_authentication(self, data):
        device_identifier = data.get('keyIdentifier', 0)
        email = data.get('email', 0)
        obj = None
        obj = AuthBiometric.objects.filter(keyIdentifier=device_identifier)
        new_obj = obj.filter(email=email)
        if new_obj and obj:
            obj = new_obj.update(**data)
        elif obj:
            obj = obj.delete()
            obj = AuthBiometric.objects.create(**data)
        else:
            obj = AuthBiometric.objects.create(**data)
        return obj

    def get_biometric_data_by_keyidentifier(self, identifier):
        return AuthBiometric.objects.filter(keyIdentifier=identifier).first()

    def create_user_profile_provisional_object(self,user_id, emp_id, field, value):
        return UserProfileProvisional(emp_id = emp_id,
                field = field,
                value = value,
                status = 1, # for pending
                created_by = user_id,
                created_date_time = datetime.now()
                )

    def get_employee_profile_change_by_emp_id_and_status_and_field(self, emp_id, field, status=1):

        nodes = ['current_address', 'permanent_address', 'emergency_contact', 'emp_name',
                 'emergency_contact.contact_person', 'emergency_contact.relationship', 'emergency_contact.phone_number']
        if field in nodes:
            if field == "permanent_address":
                field_list = ["permanent_address_1","permanent_address_2",
                "permanent_city_code","permanent_coun_code","permanent_district_code",
                "permanent_zipcode","permanent_provin_code"]

            if field == "current_address":
                field_list = ["address_1","address_2",
                "city_code","coun_code","district_code","zipcode","provin_code"]

            if field == "emergency_contact":
                    field_list = ["contact_person","relationship",
                                "phone_number"]
            if field == "emp_name":
                 field_list = ["first_name","last_name"]

            if field == "emergency_contact.relationship":
                field_list = ["relationship"]

            if field == "emergency_contact.phone_number":
                field_list = ["phone_number"]

            if field == "emergency_contact.contact_person":
                field_list = ["contact_person"]


            return UserProfileProvisional.objects.filter(status= status, emp_id = emp_id,field__in = field_list)
        else:
            return UserProfileProvisional.objects.filter(status= status, emp_id = emp_id,field = field)

    def delete_user_profile_provisional_entries(self, emp_id, field, status=1):

        nodes = ['current_address', 'permanent_address', 'emergency_contact',
                 "emp_name",'emergency_contact.contact_person', 'emergency_contact.relationship', 'emergency_contact.phone_number']
        if field in nodes:
            if field == "permanent_address":
                field_list = ["permanent_address_1","permanent_address_2",
                "permanent_city_code","permanent_coun_code","permanent_district_code",
                "permanent_zipcode","permanent_provin_code"]

            if field == "current_address":
                field_list = ["address_1","address_2",
                "city_code","coun_code","district_code","zipcode","provin_code"]

            if field == "emergency_contact":
                    field_list = ["contact_person","relationship",
                                "phone_number"]
            if field == "emp_name":
                field_list = ['first_name', 'last_name']

            if field == "emergency_contact.relationship":
                    field_list = ["relationship"]

            if field == "emergency_contact.phone_number":
                field_list = ["phone_number"]

            if field == "emergency_contact.contact_person":
                field_list = ["contact_person"]

            return UserProfileProvisional.objects.filter(status= status, emp_id = emp_id,field__in = field_list).delete()
        else:
            return UserProfileProvisional.objects.filter(status= status, emp_id = emp_id,field = field).delete()

    def get_pending_profile_field_change(self, emp_id, field, status =1):

        nodes = ['current_address', 'permanent_address', 'emergency_contact']
        if field in nodes:
            if field == "permanent_address":
                field_list = ["permanent_address_1","permanent_address_2",
                "permanent_city_code","permanent_coun_code","permanent_district_code",
                "permanent_zipcode"]

            if field == "current_address":
                field_list = ["address_1","address_2",
                "city_code","coun_code","district_code","zipcode"]

            if field == "emergency_contact":
                    field_list = ["contact_person","relationship",
                                "phone_number"]
            return UserProfileProvisional.objects.filter(status= status, emp_id = emp_id,field__in = field_list)
        else:
            return UserProfileProvisional.objects.filter(status= status, emp_id = emp_id,field = field)

    def get_email_by_id_list(self, ids=[]):
        return User.objects.filter(id__in=ids).values_list('email', flat=True)


    def delete_user_profile_provisional_entries_field_list(self, emp_id, fields, status=1):
        return UserProfileProvisional.objects.filter(status= status, emp_id = emp_id,field__in = fields).delete()


    def get_employee_lead_mapping_by_emp_id(self, emp_id):
        mapping = EmployeeLeadMapping.objects.filter(is_deleted=0,emp_id=emp_id)
        if mapping :
            return mapping[0]

    def get_timesheet_excluded_employee_by_id(self, emp_id):
        current_date = date.today()
        objs = TimesheetExcludedEmployees.objects.filter(emp_id=emp_id, expiry_date__gte=current_date)
        if objs:
            return objs[0]
        return None


    def get_user_name_by_id(self, userID):
        if type(userID) == list:
            return User.objects.filter(id__in=userID)
        else:
             return User.objects.filter(id=userID).first()

    def get_user_id_by_secret_key(self, secret_key):
        try:
            user = UserProfile.objects.get(secret_key=secret_key)
            if user:
                user = user.user_id
        except:
            user = None
        return user

    def get_user_id_by_api_token(self, api_token):
        """
        Looks up the user_id associated with the given API token in user_profile.

        Used by ApiTokenAuthentication to resolve an incoming bearer token to
        a concrete user identity. Returns the integer user_id on success, or
        None if no matching active token is found.

        Args:
            api_token (str): The raw token string from the Authorization header.

        Returns:
            int | None: The user_id if a matching token exists, otherwise None.
        """
        try:
            profile = UserProfile.objects.get(api_token=api_token)
            return profile.user_id
        except Exception:
            return None

    def save_api_token(self, user_id, api_token):
        """
        Persists a newly generated API token for the given user in user_profile.

        Called by the token-generation endpoint after producing a fresh UUID token.
        Overwrites any previously stored token for this user, effectively
        invalidating all prior integrations using the old token.

        Args:
            user_id (int): The user whose token should be updated.
            api_token (str): The new token string to store.

        Returns:
            bool: True if the update succeeded, False on any database error.
        """
        try:
            UserProfile.objects.filter(user_id=user_id).update(api_token=api_token)
            return True
        except Exception:
            self.__log.error(self.__exception.get_exception())
            return False

    def get_emps_with_role(self, group_ids="2,3,4"):
        lead_ids = []
        query = """select id,user_id,group_id from auth_user_groups where group_id in ({0}) """.format(group_ids)
        #print("query", query)
        conn = Connection('default')
        results, error = conn.execute(query)
        #print('errr', error)
        if results:
            for each in results:
                lead_ids.append(int(each[1]))
        return lead_ids

    def get_user_profiles_by_employee_ids(self, emp_ids=[0], job_status=0):
        result = UserProfile.objects.filter(user_id__in=emp_ids)
        if job_status:
            result = result.filter(job_status=job_status)
        return result
    
    
    def get_user_full_name_from_id(self, user_id):
        name = None
        try:
            user = User.objects.filter(id=user_id).first()
            name = user.first_name + " " + user.last_name
        except Exception as e:
            print(e)
        return name


    def get_all_supervisors_for_induction(self):
        query = ''' SELECT DISTINCT auth_user.id, auth_user.first_name, auth_user.last_name, auth_user.email, group_id
                    FROM auth_user_groups
                    JOIN auth_user ON auth_user.id = auth_user_groups.user_id
                    WHERE group_id != 5 AND is_active = 1
                    ORDER BY group_id, auth_user.first_name, auth_user.last_name
                    '''
        conn = Connection("default")
        return conn.execute(query)
    

    def create_deactivated_employee(self, emp_id):
        obj = DeactivatedEmployee(emp_id=emp_id)
        obj.save()
        return obj
    
    def delete_deactivated_employee(self, auth_data, emp_id):
        DeactivatedEmployee.objects.filter(emp_id=emp_id, deleted=0).update(**auth_data)
        











