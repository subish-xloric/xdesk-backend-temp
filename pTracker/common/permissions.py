from rest_framework import permissions

from pTracker.dataaccess.ptracker_access.permissions_da import PermissionsDA
from pTracker.dataaccess.platform_access.platform_user_models import PlatformUser

class IPRestrictedPermission(permissions.BasePermission):

    def has_permission(self, request, view):
        allowed_ips = list(PermissionsDA().get_allowed_hosts())
        remote_ip = request.META.get('REMOTE_ADDR')
        return remote_ip in allowed_ips


class IsPlatformUser(permissions.BasePermission):
    """ Restricts a view to authenticated SaaS platform operators only,
    keeping this entirely separate from employee (auth_user) access. """

    def has_permission(self, request, view):
        user = getattr(request, 'user', None)
        return isinstance(user, PlatformUser) and user.is_active
