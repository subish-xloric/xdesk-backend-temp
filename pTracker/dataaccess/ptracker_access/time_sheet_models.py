from django.db import models

class TimeSheet(models.Model):
    timesheet_id = models.AutoField(primary_key=True, db_column='timesheet_id')
    status = models.CharField(max_length=50, db_column='status')
    timesheet_date = models.DateField()
    user_id = models.IntegerField(db_column='user_id')
    total_duration = models.IntegerField(db_column='total_duration', default=0)
    created_date = models.DateTimeField(auto_now=True)

    class Meta:
        db_table = u'timesheet'

class TimeSheetItem(models.Model):
    timesheet_item_id = models.AutoField(primary_key=True, db_column='timesheet_item_id')
    timesheet_id = models.IntegerField(db_column='timesheet_id')
    module_id = models.IntegerField(db_column='module_id')
    project_id = models.IntegerField(db_column='project_id')
    activity_id = models.IntegerField(db_column='activity_id')
    duration = models.IntegerField(db_column='duration', default=0)
    comment = models.CharField(max_length=5000, db_column='comment')
    user_id = models.IntegerField(db_column='user_id')
    timesheet_date = models.DateField(null=True, blank=True)
    is_billable = models.IntegerField(default=1, db_column='is_billable')
    percentage_completed = models.CharField(max_length=3, db_column='percentage_completed')
    status = models.CharField(max_length=20, db_column='status')
    ticket_title = models.CharField(max_length=255, blank=True, null=True)
    ticket_eta = models.DateField(blank=True, null=True)
    class Meta:
        db_table = u'timesheet_item'


class TimeSheetActionLog(models.Model):
    action_id = models.AutoField(primary_key=True, db_column='action_id')
    timesheet_id = models.IntegerField(db_column='timesheet_id')
    comment = models.CharField(max_length=500, db_column='comment', null=True, blank=True)
    action = models.CharField(max_length=50, db_column='action')
    action_date = models.DateField(auto_now=True)
    performed_by = models.IntegerField(db_column='performed_by')

    class Meta:
        db_table = u'timesheet_action_log'

class TimeSheetArchive(models.Model):
    timesheet_id = models.IntegerField(primary_key=True, db_column='timesheet_id')
    status = models.CharField(max_length=50, db_column='status')
    timesheet_date = models.DateField()
    user_id = models.IntegerField(db_column='user_id')
    total_duration = models.IntegerField(db_column='total_duration', default=0)
    created_date = models.DateTimeField()

    class Meta:
        db_table = u'timesheet_archive'

class TimeSheetItemArchive(models.Model):
    timesheet_item_id = models.IntegerField(primary_key=True, db_column='timesheet_item_id')
    timesheet_id = models.IntegerField(db_column='timesheet_id')
    module_id = models.IntegerField(db_column='module_id')
    project_id = models.IntegerField(db_column='project_id')
    activity_id = models.IntegerField(db_column='activity_id')
    duration = models.IntegerField(db_column='duration', default=0)
    comment = models.CharField(max_length=5000, db_column='comment')
    user_id = models.IntegerField(db_column='user_id')
    timesheet_date = models.DateField(null=True, blank=True)
    is_billable = models.IntegerField(default=1, db_column='is_billable')
    percentage_completed = models.CharField(max_length=3, db_column='percentage_completed')
    status = models.CharField(max_length=20, db_column='status')
    ticket_title = models.CharField(max_length=255, blank=True, null=True)
    ticket_eta = models.DateField(blank=True, null=True)
    class Meta:
        db_table = u'timesheet_item_archive'


class TimeSheetActionLogArchive(models.Model):
    action_id = models.IntegerField(primary_key=True, db_column='action_id')
    timesheet_id = models.IntegerField(db_column='timesheet_id')
    comment = models.CharField(max_length=500, db_column='comment', null=True, blank=True)
    action = models.CharField(max_length=50, db_column='action')
    action_date = models.DateField()
    performed_by = models.IntegerField(db_column='performed_by')

    class Meta:
        db_table = u'timesheet_action_log_archive'

class TimeSheetArchiveLog(models.Model):
    archive_id = models.AutoField(primary_key=True, db_column='archive_id')
    archive_from = models.DateField(db_column='archive_from')
    archive_to = models.DateField(db_column='archive_to')
    archive_date = models.DateField(db_column='archive_date')
    user_id = models.IntegerField(db_column='user_id')

    class Meta:
        db_table = u'timesheet_archive_log'