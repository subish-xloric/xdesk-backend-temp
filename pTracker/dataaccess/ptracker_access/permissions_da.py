
from pTracker.dataaccess.ptracker_access.permissions_models import AllowedIPs


class PermissionsDA():

    def __init__(self):
        pass

    def get_allowed_hosts(self):
        resultSet = AllowedIPs.objects.filter(is_deleted=0).values_list('ip_address', flat=True)
        return resultSet

