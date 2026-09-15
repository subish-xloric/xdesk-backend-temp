from django.db import models
""" The following tables are created here
FinancialYear
EmployeePayHeader
EmployeePayDetails
EmployeePayLog
"""

class FinancialYear(models.Model):
    financial_year_id = models.AutoField(primary_key=True)
    start_date = models.DateTimeField(blank=True, null=True)
    end_date = models.DateTimeField(blank=True, null=True)
    description = models.CharField(max_length=250, blank=True, null=True)

    class Meta:
        managed = False
        db_table = 'financial_year'

class EmployeePayHeader(models.Model):
    pay_header_id = models.AutoField(primary_key=True)
    financial_year_id = models.IntegerField()
    month = models.IntegerField()
    year = models.IntegerField()
    comment = models.TextField(blank=True, null=True)
    status = models.IntegerField()
    organization = models.IntegerField()
    #status = models.IntegerField()
    processed_date_time =  models.DateTimeField(blank=True, null=True)
    published_date_time =  models.DateTimeField(blank=True, null=True)
    reverted_date_time =  models.DateTimeField(blank=True, null=True)
    processed_by = models.IntegerField(blank=True, null=True)
    published_by = models.IntegerField(blank=True, null=True)
    reverted_by = models.IntegerField(blank=True, null=True)
    reverted_reason = models.CharField(max_length=250, blank=True, null=True)
    is_reverted = models.IntegerField(default=0, blank=True, null=True)

    class Meta:
        managed = False
        db_table = 'employee_pay_header'

class EmployeePayDetails(models.Model):
    pay_detail_id = models.AutoField(primary_key=True)
    pay_header_id = models.IntegerField()
    financial_year_id = models.IntegerField()
    emp_id = models.IntegerField()
    emp_code = models.CharField(max_length=25)
    month = models.IntegerField(blank=True, null=True)
    year = models.IntegerField( blank=True, null=True)
    processed_date_time = models.DateTimeField()
    published_date_time = models.DateTimeField()
    comment = models.TextField(blank=True, null=True)
    file_name = models.CharField(max_length=250)
    status = models.IntegerField()

    class Meta:
        managed = False
        db_table = 'employee_pay_details'


class EmployeePayLog(models.Model):
    log_id = models.AutoField(primary_key=True)
    log_message = models.TextField(blank=True, null=True)
    header_id = models.IntegerField()
    created_by = models.IntegerField(blank=True, null=True)
    created_date = models.DateTimeField(blank=True, null=True)

    class Meta:
        managed = False
        db_table = 'employee_pay_log'














