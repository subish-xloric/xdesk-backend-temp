from django.db import models
""" The following tables are created here
AllowedIPs
"""

class AllowedIPs(models.Model):
    id = models.AutoField(primary_key=True)
    ip_address = models.CharField(max_length=50)
    is_deleted = models.IntegerField(default=0)

    class Meta:
        managed = False
        db_table = 'allowed_ip_addresses'












