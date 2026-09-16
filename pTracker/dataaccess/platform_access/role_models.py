from django.db import models

from pTracker.dataaccess.platform_access.tenancy_models import Company
from pTracker.dataaccess.platform_access.capability_models import Capability
""" The following tables are created here
Role

Company-scoped (not tenant-scoped, not global): each company builds
its own named roles by bundling capabilities from the shared
Capability catalog. An IT company's "Director" and an accounting
company's "Partner" are unrelated Role rows even if their capability
sets overlap.
"""

class Role(models.Model):
    company = models.ForeignKey(Company, on_delete=models.CASCADE, related_name='roles')
    name = models.CharField(max_length=100)
    description = models.CharField(max_length=250, blank=True, null=True)
    capabilities = models.ManyToManyField(Capability, blank=True, related_name='roles',
        db_table='platform_role_capabilities')
    is_active = models.BooleanField(default=True)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        db_table = 'platform_role'
        unique_together = ('company', 'name')

    def __str__(self):
        return f'{self.company_id}:{self.name}'
