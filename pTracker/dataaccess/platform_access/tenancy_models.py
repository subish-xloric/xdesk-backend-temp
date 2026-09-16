from django.db import models
""" The following tables are created here
Tenant
Company
Branch
"""

class Tenant(models.Model):
    STATUS_TRIAL = 'trial'
    STATUS_ACTIVE = 'active'
    STATUS_SUSPENDED = 'suspended'
    STATUS_CHOICES = (
        (STATUS_TRIAL, 'Trial'),
        (STATUS_ACTIVE, 'Active'),
        (STATUS_SUSPENDED, 'Suspended'),
    )

    slug = models.SlugField(max_length=100, unique=True)
    name = models.CharField(max_length=250)
    status = models.CharField(max_length=20, choices=STATUS_CHOICES, default=STATUS_TRIAL)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        db_table = 'platform_tenant'

    def __str__(self):
        return self.name


class Company(models.Model):
    tenant = models.ForeignKey(Tenant, on_delete=models.PROTECT, related_name='companies')
    parent_company = models.ForeignKey('self', on_delete=models.SET_NULL, null=True, blank=True,
        related_name='subsidiaries')
    legal_name = models.CharField(max_length=250)
    short_name = models.CharField(max_length=100)
    registered_address = models.TextField(blank=True, null=True)
    contact_email = models.EmailField(blank=True, null=True)
    is_active = models.BooleanField(default=True)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        db_table = 'platform_company'
        unique_together = ('tenant', 'short_name')

    def __str__(self):
        return self.legal_name


class Branch(models.Model):
    KIND_HEAD_OFFICE = 'head_office'
    KIND_OFFICE = 'office'
    KIND_PLANT = 'plant'
    KIND_UNIT = 'unit'
    KIND_CHOICES = (
        (KIND_HEAD_OFFICE, 'Head Office'),
        (KIND_OFFICE, 'Office'),
        (KIND_PLANT, 'Plant'),
        (KIND_UNIT, 'Unit'),
    )

    company = models.ForeignKey(Company, on_delete=models.PROTECT, related_name='branches')
    name = models.CharField(max_length=250)
    code = models.CharField(max_length=50)
    kind = models.CharField(max_length=20, choices=KIND_CHOICES, default=KIND_OFFICE)
    timezone = models.CharField(max_length=50, default='Asia/Kolkata')
    address = models.TextField(blank=True, null=True)
    is_active = models.BooleanField(default=True)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        db_table = 'platform_branch'
        unique_together = ('company', 'code')

    def __str__(self):
        return self.name
