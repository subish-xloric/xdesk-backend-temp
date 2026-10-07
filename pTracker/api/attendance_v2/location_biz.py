from django.db import transaction

from pTracker.api.attendance_v2.attendance_v2_helper import active_company_id
from pTracker.api.attendance_v2.attendance_v2_helper import require_capability
from pTracker.api.attendance_v2.attendance_v2_helper import guarded
from pTracker.api.attendance_v2.attendance_v2_helper import first_error_message
from pTracker.api.attendance_v2.attendance_v2_helper import V2Error
from pTracker.api.attendance_v2.attendance_v2_helper import CAP_MANAGE_DEVICES
from pTracker.api.attendance_v2.audit_biz import record_audit
from pTracker.api.attendance_v2.audit_biz import snapshot_fields
from pTracker.api.attendance_v2.serializers import LocationSerializer
from pTracker.dataaccess.attendance_v2_access.location_da import LocationDA
from pTracker.dataaccess.attendance_v2_access.device_da import DeviceDA
from pTracker.dataaccess.attendance_v2_access.org_da import OrgDA

AUDIT_FIELDS = ('name', 'code', 'location_type', 'parent_id', 'branch_id', 'is_active')


def location_dict(location, paths=None):
    return {
        'id': location.id,
        'name': location.name,
        'code': location.code,
        'location_type': location.location_type,
        'parent_id': location.parent_id,
        'branch_id': location.branch_id,
        'path': paths.get(location.id) if paths else None,
        'is_active': location.is_active,
    }


class LocationBL:
    """ Company-scoped building / floor / area / room hierarchy. Readable by any
    member (it is needed for filters and check-in); changed only with
    attendance.manage_devices. """

    def __init__(self):
        self.__da = LocationDA()

    @guarded('list_locations')
    def list_locations(self, user_id, query):
        company_id = active_company_id(user_id)
        include_inactive = query.get('include_inactive') in ('1', 'true', 'True')
        locations = list(self.__da.get_locations(company_id, include_inactive))
        paths = self._paths(locations)
        return {'locations': [location_dict(l, paths) for l in locations], 'status': 200}

    @guarded('get_location')
    def get_location(self, user_id, location_id):
        company_id = active_company_id(user_id)
        location = self.__da.get_location(company_id, location_id)
        if location is None:
            raise V2Error('Location not found', 404)
        return {'location': location_dict(location), 'status': 200}

    @guarded('create_location')
    def create_location(self, user_id, data):
        company_id = active_company_id(user_id)
        require_capability(user_id, CAP_MANAGE_DEVICES)
        fields = self._validated(company_id, data)
        with transaction.atomic():
            location = self.__da.create_location(company_id=company_id, created_by=user_id, **fields)
            record_audit(company_id, user_id, 'location', location.id, 'create',
                         new=snapshot_fields(location, AUDIT_FIELDS))
        return {'location': location_dict(location), 'status': 201}

    @guarded('update_location')
    def update_location(self, user_id, location_id, data):
        company_id = active_company_id(user_id)
        require_capability(user_id, CAP_MANAGE_DEVICES)
        location = self.__da.get_location(company_id, location_id)
        if location is None:
            raise V2Error('Location not found', 404)
        fields = self._validated(company_id, data, location)
        if fields.get('is_active') is False:
            self._ensure_can_deactivate(location)
        with transaction.atomic():
            old = snapshot_fields(location, AUDIT_FIELDS)
            location = self.__da.update_location(location, **fields)
            record_audit(company_id, user_id, 'location', location.id, 'update', old=old,
                         new=snapshot_fields(location, AUDIT_FIELDS))
        return {'location': location_dict(location), 'status': 200}

    @guarded('deactivate_location')
    def deactivate_location(self, user_id, location_id):
        """ Soft delete: history (punches, sessions) keeps pointing at it. """
        company_id = active_company_id(user_id)
        require_capability(user_id, CAP_MANAGE_DEVICES)
        location = self.__da.get_location(company_id, location_id)
        if location is None:
            raise V2Error('Location not found', 404)
        self._ensure_can_deactivate(location)
        with transaction.atomic():
            self.__da.update_location(location, is_active=False)
            record_audit(company_id, user_id, 'location', location.id, 'deactivate')
        return {'message': 'Location deactivated', 'status': 200}

    def _ensure_can_deactivate(self, location):
        if self.__da.has_active_children(location.id):
            raise V2Error('Deactivate or move the child locations first', 409)
        if DeviceDA().location_in_use(location.id):
            raise V2Error('Active devices are assigned to this location', 409)

    def _validated(self, company_id, data, existing=None):
        serializer = LocationSerializer(data=data)
        if not serializer.is_valid():
            raise V2Error('Validation failed', 400, first_error_message(serializer.errors))
        fields = dict(serializer.validated_data)
        if self.__da.code_exists(company_id, fields['code'], existing.id if existing else None):
            raise V2Error(f"Location code {fields['code']} already exists", 409)

        parent_id = fields.get('parent_id')
        if parent_id:
            if not self.__da.get_location(company_id, parent_id):
                raise V2Error('parent_id must be a location of your company')
            if existing and self._creates_cycle(company_id, existing.id, parent_id):
                raise V2Error('A location cannot be placed under itself or its descendants')
        branch_id = fields.get('branch_id')
        if branch_id and not OrgDA().branch_belongs_to_company(branch_id, company_id):
            raise V2Error('branch_id must be a branch of your company')
        return fields

    def _creates_cycle(self, company_id, location_id, parent_id):
        parents = self.__da.get_parent_map(company_id)
        current, hops = parent_id, 0
        while current and hops < 1000:
            if current == location_id:
                return True
            current, hops = parents.get(current), hops + 1
        return False

    def _paths(self, locations):
        """ "Building A / Ground Floor / Production" for display. """
        by_id = {l.id: l for l in locations}
        paths = {}

        def path(location, depth=0):
            if location.id in paths:
                return paths[location.id]
            parent = by_id.get(location.parent_id)
            value = location.name if parent is None or depth > 50 else f'{path(parent, depth + 1)} / {location.name}'
            paths[location.id] = value
            return value

        for location in locations:
            path(location)
        return paths
