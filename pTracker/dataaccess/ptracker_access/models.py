
from django.db import models

class AdminEmployee(models.Model):
    id = models.AutoField(primary_key=True, db_column='id')
    emp_code = models.CharField(max_length=10, db_column='emp_code')
    company_id = models.IntegerField(db_column='company_id')
    deleted = models.IntegerField(default=0, db_column='deleted')

    class Meta:
        db_table = u'admin_employee'

class AttendanceExcludeEmployee(models.Model):
    id = models.AutoField(primary_key=True, db_column='id')
    emp_code = models.CharField(max_length=10, db_column='emp_code')
    company_id = models.IntegerField(db_column='company_id')
    deleted = models.IntegerField(default=0, db_column='deleted')

    class Meta:
        db_table = u'attendance_exclude_employee'


class Logs(models.Model):
    id = models.AutoField(primary_key=True, db_column='log_id')
    message = models.CharField(max_length=500000, null=True, blank=True, db_column='message')
    log_type = models.CharField(max_length=10, null=True, blank=True, db_column='log_type')
    created_date = models.DateTimeField(auto_now=True, db_column='created_date')

    class Meta:
        db_table = u'Logs'

class Holidays(models.Model):
    id = models.AutoField(primary_key=True, db_column='holiday_id')
    company_id = models.IntegerField(db_column='company_id')
    holiday_date = models.DateField(db_column='holiday_date')
    title = models.CharField(max_length=250, db_column='title')
    description = models.CharField(max_length=500, db_column='description')
    deleted = models.IntegerField(default=0, db_column='deleted')
    created_date = models.DateTimeField(auto_now=True, db_column='created_date')
    holiday_image = models.CharField(max_length=250, db_column='holiday_image')

    class Meta:
        db_table = u'holidays'


class DailyAttendance(models.Model):
    attendance_id = models.AutoField(primary_key=True, db_column='attendance_id')
    attendance_date = models.DateField(db_column='attendance_date')
    company_id = models.IntegerField(db_column='company_id', null=True, blank=True)
    emp_code = models.CharField(max_length=10, db_column='emp_code')
    total_hours = models.IntegerField(db_column='total_hours', default=0)
    work_hours = models.IntegerField(db_column='work_hours', default=0)
    break_hours = models.IntegerField(db_column='break_hours', default=0)
    arrival = models.DateTimeField(db_column='arrival', null=True, blank=True,)
    departure = models.DateTimeField(db_column='departure', null=True, blank=True)
    arrival_status = models.CharField(max_length=1, db_column='arrival_status')

    class Meta:
        db_table = u'daily_attendance'



class WFHRequest(models.Model):
    wfh_id = models.AutoField(primary_key=True)
    start_date = models.DateField()
    end_date = models.DateField()
    emp_id = models.SmallIntegerField()
    approver_id = models.SmallIntegerField()
    status = models.SmallIntegerField()
    reason = models.CharField(max_length=250)
    comment = models.CharField(max_length=250, default=None)
    created_date = models.DateTimeField(auto_now=True)
    respond_date = models.DateField(default=None)
    notify = models.CharField(max_length=100, default='')

    class Meta:
        db_table = u'wfh_requests'

class AdditionalWorkingDays(models.Model):
    id = models.AutoField(primary_key=True)
    company_id = models.IntegerField(db_column='company_id')
    working_date = models.DateField(db_column='working_date')
    description = models.CharField(max_length=500, db_column='description')
    deleted = models.IntegerField(default=0, db_column='deleted')
    created_date = models.DateTimeField(auto_now=True, db_column='created_date')

    class Meta:
        db_table = u'additional_working_days'
