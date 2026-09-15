from django.db import models



class RewardType(models.Model):
    id = models.AutoField(primary_key=True)
    name = models.CharField(max_length=150)
    description = models.CharField(max_length=500,blank=True)
    is_deleted = models.IntegerField(default=0)

    class Meta:
        db_table = u'reward_type'

class Reward(models.Model):
    id = models.AutoField(primary_key=True)
    reward_type = models.ForeignKey(RewardType, on_delete=models.SET_DEFAULT, default=0)
    receiving_emp_id = models.IntegerField()
    nominated_by  = models.IntegerField()
    status = models.IntegerField(default=1) #1 Nominated, 2 Under Review, 3: Approved, 4:Rejected
    title = models.CharField(max_length=150)
    short_description = models.CharField(max_length=500)
    justification_description = models.CharField(max_length=1000)
    published_date = models.DateTimeField(blank=True, null=True)
    created_date = models.DateTimeField(auto_now_add=True)
    is_deleted = models.IntegerField(default=0)

    class Meta:
        db_table = u'reward'


class RewardApprover(models.Model):
    id = models.AutoField(primary_key=True)
    reward = models.ForeignKey(Reward, on_delete=models.SET_DEFAULT, default=0)
    approver_id = models.IntegerField()
    is_approved = models.IntegerField(default=0)
    approval_date = models.DateTimeField(blank=True, null=True)
    approval_order =  models.IntegerField(default=0)

    class Meta:
        db_table = u'reward_approver'

class RewardComments(models.Model):
    id = models.AutoField(primary_key=True)
    reward = models.ForeignKey(Reward, on_delete=models.SET_DEFAULT, default=0)
    comment = models.CharField(max_length=1000)
    created_date = models.DateTimeField(auto_now_add=True)
    created_by = models.IntegerField()

    class Meta:
        db_table = u'reward_comments'

class Criteria(models.Model):
    id = models.AutoField(primary_key=True)
    reward_type = models.ForeignKey(RewardType, on_delete=models.SET_DEFAULT, default=0)
    criteria = models.CharField(max_length=1000)
    is_deleted = models.IntegerField(default=0)
    
    class Meta:
        db_table = u'master_criteria'

class RewardCriteria(models.Model):
    id = models.AutoField(primary_key=True)
    reward = models.ForeignKey(Reward, on_delete=models.SET_DEFAULT, default=0)
    criteria = models.ForeignKey(Criteria, on_delete=models.SET_DEFAULT, default=0)
    is_deleted = models.IntegerField(default=0)
    
    class Meta:
        db_table = u'reward_criteria'


class TvNotification(models.Model):
    id = models.AutoField(primary_key=True)
    type = models.CharField(max_length=50, null=True)
    start_date = models.DateField(null=True)
    end_date = models.DateField(null=True)
    emp_id = models.CharField(max_length=10, null=True)
    rewarded_by = models.CharField(max_length=100, null=True)
    title = models.CharField(max_length=251, null=True)
    short_desc = models.CharField(max_length=200, null=True)
    long_desc = models.TextField(null=True)
    is_deleted = models.IntegerField(default=0)
    created_date = models.DateTimeField(auto_now_add=True)

    class Meta:
        db_table = 'tv_notification'



class TvNotificationDetails(models.Model):
    id = models.AutoField(primary_key=True)
    notification = models.ForeignKey(TvNotification, on_delete=models.SET_DEFAULT, default=0)
    title = models.CharField(max_length=200)
    url = models.CharField(max_length=200)
    
    class Meta:
        db_table = u'tv_notification_details'
