from django.db import models
""" The following tables are created here
Assessee
Assessment
AssessmentComment
AssessmentLog

"""


class Assessee(models.Model):
    #assessee_id = models.AutoField(primary_key=True)
    emp_id = models.IntegerField(primary_key=True)
    status = models.IntegerField()
    general_impression = models.CharField(max_length=500)
    department = models.CharField(max_length=50)
    total_assessment = models.IntegerField(default=3)
    score = models.FloatField(default=0) #out of 5
    assessment_completed = models.IntegerField(default=0)
    created_date = models.DateTimeField(auto_now_add=True)
    created_by = models.IntegerField()

    class Meta:
        db_table = u'assessee'

    #department -  Developer, QA, SEO,
    #status - 1 Initiated, 2: IN progress, 3: Completed, 4 :Cancelled

class Assessment(models.Model):
    assessment_id = models.AutoField(primary_key=True)
    emp_id = models.IntegerField()
    assessment_code = models.CharField(max_length=50)
    assessor = models.CharField(max_length=50)
    assessment_status = models.IntegerField(default=0) # Pending, completed
    date_and_time = models.DateTimeField()
    mode_of_assessment = models.CharField(max_length=30, default='F2F')
    score = models.IntegerField(default=0) #out of 5
    summative_remark = models.CharField(max_length=500)
    is_deleted = models.SmallIntegerField(default=0)
    time_taken = models.IntegerField()
    estimated_time = models.IntegerField(default=3600)
    created_date = models.DateTimeField(auto_now_add=True)
    created_by = models.IntegerField()

    class Meta:
        db_table = u'assessment'

class AssessmentComment(models.Model):
    comment_id = models.AutoField(primary_key=True)
    assessment_id = models.IntegerField()
    comment = models.CharField(max_length=1000)
    comment_type = models.IntegerField(default=0)
    is_private = models.IntegerField(default=0)
    created_date = models.DateTimeField(auto_now_add=True)
    created_by = models.IntegerField()
    class Meta:
        db_table = u'assessment_comment'


class AssessmentLog(models.Model):
    id = models.AutoField(primary_key=True)
    assessee_id = models.IntegerField()
    assessment_id = models.IntegerField()
    action = models.CharField(max_length=500)

    class Meta:
        db_table = u'assessment_log'