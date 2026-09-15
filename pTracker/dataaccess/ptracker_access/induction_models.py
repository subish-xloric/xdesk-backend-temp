from django.db import models
""" The following tables are created here
Induction
InductionDetail
InductionLog

"""


class Induction(models.Model):
    induction_id = models.AutoField(primary_key=True)
    emp_id = models.IntegerField()
    status = models.IntegerField()
    initiated_on = models.DateTimeField(auto_now_add=True)
    due_on = models.DateTimeField()
    created_by = models.IntegerField()

    class Meta:
        db_table = u'induction'

    """
    Status
    1 : Initiated
    2 : In progress
    3 : Complted
    4 : Cancelled
    """

class InductionDetail(models.Model):
    id = models.AutoField(primary_key=True)
    induction_id = models.IntegerField()
    lead_id = models.IntegerField()
    status = models.IntegerField(default=0)
    sign_on = models.DateTimeField(null=True, blank=True)

    class Meta:
        db_table = u'induction_detail'

    """
    status
    1 : pending
    2 : completed
    """

class InductionLog(models.Model):
    id = models.AutoField(primary_key=True)
    induction_id = models.IntegerField()
    action = models.CharField(max_length=500)
    class Meta:
        db_table = u'induction_log'



