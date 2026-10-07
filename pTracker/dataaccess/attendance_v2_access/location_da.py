from pTracker.dataaccess.attendance_v2_access.location_models import AttendanceLocation


class LocationDA:

    def get_locations(self, company_id, include_inactive=False):
        locations = AttendanceLocation.objects.filter(company_id=company_id)
        if not include_inactive:
            locations = locations.filter(is_active=True)
        return locations.order_by('parent_id', 'name')

    def get_location(self, company_id, location_id):
        return AttendanceLocation.objects.filter(company_id=company_id, pk=location_id).first()

    def get_location_by_code(self, company_id, code):
        return AttendanceLocation.objects.filter(company_id=company_id, code=code, is_active=True).first()

    def code_exists(self, company_id, code, exclude_id=None):
        locations = AttendanceLocation.objects.filter(company_id=company_id, code=code)
        if exclude_id:
            locations = locations.exclude(pk=exclude_id)
        return locations.exists()

    def get_parent_map(self, company_id):
        return dict(AttendanceLocation.objects.filter(company_id=company_id).values_list('id', 'parent_id'))

    def has_active_children(self, location_id):
        return AttendanceLocation.objects.filter(parent_id=location_id, is_active=True).exists()

    def create_location(self, **fields):
        return AttendanceLocation.objects.create(**fields)

    def update_location(self, location, **fields):
        for key, value in fields.items():
            setattr(location, key, value)
        location.save()
        return location
