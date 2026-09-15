from django.db import models

class EmployeeLeadMapping(models.Model):
    id = models.AutoField(primary_key=True, db_column='id')
    emp_id = models.IntegerField(db_column='emp_id')
    lead_id = models.IntegerField(db_column='lead_id')
    from_date = models.DateField()
    to_date = models.DateField()
    is_deleted = models.IntegerField(default=0, db_column='is_deleted')

    class Meta:
        db_table = u'emp_lead_mapping'


class UserProfile(models.Model):
    user_id = models.IntegerField(primary_key=True)
    secret_key = models.CharField(max_length=250, unique=True)
    is_twofa_on = models.SmallIntegerField(default=0)
    is_accout_blocked = models.SmallIntegerField(default=0)
    company_id = models.SmallIntegerField(default=0)
    reported_to = models.SmallIntegerField(default=0)
    dob = models.DateField()
    gender = models.CharField(max_length=10)
    marital_status = models.CharField(max_length=15)
    wedding_anniversary = models.DateField()
    job_status = models.SmallIntegerField(default=0)
    job_title = models.CharField(max_length=30)
    job_category = models.CharField(max_length=30)
    address_1 = models.CharField(max_length=250)
    address_2 = models.CharField(max_length=250)
    city_code = models.CharField(max_length=250)
    coun_code = models.CharField(max_length=20)
    provin_code = models.CharField(max_length=30)
    district_code = models.CharField(max_length=100)
    zipcode = models.CharField(max_length=20)
    home_telephone = models.CharField(max_length=20)
    mobile = models.CharField(max_length=20)
    work_telephone = models.CharField(max_length=50)
    personal_email = models.CharField(max_length=100, unique=True)
    termination_id = models.SmallIntegerField(default=0)
    blood_group = models.CharField(max_length=10)
    permanent_address_1 = models.CharField(max_length=250)
    permanent_address_2 = models.CharField(max_length=250)
    permanent_city_code = models.CharField(max_length=250)
    permanent_coun_code = models.CharField(max_length=20)
    permanent_provin_code = models.CharField(max_length=45)
    permanent_district_code = models.CharField(max_length=45)
    permanent_zipcode = models.CharField(max_length=20)
    profile_photo = models.CharField(max_length=250)
    pan = models.CharField(max_length=15)
    father_name = models.CharField(max_length=300)
    mother_name = models.CharField(max_length=300)
    # Stores the per-user API token for external third-party integrations.
    # Null means the user has not generated a token yet.
    api_token = models.CharField(
        max_length=64, null=True, blank=True, unique=True, db_column='api_token'
    )

    class Meta:
        db_table = u'user_profile'

class UsedBirthdayImage(models.Model):
    id = models.AutoField(primary_key=True, db_column='id')
    image_id = models.IntegerField(default=0)

    class Meta:
        db_table = u'used_birthday_image'

class EmployeeJobTitle(models.Model):
    id = models.AutoField(primary_key=True, db_column='id')
    job_title = models.CharField(max_length=100,db_column='job_title')
    job_description = models.CharField(max_length=100,db_column='job_description')
    note = models.CharField(max_length=400,default=None,db_column='note')
    is_deleted = models.IntegerField(default=0, db_column='is_deleted')

    class Meta:
        db_table = u'job_title'

class Organization(models.Model):
    id = models.AutoField(primary_key=True, db_column='id')
    name = models.CharField(max_length=50,db_column='name')
    description = models.CharField(max_length=400,db_column='description')
    is_deleted = models.IntegerField(default=0, db_column='is_deleted')

    class Meta:
        db_table = u'organization'

class EmployeeEmergencyContacts(models.Model):
    emp_id = models.IntegerField(primary_key=True)
    name = models.CharField(max_length=250)
    relationship = models.CharField(max_length=100)
    mobile_no = models.CharField(max_length=100)

    class Meta:
        db_table = u'employee_emergency_contacts'

class EmpLeadMappingLog(models.Model):
    id = models.AutoField(primary_key=True, db_column='id')
    mapping_id = models.IntegerField(db_column='mapping_id')
    emp_id = models.IntegerField(db_column='emp_id')
    lead_id = models.IntegerField(db_column='lead_id')
    action = models.CharField(max_length=250)

    class Meta:
        db_table = u'emp_lead_mapping_log'

class OffBoardingRequest(models.Model):
    id = models.AutoField(primary_key=True, db_column='id')
    user_id = models.IntegerField(db_column='user_id')
    emp_code = models.IntegerField(db_column='emp_code')
    subject = models.CharField(max_length=100,db_column='subject')
    content = models.CharField(max_length=10000,db_column='content')
    request_date = models.DateField(auto_now=True)
    relieving_date = models.DateField()
    status = models.SmallIntegerField()
    approver_id = models.IntegerField(db_column='approver_id')
    comment = models.CharField(max_length=250)
    organization_id = models.IntegerField(db_column='organization_id')
    deleted = models.SmallIntegerField(default=0)
    is_terminated = models.SmallIntegerField(default=0)
    off_boarding_type = models.SmallIntegerField()

    class Meta:
        db_table = u'off_boarding_request'

