from django.db import models

class LeavePeriod(models.Model):
    leave_period_id = models.AutoField(primary_key=True)
    leave_period_start_date =  models.DateField()
    leave_period_end_date =  models.DateField()

    class Meta:
        db_table = u'leave_period'

class LeaveType(models.Model):
    leave_type_id = models.AutoField(primary_key=True)
    leave_type_name = models.CharField(max_length=50)
    available_flag =  models.SmallIntegerField()
    default_no_of_leaves = models.IntegerField()
    class Meta:
        db_table = u'leave_type'

class LeaveQuota(models.Model):
    quota_id = models.AutoField(primary_key=True)
    leave_type_id = models.SmallIntegerField()
    leave_period_id = models.SmallIntegerField()
    employee_id =  models.SmallIntegerField()
    no_of_days_allotted =  models.FloatField()
    leave_taken = models.FloatField()
    leave_brought_forward = models.FloatField(default=0.0)
    leave_carried_forward = models.FloatField(default=0.0)
    class Meta:
        db_table = u'leave_quota'


class LeaveRequests(models.Model):
    request_id = models.AutoField(primary_key=True)
    type_id =  models.SmallIntegerField()
    leave_period_id = models.SmallIntegerField()
    date_applied =  models.DateField(auto_now=True)
    employee_id =  models.SmallIntegerField()
    reason = models.CharField(max_length=250)
    length_days =  models.FloatField()
    start_date = models.DateField()
    end_date = models.DateField()
    status = models.SmallIntegerField()
    approver =  models.SmallIntegerField()
    comment =  models.CharField(max_length=250, default=None)
    notify = models.CharField(max_length=250, default=None)
    last_updated_date = models.DateTimeField(auto_now=True)
    comp_off_id = models.IntegerField(default=0)
    class Meta:
        db_table = u'leave_requests'

class Leave(models.Model):
    leave_id = models.AutoField(primary_key=True)
    type_id =  models.SmallIntegerField()
    leave_date =  models.DateField()
    length_hours =  models.SmallIntegerField()
    status = models.SmallIntegerField()
    leave_request_id = models.SmallIntegerField()
    leave_day_type =  models.SmallIntegerField()
    employee_id =  models.SmallIntegerField()
    leave_period_id =  models.SmallIntegerField()
    class Meta:
        db_table = u'leaves'

class LeaveRequestLog(models.Model):
    request_log_id =  models.AutoField(primary_key=True)
    request_id = models.SmallIntegerField()
    action = models.CharField(max_length=250)
    employee_id = models.SmallIntegerField()
    log_date_time =  models.DateTimeField(auto_now=True)
    class Meta:
        db_table = u'leave_request_log'

class CompensatoryLeaveRequest(models.Model):
    comp_off_id = models.AutoField(primary_key=True)
    start_date = models.DateField()
    end_date = models.DateField()
    no_of_days = models.SmallIntegerField()
    employee_id = models.SmallIntegerField()
    leave_type_id = models.SmallIntegerField()
    leave_period_id = models.SmallIntegerField()
    approver_id = models.SmallIntegerField()
    status = models.SmallIntegerField()
    reason = models.CharField(max_length=250)
    comment = models.CharField(max_length=250, default=None)
    applied_date = models.DateTimeField(auto_now=True)
    last_updated_date = models.DateField(auto_now=True)
    is_flag = models.IntegerField(default=0)
    scheduled_date = models.DateField(default=None)
    class Meta:
        db_table = u'compensatory_leave_request'

class CompensatoryLeaveRequestLog(models.Model):
    comp_off_log_id = models.AutoField(primary_key=True)
    comp_off_id = models.SmallIntegerField()
    action = models.CharField(max_length=250)
    employee_id = models.SmallIntegerField()
    log_date_time = models.DateTimeField(auto_now=True)
    class Meta:
        db_table = u'compensatory_leave_request_log'
