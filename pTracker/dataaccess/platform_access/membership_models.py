from django.conf import settings
from django.db import models

from pTracker.dataaccess.platform_access.tenancy_models import Company
from pTracker.dataaccess.platform_access.tenancy_models import Branch
from pTracker.dataaccess.platform_access.role_models import Role
""" The following tables are created here
Membership

Links an existing employee (auth_user) to a Company (and optionally a
specific Branch) with a company-scoped Role. One employee can hold
several Memberships - e.g. a different role per branch, or a
company-wide role alongside a branch-specific one.
"""

class Membership(models.Model):
    STATUS_ACTIVE = 'active'
    STATUS_INVITED = 'invited'
    STATUS_SUSPENDED = 'suspended'
    STATUS_CHOICES = (
        (STATUS_ACTIVE, 'Active'),
        (STATUS_INVITED, 'Invited'),
        (STATUS_SUSPENDED, 'Suspended'),
    )

    user = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.CASCADE,
        related_name='company_memberships')
    company = models.ForeignKey(Company, on_delete=models.CASCADE, related_name='memberships')
    branch = models.ForeignKey(Branch, on_delete=models.SET_NULL, null=True, blank=True,
        related_name='memberships')
    role = models.ForeignKey(Role, on_delete=models.PROTECT, related_name='memberships')
    is_primary = models.BooleanField(default=False)
    status = models.CharField(max_length=20, choices=STATUS_CHOICES, default=STATUS_ACTIVE)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        db_table = 'platform_membership'
        unique_together = ('user', 'company', 'branch', 'role')

    def __str__(self):
        return f'{self.user_id}@{self.company_id}:{self.role_id}'
