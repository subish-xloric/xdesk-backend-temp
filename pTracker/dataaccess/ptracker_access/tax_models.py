# models.py

from django.db import models
from django.contrib.auth.models import User


class TaxBatch(models.Model):
    id = models.AutoField(primary_key=True)
    tax_period_id = models.IntegerField()
    user_id = models.IntegerField()
    regime_type = models.IntegerField(default=0) # {1: 'Old',  2: 'New'}
    last_date_of_declaration = models.DateField()
    last_date_of_claim_entry = models.DateField()
    created_by = models.IntegerField()
    created_on = models.DateTimeField(auto_now_add=True)
    org_id = models.IntegerField(default=0)
    is_deleted = models.IntegerField(default=0)

    class Meta:
        managed = False
        db_table = 'tax_batch'


class ClaimCategory(models.Model):
    id = models.AutoField(primary_key=True)
    name = models.CharField(max_length=255)
    description = models.TextField()
    maximum_allowed = models.IntegerField()
    parent_id = models.IntegerField()
    # properties = models.JSONField()
    section = models.CharField(max_length=255, null=True)

    class Meta:
        managed = False
        db_table = 'claim_category'


# class ClaimSubCategory(models.Model):
#     id = models.AutoField(primary_key=True)
#     cat_id = models.IntegerField()
#     name = models.CharField(max_length=255)

class TaxPeriod(models.Model):
    id = models.AutoField(primary_key=True)
    fin_year_id = models.IntegerField()
    claim_declaration_last_date = models.DateTimeField()
    claim_entry_last_date = models.DateTimeField()
    created_by = models.IntegerField()
    created_on = models.DateTimeField(auto_now_add=True)
    is_deleted = models.IntegerField(default=0)

    class Meta:
        managed = False
        db_table = 'tax_period'


class TaxPeriodExclude(models.Model):
    id = models.AutoField(primary_key=True)
    tax_period_id = models.IntegerField()
    user_id = models.IntegerField()
    valid_upto = models.DateTimeField()
    is_claim_declaration = models.IntegerField(default=0)
    is_claim_entry = models.IntegerField(default=0)
    created_by = models.IntegerField()
    created_on = models.DateTimeField(auto_now_add=True)

    class Meta:
        managed = False
        db_table = 'tax_period_exclude'



class ClaimDeclaration(models.Model):
    id = models.AutoField(primary_key=True)
    tax_period_id = models.IntegerField()
    user_id = models.IntegerField()
    cat_id = models.IntegerField()
    amount = models.DecimalField(max_digits=10, decimal_places=2)
    #approved_amount = models.DecimalField(max_digits=10, decimal_places=2)
    created_by = models.IntegerField()
    created_on = models.DateTimeField(auto_now_add=True)
    is_deleted = models.IntegerField(default=0)

    class Meta:
        managed = False
        db_table = 'claim_declaration'


class Claim(models.Model):
    id = models.AutoField(primary_key=True)
    claim_declaration_id = models.IntegerField()
    user_id = models.IntegerField()
    party_id = models.IntegerField(default=0)
    tax_period_id = models.IntegerField()
    cat_id =models.IntegerField()
    sub_cat_id = models.IntegerField()
    proof_attached = models.BooleanField()
    file_name = models.CharField(max_length=255)
    amount = models.DecimalField(max_digits=10, decimal_places=2)
    # status_choices = [('Under review', 'Under review'), ('Approved', 'Approved'), ('Rejected', 'Rejected')]
    status = models.CharField(max_length=20)
    comment = models.CharField(max_length=255)
    reject_reason = models.CharField(max_length=255, null=True, blank=True)
    created_by = models.IntegerField()
    created_on = models.DateTimeField(auto_now=True)
    is_deleted = models.BooleanField(default=False)
 
    class Meta:
        managed = False
        db_table = 'claim'

class ClaimsActivity(models.Model):
    id = models.AutoField(primary_key=True)
    action = models.CharField(max_length=255)
    claim_id = models.IntegerField()
    comment = models.TextField()
    created_by = models.IntegerField()
    created_on = models.DateTimeField(auto_now_add=True)
    
    class Meta:
        managed = False
        db_table = 'claims_activity'


