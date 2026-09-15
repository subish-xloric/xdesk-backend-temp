from django.db import models

class ProjectActivity(models.Model):
    activity_id = models.AutoField(primary_key=True, db_column='activity_id')
    name = models.CharField(max_length=150, db_column='name')
    description = models.CharField(max_length=500, db_column='description', blank=True)
    is_deleted = models.IntegerField(default=0, db_column='is_deleted')

    class Meta:
        db_table = u'project_activity'

class ProjectType(models.Model):
    type_id = models.AutoField(primary_key=True, db_column='type_id')
    name = models.CharField(max_length=150, db_column='name')
    description = models.CharField(max_length=500, db_column='description', blank=True)

    class Meta:
        db_table = u'project_type'

class Project(models.Model):
    project_id = models.AutoField(primary_key=True, db_column='project_id')
    account_id = models.IntegerField(null=True, blank=True, db_column='account_id')
    project_type_id = models.IntegerField(null=True, blank=True, db_column='project_type_id')
    company_id = models.IntegerField(null=True, blank=True, db_column='company_id', default=2)
    name = models.CharField(max_length=150, db_column='name')
    description = models.CharField(max_length=500, db_column='description', blank=True)
    is_deleted = models.IntegerField(default=0, db_column='is_deleted')
    is_billable = models.IntegerField(default=1, db_column='is_billable')
    created_by = models.IntegerField(null=True, blank=True, db_column='created_by')
    deleted_by = models.IntegerField(null=True, blank=True, db_column='deleted_by')
    start_date = models.DateField(null=True, blank=True)
    end_date = models.DateField(null=True, blank=True)
    project_code = models.IntegerField(null=True, blank=True, db_column='project_code')

    class Meta:
        db_table = u'project'

class ProjectModule(models.Model):
    module_id = models.AutoField(primary_key=True, db_column='module_id')
    project_id = models.IntegerField(null=True, blank=True, db_column='project_id')
    name = models.CharField(max_length=150, db_column='name')
    description = models.CharField(max_length=500, db_column='description', blank=True)
    is_deleted = models.IntegerField(default=0, db_column='is_deleted')
    #is_billable = models.IntegerField(default=1, db_column='is_billable')
    created_by = models.IntegerField(null=True, blank=True, db_column='created_by')
    deleted_by = models.IntegerField(null=True, blank=True, db_column='deleted_by')
    start_date = models.DateField(null=True, blank=True)
    end_date = models.DateField(null=True, blank=True)

    class Meta:
        db_table = u'project_module'

class ProjectAccount(models.Model):
    account_id = models.AutoField(primary_key=True, db_column='account_id')
    name = models.CharField(max_length=150, db_column='name')
    description = models.CharField(max_length=500, db_column='description', blank=True)
    is_deleted = models.IntegerField(default=0, db_column='is_deleted')
    created_by = models.IntegerField(null=True, blank=True, db_column='created_by')
    deleted_by = models.IntegerField(null=True, blank=True, db_column='deleted_by')

    class Meta:
        db_table = u'project_account'

class ProjectEmployee(models.Model):
    mapping_id = models.AutoField(primary_key=True, db_column='mapping_id')
    project_id = models.IntegerField(db_column='project_id')
    user_id = models.IntegerField(db_column='user_id')
    is_lead = models.IntegerField(db_column='is_lead', default=0)
    is_preferred_project = models.IntegerField(db_column='is_preferred_project', default=0)

    class Meta:
        db_table = u'project_emp_mapping'

class ProjectEmployeeLog(models.Model):
    id = models.AutoField(primary_key=True)
    project_id = models.IntegerField(db_column='project_id')
    user_id = models.IntegerField(db_column='user_id')
    join_date = models.DateField(auto_now=True)
    release_date = models.DateField(null=True, blank=True,)

    class Meta:
        db_table = u'project_emp_mapping_log'


class ProjectAccountEmpMapping(models.Model):
    id = models.AutoField(primary_key=True)
    account_id = models.IntegerField()
    emp_id = models.IntegerField()
    is_billable = models.IntegerField(default=1)
    resource_alias_name = models.CharField(max_length=500, null=True, blank=True)
    start_date = models.DateField(auto_now=True)
    end_date = models.DateField(null=True, blank=True)
    created_by = models.IntegerField()
    created_date = models.DateField(auto_now=True)


    class Meta:
        db_table = u'project_account_emp_mapping'


class ProjectAccountEmpMappingLog(models.Model):
    log_id = models.AutoField(primary_key=True)
    mapping_id = models.IntegerField()
    emp_id = models.IntegerField()
    comment = models.CharField(max_length=500, null=True, blank=True)
    created_by = models.IntegerField()
    created_date = models.DateField(auto_now=True)

    class Meta:
        db_table = u'project_account_emp_mapping_log'


class ProjectRepo(models.Model):
    
    repo_id = models.AutoField(primary_key=True)
    provider = models.CharField(max_length=255)
    repo_name = models.CharField(max_length=255)
    base_url = models.CharField(max_length=255)
    token = models.CharField(max_length=255)
    repo_project_id = models.IntegerField()
    production_branch = models.CharField(max_length=255, null=True, blank=True)
    staging_branch = models.CharField(max_length=255,null=True, blank=True)
    qa_branch = models.CharField(max_length=255, null=True, blank=True)
    development_branch = models.CharField(max_length=255, null=True, blank=True)
    branch_prefix = models.CharField(max_length=255)
    branch_suffix = models.CharField(max_length=255)
    source_branch = models.CharField(max_length=255)
    target_branch = models.CharField(max_length=255)
    is_deleted = models.IntegerField(default=0)
    
    class Meta:
        managed = False
        db_table = 'project_repo'


class ProjectRepoMapping(models.Model):
    
    mapping_id = models.AutoField(primary_key=True)
    project_id = models.IntegerField()
    repo_id = models.IntegerField()
    is_deleted = models.IntegerField(default=0)

    class Meta:
        managed = False
        db_table = 'project_repo_mapping'



class ProjectRepoUserMapping(models.Model):

    repo_user_mapping_id = models.AutoField(primary_key=True)
    repo_id = models.IntegerField()
    user_id = models.IntegerField()
    token = models.CharField(max_length=255)

    class Meta:
        managed = False
        db_table = 'project_repo_user_mapping'
