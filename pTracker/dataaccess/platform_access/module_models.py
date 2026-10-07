from django.db import models

from pTracker.dataaccess.platform_access.tenancy_models import Company
""" The following tables are created here
Module
CompanyModule

Module is the global catalog of sellable product modules. Its code matches
the Capability.module string (e.g. 'leave'), so a capability's module can be
checked directly. CompanyModule records which modules a company has bought;
a company with no rows has no modules enabled.
"""

class Module(models.Model):
    code = models.CharField(max_length=50, primary_key=True)
    name = models.CharField(max_length=100)
    description = models.CharField(max_length=250, blank=True, null=True)
    is_active = models.BooleanField(default=True)
    requires = models.ManyToManyField('self', symmetrical=False, blank=True, related_name='required_by',
        db_table='platform_module_requires')

    class Meta:
        db_table = 'platform_module'

    def __str__(self):
        return self.code


class CompanyModule(models.Model):
    company = models.ForeignKey(Company, on_delete=models.CASCADE, related_name='company_modules')
    module = models.ForeignKey(Module, on_delete=models.PROTECT, related_name='company_modules')
    is_enabled = models.BooleanField(default=True)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        db_table = 'platform_company_module'
        unique_together = ('company', 'module')

    def __str__(self):
        return f'{self.company_id}:{self.module_id}'