class Parties(models.Model):
    id = models.AutoField(primary_key=True)
    party_type = models.IntegerField() 
    user_id = models.IntegerField()
    period_id = models.IntegerField()
    name = models.CharField(max_length=255)
    address_line1 = models.CharField(max_length=255)
    address_line2 = models.CharField(max_length=255, default='')
    city = models.CharField(max_length=255, default='')
    district = models.CharField(max_length=255, default='')
    state = models.CharField(max_length=255, default='')
    pincode = models.CharField(max_length=255, default='')
    pan_number = models.CharField(max_length=255)
    parent_id = models.IntegerField()
    is_deleted = models.BooleanField(default=False)

    class Meta:
        managed = False
        db_table = 'parties'


class ClaimAttachments(models.Model):
    id = models.AutoField(primary_key=True)
    claim_id = models.IntegerField()
    claim_declaration_id = models.IntegerField()
    file_name = models.CharField(max_length=255)

    class Meta:
        managed = False
        db_table = 'claim_attachments'

class HraDetails(models.Model):
    id = models.AutoField(primary_key=True)
    claim_id = models.IntegerField()
    claim_declaration_id = models.IntegerField()
    proof_type = models.CharField(max_length=50)
    from_date = models.DateField()
    to_date = models.DateField()
    payment_mode = models.CharField(max_length=50)

    class Meta:
        managed = False
        db_table = 'hra_details'
        
        
class Chat(models.Model):
    chat_id = models.AutoField(primary_key=True)
    user_1 = models.IntegerField()
    user_2 = models.IntegerField()
    created_on = models.DateTimeField(auto_now_add=True)
    
    class Meta:
        managed = False
        db_table = 'chat'
    

class Message(models.Model):
    id = models.AutoField(primary_key=True)
    chat_id = models.IntegerField()
    content = models.TextField()
    created_by = models.IntegerField()
    created_on = models.DateTimeField(auto_now_add=True)
    tax_period_id = models.IntegerField()
    
    class Meta:
        managed = False
        db_table = 'message'
        
        

class EmployeeTDS(models.Model):
    id = models.AutoField(primary_key=True)
    user_id = models.IntegerField()
    fin_year_id = models.IntegerField()
    month_id = models.IntegerField()
    year = models.IntegerField()
    amount = models.DecimalField(max_digits=10, decimal_places=2)
    created_on = models.DateTimeField(auto_now_add=True)
    last_updated_by = models.IntegerField()
    
    class Meta:
        managed = False
        db_table = 'employee_tds'
        


class CtcMaster(models.Model):
    ctc_id = models.AutoField(primary_key=True)
    name = models.CharField(max_length=300, null=True)
    description = models.CharField(max_length=300, null=True)
    section = models.CharField(max_length=300, null=True)
    type = models.CharField(max_length=300, null=True)
    is_deleted = models.BooleanField(default=False)

    class Meta:
        managed = False
        db_table = 'ctc_master'


class CtcEmployee(models.Model):
    emp_ctc_id = models.AutoField(primary_key=True)
    fin_yr_id = models.IntegerField()
    emp_id = models.IntegerField()
    ctc_id = models.IntegerField()
    amount = models.CharField(max_length=3000,null=True)
    created_by = models.IntegerField()
    created_on = models.DateTimeField(auto_now_add=True)
    is_deleted = models.BooleanField(default=False)

    class Meta:
        managed = False
        db_table = 'ctc_employee'



class EmployeeTaxDeduction(models.Model):
    id = models.AutoField(primary_key=True)
    description = models.CharField(max_length=255, null=True)
    amount = models.DecimalField(max_digits=10, decimal_places=2)
    criteria = models.CharField(max_length=255, null=True)
    regime_type = models.IntegerField()
    emp_id = models.IntegerField()
    fin_year_id = models.IntegerField()
    section = models.CharField(max_length=255, null=True)
    codename = models.CharField(max_length=255, null=True)
    
    class Meta:
        managed = False
        db_table = 'employee_tax_deduction'