class OffBoardingRequestLog(models.Model):
    id = models.AutoField(primary_key=True, db_column='id')
    off_boarding_id = models.IntegerField(db_column='off_boarding_id')
    action = models.CharField(max_length=250)
    emp_id = models.SmallIntegerField()
    log_date_time =  models.DateTimeField(auto_now=True)

    class Meta:
        db_table = u'off_boarding_request_log'


class OffBoardingExitForm(models.Model):
    id = models.AutoField(primary_key=True, db_column='id')
    off_boarding_id = models.IntegerField(db_column='off_boarding_id')
    emp_id = models.IntegerField(db_column='emp_id')
    off_boarding_code = models.CharField(max_length=250,db_column='off_boarding_code')
    exit_form_data = models.CharField(max_length=1000000,db_column='exit_form_data')
    status = models.SmallIntegerField()
    organization_id = models.IntegerField(db_column='organization_id')
    request_date =  models.DateField()
    releiving_date  = models.DateField()

    class Meta:
        db_table = u'off_boarding_exit_form'

class ResetPasswordModel(models.Model):
    id = models.AutoField(primary_key=True, db_column='id')
    email = models.CharField(max_length=50)
    user_id = models.IntegerField(default=1)
    req_code = models.CharField(max_length=100)
    expiry = models.DateTimeField(null=True)
    deleted = models.BooleanField(default=False)

    class Meta:
        db_table = u'reset_password'


class OffBoardingDocuments(models.Model):
    id = models.AutoField(primary_key=True, db_column='id')
    off_boarding_id = models.IntegerField(db_column='off_boarding_id')
    emp_id = models.IntegerField(db_column='emp_id')
    document_name = models.CharField(max_length=100,db_column='document_name')
    document = models.CharField(max_length=250,db_column='document')
    created_date  = models.DateField(auto_now=True)

    class Meta:

        db_table = u'off_boarding_documents'



class EncryptedMobileData(models.Model):
    id = models.AutoField(primary_key=True, db_column='id')
    encrypted_text = models.CharField(max_length=2000, db_column='encrypted_text')
    token_id = models.CharField(max_length=250, db_column='token_id')
    is_deleted = models.BooleanField(default=False, db_column='is_deleted')

    class Meta:
        db_table = u'mobile_auth_token'

class MobileDevices(models.Model):
    id = models.AutoField(primary_key=True, db_column='id')
    user_id = models.IntegerField(db_column='user_id')
    app_version = models.CharField(max_length=50,db_column='app_version')
    build_number = models.CharField(max_length=50,db_column='build_number')
    device_type = models.CharField(max_length=50,db_column='device_type')
    device_os_version = models.CharField(max_length=50,db_column='device_os_version')
    device_identifier = models.CharField(max_length=1000,db_column='device_identifier')


    class Meta:
        db_table = u'mobile_devices'

class OffBoardingExitInterviewForm(models.Model):
    id = models.AutoField(primary_key=True, db_column='id')
    off_boarding_id = models.IntegerField(db_column='off_boarding_id')
    emp_id = models.IntegerField(db_column='emp_id')
    exit_interview_code = models.CharField(max_length=250,db_column='exit_interview_code')
    exit_interview_form_data = models.CharField(max_length=1000000,db_column='exit_interview_form_data')
    status = models.SmallIntegerField()
    organization_id = models.IntegerField(db_column='organization_id')
    request_date =  models.DateField()
    releiving_date  = models.DateField()

    class Meta:
        db_table = u'off_boarding_exit_interview_form'


class UserProfileProvisional(models.Model):
    id = models.IntegerField(primary_key=True)
    emp_id = models.IntegerField()
    field = models.CharField(max_length=150)
    value = models.CharField(max_length=250)
    status = models.IntegerField()
    created_by = models.IntegerField()
    created_date_time = models.DateTimeField(auto_now=True)
    class Meta:
        db_table = u'user_profile_provisional'

class AuthBiometric(models.Model):
    id = models.AutoField(primary_key=True, db_column='id')
    email = models.CharField(max_length=250, db_column='email')
    publicKey = models.CharField(max_length=2500, db_column='public_key')
    keyIdentifier = models.CharField(max_length=500, db_column='device_identifier')

    class Meta:
        db_table = u'auth_biometric'

class TimesheetExcludedEmployees(models.Model):
    id = models.IntegerField(primary_key=True)
    emp_id = models.IntegerField()
    expiry_date  = models.DateField()
    class Meta:
        db_table = u'timesheet_excluded_employees'

    
class DeactivatedEmployee(models.Model):
    id = models.IntegerField(primary_key=True)
    emp_id = models.IntegerField()    
    deleted = models.IntegerField(default=0)
    class Meta:
        db_table = u'inaktiver_employee'



        




