from django.db import models
""" The following tables are created here
Capability

A small, fixed, developer-curated catalog of atomic permission codes
(e.g. "leave.approve", "payroll.process"). Not user/API-creatable -
only listable. Roles (per-company) bundle capabilities from this
catalog.
"""

class Capability(models.Model):
    code = models.CharField(max_length=100, primary_key=True)
    module = models.CharField(max_length=50)
    description = models.CharField(max_length=250, blank=True, null=True)

    class Meta:
        db_table = 'platform_capability'

    def __str__(self):
        return self.code
