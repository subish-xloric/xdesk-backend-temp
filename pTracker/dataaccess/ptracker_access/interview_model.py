from django.db import models
""" The following tables are created here
CareerOpening
Candidate
OfferReleased
Interview
InterviewScoreCard
"""

class CareerOpening(models.Model):
    career_opening_id = models.AutoField(primary_key=True)
    position_name = models.CharField(max_length=300)
    ref_no = models.CharField(max_length=50)
    required_experience = models.CharField(max_length=100)
    required_qualification = models.CharField(max_length=200)
    soft_skill = models.CharField(max_length=2000)
    technical_skill = models.CharField(max_length=2000)
    comment = models.CharField(max_length=10000)
    status = models.SmallIntegerField(default=1)
    number_of_opening = models.IntegerField(default=1)
    total_interviews = models.IntegerField(default=0)
    no_of_short_listed = models.IntegerField(default=0)
    no_of_hold = models.IntegerField(default=0)
    no_of_acquired = models.IntegerField(default=0)
    is_deleted = models.SmallIntegerField(default=0)
    created_date = models.DateTimeField(auto_now=True)
    lead_interviewer = models.IntegerField()
    created_by = models.IntegerField()
    deleted_by = models.IntegerField()
    deleted_date = models.DateTimeField(null=True, blank=True)
    closed_date = models.DateTimeField(null=True, blank=True)
    min_and_max_experience = models.CharField(max_length=100,default='0-0')
    coding_tools = models.CharField(null=True, blank=True,max_length=250)

    class Meta:
        db_table = u'career_opening'


class Candidate(models.Model):
    candidate_id = models.AutoField(primary_key=True)
    first_name = models.CharField(max_length=100)
    last_name = models.CharField(max_length=100)
    email = models.CharField(max_length=100)
    mobile = models.CharField(max_length=20)
    career_opening_id = models.IntegerField()
    candidate_status = models.IntegerField(default=1)
    profile = models.CharField(max_length=250)
    offer_released = models.SmallIntegerField(default=0)
    is_deleted = models.SmallIntegerField(default=0)
    reference = models.CharField(max_length=50)
    refered_employee = models.IntegerField()
    created_date = models.DateTimeField(auto_now=True)
    created_by = models.IntegerField()
    deleted_by = models.IntegerField()
    deleted_date = models.DateTimeField(null=True, blank=True)
    comment = models.CharField(max_length=500)

    class Meta:
        db_table = u'candidate'


class CandidateLogs(models.Model):
    id = models.AutoField(primary_key=True)
    candidate_id = models.IntegerField()
    action = models.CharField(max_length=500)
    created_by = models.IntegerField()
    created_date = models.DateTimeField(auto_now=True)
    class Meta:
        db_table = u'candidate_logs'



class Interview(models.Model):
    interview_id = models.AutoField(primary_key=True)
    interview_code = models.CharField(max_length=30)
    candidate_id = models.IntegerField(max_length=11)
    interviewer = models.CharField(max_length=50)
    interview_status = models.IntegerField()
    date_and_time = models.DateTimeField()
    mode_of_interview = models.CharField(max_length=30)
    meeting_link = models.CharField(max_length=250)
    result = models.CharField(max_length=40)
    score = models.IntegerField(default=0)
    comment = models.CharField(max_length=20000)
    is_deleted = models.SmallIntegerField(default=0)
    time_taken = models.IntegerField()
    estimated_time = models.IntegerField()
    created_date = models.DateTimeField(auto_now=True)
    created_by = models.IntegerField()
    deleted_by = models.IntegerField(null=True, blank=True)
    deleted_date = models.DateTimeField(null=True, blank=True)

    class Meta:
        db_table = u'interview'



class InterviewScoreCard(models.Model):
    id = models.AutoField(primary_key=True)
    interview_id = models.IntegerField(max_length=11)
    skill = models.CharField(max_length=2000)
    score = models.IntegerField()
    note = models.CharField(max_length=500)
    is_deleted = models.SmallIntegerField(default=0)
    skill_type = models.CharField(max_length=30)
    created_by = models.IntegerField()

    class Meta:
        db_table = u'interview_score_card'

class SoftSkills(models.Model):
    id = models.AutoField(primary_key=True)
    soft_skill = models.CharField(max_length=300)
    is_mandatory = models.SmallIntegerField(default=0)

    class Meta:
        db_table = u'soft_skills'

class TechnicalSkills(models.Model):
    id = models.AutoField(primary_key=True)
    technical_skill = models.CharField(max_length=300)
    is_mandatory = models.SmallIntegerField(default=0)

    class Meta:
        db_table = u'technical_skills'

class InterviewLogs(models.Model):
    id = models.AutoField(primary_key=True)
    interview_id = models.IntegerField(max_length=11)
    action = models.CharField(max_length=250)

    class Meta:
        db_table = u'interview_logs'

class InterviewComments(models.Model):
    id = models.AutoField(primary_key=True)
    interview_id = models.IntegerField()
    comment = models.CharField(max_length=1000)
    created_date = models.DateTimeField(auto_now=True)
    created_by = models.IntegerField()
    class Meta:
        db_table = u'interview_comments'

class CandidateInformationSheet(models.Model):
    id = models.AutoField(primary_key=True)
    candidate_id = models.IntegerField()
    status = models.IntegerField()
    information_sheet = models.TextField()
    unique_code = models.CharField(max_length=250)
    class Meta:
        db_table = u'candidate_information_sheet'

class InterviewRoundMailStatus(models.Model):
    id = models.AutoField(primary_key=True)
    interview_id = models.IntegerField()
    status = models.IntegerField() # staus =1
    created_date = models.DateTimeField(auto_now=True)
    class Meta:
        db_table = u'interview_round_mail_status'















