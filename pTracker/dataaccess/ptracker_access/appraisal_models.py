from django.db import models

class AppraisalPeriod(models.Model):
    period_id = models.AutoField(primary_key=True)
    period_start_date =  models.DateField()
    period_end_date =  models.DateField()
    year = models.CharField(max_length=45)
    is_deleted = models.SmallIntegerField()

    class Meta:
        db_table = u'appraisal_period'

class AppraisalForm(models.Model):
    appraisal_id = models.AutoField(primary_key=True)
    period_id = models.SmallIntegerField()
    employee_id = models.SmallIntegerField()
    appraisal_token = models.CharField(max_length=250)
    appraisal_data = models.TextField()
    date_initialized = models.DateField(auto_now=True)
    status = models.SmallIntegerField()
    organization_id = models.SmallIntegerField()
    appraiser_id = models.SmallIntegerField()
    reviewer_id = models.SmallIntegerField()
    appraiser_expiry_date = models.DateField()
    reviewer_expiry_date = models.DateField()
    employee_expiry_date = models.DateField()
    appraiser_submitted = models.SmallIntegerField()
    reviewer_submitted =  models.SmallIntegerField()
    employee_submitted = models.SmallIntegerField()
    rating = models.SmallIntegerField(default=0)
    batch_id = models.SmallIntegerField()
    is_published = models.SmallIntegerField(default=0)
    assessment_file = models.CharField(max_length=250)

    class Meta:
        db_table = u'appraisal_form'

class AppraisalLog(models.Model):
    id = models.AutoField(primary_key=True)
    appraisal_id = models.SmallIntegerField()
    action = models.CharField(max_length=250)
    employee_id = models.SmallIntegerField()
    log_date_time =  models.DateTimeField(auto_now=True)

    class Meta:
        db_table = u'appraisal_log'

class AppraisalCeleryJobLog(models.Model):
    id = models.AutoField(primary_key=True)
    message = models.TextField()
    class Meta:
        db_table = u'appraisal_celery_job_log'

class AppraisalBatches(models.Model):
    batch_id = models.AutoField(primary_key=True)
    batch_name = models.CharField(max_length=45)
    is_deleted = models.SmallIntegerField()
    class Meta:
        db_table = u'appraisal_batches'