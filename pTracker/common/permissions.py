from rest_framework import permissions

from pTracker.dataaccess.ptracker_access.permissions_da import PermissionsDA

class IPRestrictedPermission(permissions.BasePermission):

    def has_permission(self, request, view):
        allowed_ips = list(PermissionsDA().get_allowed_hosts())
        remote_ip = request.META.get('REMOTE_ADDR')
        return remote_ip in allowed_ips
