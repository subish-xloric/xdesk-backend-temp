from pTracker.dataaccess.attendance_v2_access.device_models import AttendanceDevice
from pTracker.dataaccess.attendance_v2_access.device_models import AttendanceCollector


class DeviceDA:

    def get_devices(self, company_id, include_inactive=False, device_types=None):
        devices = AttendanceDevice.objects.filter(company_id=company_id).select_related('location')
        if not include_inactive:
            devices = devices.filter(is_active=True)
        if device_types:
            devices = devices.filter(device_type__in=device_types)
        return devices.order_by('name')

    def get_device(self, company_id, device_id):
        return AttendanceDevice.objects.filter(company_id=company_id, pk=device_id).select_related('location').first()

    def get_devices_by_ids(self, company_id, device_ids):
        return list(AttendanceDevice.objects.filter(company_id=company_id, pk__in=list(device_ids)))

    def code_exists(self, company_id, code, exclude_id=None):
        devices = AttendanceDevice.objects.filter(company_id=company_id, code=code)
        if exclude_id:
            devices = devices.exclude(pk=exclude_id)
        return devices.exists()

    def location_in_use(self, location_id):
        return AttendanceDevice.objects.filter(location_id=location_id, is_active=True).exists()

    def create_device(self, **fields):
        return AttendanceDevice.objects.create(**fields)

    def update_device(self, device, **fields):
        for key, value in fields.items():
            setattr(device, key, value)
        device.save()
        return device


class CollectorDA:

    def get_collectors(self, company_id, include_inactive=False):
        collectors = AttendanceCollector.objects.filter(company_id=company_id).prefetch_related('devices')
        if not include_inactive:
            collectors = collectors.filter(is_active=True)
        return collectors.order_by('collector_id')

    def get_collector(self, company_id, pk):
        return AttendanceCollector.objects.filter(company_id=company_id, pk=pk).prefetch_related('devices').first()

    def get_collector_for_auth(self, collector_id):
        return AttendanceCollector.objects.filter(collector_id=collector_id).select_related('company').first()

    def collector_id_exists(self, collector_id, exclude_pk=None):
        collectors = AttendanceCollector.objects.filter(collector_id=collector_id)
        if exclude_pk:
            collectors = collectors.exclude(pk=exclude_pk)
        return collectors.exists()

    def get_collector_device_by_code(self, collector, device_code):
        return collector.devices.filter(code=device_code, is_active=True).select_related('location').first()

    def create_collector(self, device_ids, **fields):
        collector = AttendanceCollector.objects.create(**fields)
        collector.devices.set(device_ids)
        return collector

    def update_collector(self, collector, device_ids=None, **fields):
        for key, value in fields.items():
            setattr(collector, key, value)
        collector.save()
        if device_ids is not None:
            collector.devices.set(device_ids)
        return collector

    def touch_collector(self, pk, **fields):
        """ Monitoring timestamps only; avoids re-saving (and racing on) the row. """
        AttendanceCollector.objects.filter(pk=pk).update(**fields)
