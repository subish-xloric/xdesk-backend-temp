""" Django only auto-imports an app's `models` module. The actual model
definitions live in tenancy_models.py and platform_user_models.py
(matching this project's convention of splitting models by concern);
this file just makes sure Django's app loader discovers them. """

from pTracker.dataaccess.platform_access.tenancy_models import Tenant
from pTracker.dataaccess.platform_access.tenancy_models import Company
from pTracker.dataaccess.platform_access.tenancy_models import Branch
from pTracker.dataaccess.platform_access.platform_user_models import PlatformUser
from pTracker.dataaccess.platform_access.capability_models import Capability
from pTracker.dataaccess.platform_access.role_models import Role
from pTracker.dataaccess.platform_access.membership_models import Membership

__all__ = [
    'Tenant', 'Company', 'Branch', 'PlatformUser',
    'Capability', 'Role', 'Membership',
]
