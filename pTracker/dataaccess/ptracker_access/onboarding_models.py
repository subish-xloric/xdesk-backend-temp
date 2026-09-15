from django.db import models

class UserAcademicDetails(models.Model):
    id = models.AutoField(primary_key=True, db_column='id')
    emp_id = models.IntegerField(db_column='emp_id')
    course = models.CharField(max_length=250,db_column='course')
    start_date = models.DateField()
    end_date = models.DateField()
    year_of_passout = models.CharField(max_length=45)
    certificate = models.CharField(max_length=250,db_column='certificate')
    percentage =  models.CharField(max_length=45)
    university = models.CharField(max_length=250)

    class Meta:
        db_table = u'user_academic_details'

class WorkExperience(models.Model):
    id = models.AutoField(primary_key=True, db_column='id')
    emp_id = models.IntegerField(db_column='emp_id')
    company_name = models.CharField(max_length=500,db_column='company_name')
    role = models.CharField(max_length=500,db_column='role')
    joining_date = models.DateField()
    relieving_date = models.DateField()
    experience_certificate = models.CharField(max_length=250,db_column='experience_certificate')
    releiving_letter = models.CharField(max_length=250,db_column='releiving_letter')
    pay_slip =  models.CharField(max_length=250,db_column='pay_slip')
    last_ctc = models.CharField(max_length=100)

    class Meta:
        db_table = u'work_experience'

class TechnicalAndNonTechnicalSkills(models.Model):
    id = models.AutoField(primary_key=True, db_column='id')
    emp_id = models.IntegerField(db_column='emp_id')
    skill = models.CharField(max_length=500,db_column='skill')
    is_technical =  models.IntegerField(db_column='is_technical')
    rating = models.IntegerField(db_column='rating')
    months_of_experience = models.IntegerField(db_column='months_of_experience')
    class Meta:
        db_table = u'technical_and_non_technical_skills'

class KYCDocumentTypes(models.Model):
    id = models.AutoField(primary_key=True, db_column='id')
    doc_name = models.CharField(max_length=500,db_column='doc_name')
    class Meta:
        db_table = u'kyc_doc_types'

class KYCDocuments(models.Model):
    id = models.AutoField(primary_key=True, db_column='id')
    emp_id = models.IntegerField(db_column='emp_id')
    kyc_doc_type_id = models.IntegerField(db_column='kyc_doc_type_id')
    kyc_document = models.CharField(max_length=500,db_column='kyc_document')
    class Meta:
        db_table = u'kyc_docs'

class onBoardingCandidate(models.Model):
    candidate_id = models.AutoField(primary_key=True, db_column='candidate_id')
    first_name = models.CharField(max_length=250,db_column='first_name')
    last_name = models.CharField(max_length=250,db_column='last_name')
    phone = models.CharField(max_length=100,db_column='phone',unique=True)
    email = models.CharField(max_length=250,db_column='email',unique=True)
    offer_released_date = models.DateField()
    offer_accepted_date = models.DateField()
    expected_joining_date = models.DateField()
    onboarding_code =  models.CharField(max_length=250,db_column='onboarding_code')
    status = models.IntegerField(db_column='status')
    offer_letter = models.CharField(max_length=500,db_column='offer_letter')
    is_deleted = models.IntegerField(default=0, db_column="is_deleted")
    organization_id = models.IntegerField(db_column="organization_id")
    candidate_data = models.TextField()
    comment = models.CharField(max_length=250,db_column='comment')
    class Meta:
        db_table = u'onboarding_candidate'