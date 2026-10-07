from datetime import timedelta

from django.db import transaction

from pTracker.api.attendance_v2.attendance_v2_helper import active_company_id
from pTracker.api.attendance_v2.attendance_v2_helper import require_capability
from pTracker.api.attendance_v2.attendance_v2_helper import guarded
from pTracker.api.attendance_v2.attendance_v2_helper import first_error_message
from pTracker.api.attendance_v2.attendance_v2_helper import now_local
from pTracker.api.attendance_v2.attendance_v2_helper import fmt_dt
from pTracker.api.attendance_v2.attendance_v2_helper import V2Error
from pTracker.api.attendance_v2.attendance_v2_helper import CAP_MANAGE_DEVICES
from pTracker.api.attendance_v2.audit_biz import record_audit
from pTracker.api.attendance_v2.audit_biz import snapshot_fields
from pTracker.api.attendance_v2.collector_auth import generate_collector_key
from pTracker.api.attendance_v2.day_plan_biz import RuleSettings
from pTracker.api.attendance_v2.serializers import DeviceSerializer
from pTracker.api.attendance_v2.serializers import CollectorSerializer
from pTracker.dataaccess.attendance_v2_access.device_da import DeviceDA
from pTracker.dataaccess.attendance_v2_access.device_da import CollectorDA
from pTracker.dataaccess.attendance_v2_access.location_da import LocationDA
from pTracker.dataaccess.attendance_v2_access.daily_da import DailyDA
from pTracker.dataaccess.attendance_v2_access.constants import COLLECTOR_DEVICE_TYPES
from pTracker.dataaccess.attendance_v2_access.constants import COLLECTOR_STATUS_ONLINE
from pTracker.dataaccess.attendance_v2_access.constants import COLLECTOR_STATUS_OFFLINE
from pTracker.dataaccess.attendance_v2_access.constants import COLLECTOR_STATUS_UNKNOWN

DEVICE_AUDIT_FIELDS = ('name', 'code', 'device_type', 'location_id', 'serial_number', 'ip_address',
                       'requires_wfh_approval', 'is_active')
COLLECTOR_AUDIT_FIELDS = ('collector_id', 'name', 'collector_type', 'is_active')


def device_dict(device):
    return {
        'id': device.id,
        'name': device.name,
        'code': device.code,
        'device_type': device.device_type,
        'location_id': device.location_id,
        'location_name': device.location.name if device.location_id else None,
        'serial_number': device.serial_number,
        'ip_address': device.ip_address,
        'requires_wfh_approval': device.requires_wfh_approval,
        'is_active': device.is_active,
    }


def collector_dict(collector, offline_after_minutes):
    """ Monitoring view. effective_status: what the collector last reported,
    or offline once it has been silent longer than the company threshold. """
    now = now_local()
    if collector.last_seen_at is None:
        effective = COLLECTOR_STATUS_UNKNOWN
    elif now - collector.last_seen_at > timedelta(minutes=offline_after_minutes):
        effective = COLLECTOR_STATUS_OFFLINE
    else:
        effective = collector.reported_status
    return {
        'id': collector.id,
        'collector_id': collector.collector_id,
        'name': collector.name,
        'collector_type': collector.collector_type,
        'devices': [{'id': d.id, 'code': d.code, 'name': d.name} for d in collector.devices.all()],
        'api_key_prefix': collector.api_key_prefix,
        'key_rotated_at': fmt_dt(collector.key_rotated_at),
        'version': collector.version,
        'reported_status': collector.reported_status,
        'effective_status': effective,
        'is_online': effective == COLLECTOR_STATUS_ONLINE,
        'last_seen_at': fmt_dt(collector.last_seen_at),
        'last_sync_at': fmt_dt(collector.last_sync_at),
        'last_success_at': fmt_dt(collector.last_success_at),
        'last_error_at': fmt_dt(collector.last_error_at),
        'last_error': collector.last_error,
        'last_ip': collector.last_ip,
        'is_active': collector.is_active,
    }


class DeviceBL:

    def __init__(self):
        self.__da = DeviceDA()

    @guarded('list_devices')
    def list_devices(self, user_id, query):
        company_id = active_company_id(user_id)
        require_capability(user_id, CAP_MANAGE_DEVICES)
        include_inactive = query.get('include_inactive') in ('1', 'true', 'True')
        devices = self.__da.get_devices(company_id, include_inactive)
        return {'devices': [device_dict(d) for d in devices], 'status': 200}

    @guarded('get_device')
    def get_device(self, user_id, device_id):
        company_id = active_company_id(user_id)
        require_capability(user_id, CAP_MANAGE_DEVICES)
        return {'device': device_dict(self._get(company_id, device_id)), 'status': 200}

    @guarded('create_device')
    def create_device(self, user_id, data):
        company_id = active_company_id(user_id)
        require_capability(user_id, CAP_MANAGE_DEVICES)
        fields = self._validated(company_id, data)
        with transaction.atomic():
            device = self.__da.create_device(company_id=company_id, created_by=user_id, **fields)
            record_audit(company_id, user_id, 'device', device.id, 'create',
                         new=snapshot_fields(device, DEVICE_AUDIT_FIELDS))
        return {'device': device_dict(self.__da.get_device(company_id, device.id)), 'status': 201}

    @guarded('update_device')
    def update_device(self, user_id, device_id, data):
        company_id = active_company_id(user_id)
        require_capability(user_id, CAP_MANAGE_DEVICES)
        device = self._get(company_id, device_id)
        fields = self._validated(company_id, data, device)
        with transaction.atomic():
            old = snapshot_fields(device, DEVICE_AUDIT_FIELDS)
            device = self.__da.update_device(device, **fields)
            record_audit(company_id, user_id, 'device', device.id, 'update', old=old,
                         new=snapshot_fields(device, DEVICE_AUDIT_FIELDS))
        return {'device': device_dict(self.__da.get_device(company_id, device.id)), 'status': 200}

    @guarded('deactivate_device')
    def deactivate_device(self, user_id, device_id):
        company_id = active_company_id(user_id)
        require_capability(user_id, CAP_MANAGE_DEVICES)
        device = self._get(company_id, device_id)
        with transaction.atomic():
            self.__da.update_device(device, is_active=False)
            record_audit(company_id, user_id, 'device', device.id, 'deactivate')
        return {'message': 'Device deactivated', 'status': 200}

    def _get(self, company_id, device_id):
        device = self.__da.get_device(company_id, device_id)
        if device is None:
            raise V2Error('Device not found', 404)
        return device

    def _validated(self, company_id, data, existing=None):
        serializer = DeviceSerializer(data=data)
        if not serializer.is_valid():
            raise V2Error('Validation failed', 400, first_error_message(serializer.errors))
        fields = dict(serializer.validated_data)
        if self.__da.code_exists(company_id, fields['code'], existing.id if existing else None):
            raise V2Error(f"Device code {fields['code']} already exists", 409)
        if fields.get('location_id') and not LocationDA().get_location(company_id, fields['location_id']):
            raise V2Error('location_id must be a location of your company')
        fields['ip_address'] = fields.get('ip_address') or None
        fields['serial_number'] = fields.get('serial_number') or None
        return fields


class CollectorBL:

    def __init__(self):
        self.__da = CollectorDA()

    def _offline_after(self, company_id):
        return RuleSettings.from_row(DailyDA().get_settings(company_id)).collector_offline_after_minutes

    @guarded('list_collectors')
    def list_collectors(self, user_id, query):
        company_id = active_company_id(user_id)
        require_capability(user_id, CAP_MANAGE_DEVICES)
        include_inactive = query.get('include_inactive') in ('1', 'true', 'True')
        offline_after = self._offline_after(company_id)
        return {'collectors': [collector_dict(c, offline_after)
                               for c in self.__da.get_collectors(company_id, include_inactive)], 'status': 200}

    @guarded('get_collector')
    def get_collector(self, user_id, pk):
        company_id = active_company_id(user_id)
        require_capability(user_id, CAP_MANAGE_DEVICES)
        return {'collector': collector_dict(self._get(company_id, pk), self._offline_after(company_id)),
                'status': 200}

    @guarded('create_collector')
    def create_collector(self, user_id, data):
        """ The plain API key is returned only in this response. """
        company_id = active_company_id(user_id)
        require_capability(user_id, CAP_MANAGE_DEVICES)
        fields, device_ids = self._validated(company_id, data)
        plain, key_hash, prefix = generate_collector_key()
        with transaction.atomic():
            collector = self.__da.create_collector(
                device_ids, company_id=company_id, created_by=user_id, api_key_hash=key_hash,
                api_key_prefix=prefix, key_rotated_at=now_local(), **fields)
            record_audit(company_id, user_id, 'collector', collector.id, 'create',
                         new={**snapshot_fields(collector, COLLECTOR_AUDIT_FIELDS), 'device_ids': device_ids})
        return {'collector': collector_dict(self._get(company_id, collector.id), self._offline_after(company_id)),
                'api_key': plain,
                'message': 'Store this key in the collector configuration now; it cannot be shown again.',
                'status': 201}

    @guarded('update_collector')
    def update_collector(self, user_id, pk, data):
        company_id = active_company_id(user_id)
        require_capability(user_id, CAP_MANAGE_DEVICES)
        collector = self._get(company_id, pk)
        fields, device_ids = self._validated(company_id, data, collector)
        with transaction.atomic():
            old = {**snapshot_fields(collector, COLLECTOR_AUDIT_FIELDS),
                   'device_ids': sorted(d.id for d in collector.devices.all())}
            self.__da.update_collector(collector, device_ids, **fields)
            record_audit(company_id, user_id, 'collector', collector.id, 'update', old=old,
                         new={**snapshot_fields(collector, COLLECTOR_AUDIT_FIELDS), 'device_ids': device_ids})
        return {'collector': collector_dict(self._get(company_id, pk), self._offline_after(company_id)),
                'status': 200}

    @guarded('rotate_collector_key')
    def rotate_key(self, user_id, pk):
        """ Old key stops working immediately. """
        company_id = active_company_id(user_id)
        require_capability(user_id, CAP_MANAGE_DEVICES)
        collector = self._get(company_id, pk)
        plain, key_hash, prefix = generate_collector_key()
        with transaction.atomic():
            self.__da.update_collector(collector, api_key_hash=key_hash, api_key_prefix=prefix,
                                       key_rotated_at=now_local())
            record_audit(company_id, user_id, 'collector', collector.id, 'rotate_key',
                         remarks='API key rotated')
        return {'collector_id': collector.collector_id, 'api_key': plain,
                'message': 'Store this key in the collector configuration now; it cannot be shown again.',
                'status': 200}

    @guarded('deactivate_collector')
    def deactivate_collector(self, user_id, pk):
        company_id = active_company_id(user_id)
        require_capability(user_id, CAP_MANAGE_DEVICES)
        collector = self._get(company_id, pk)
        with transaction.atomic():
            self.__da.update_collector(collector, is_active=False)
            record_audit(company_id, user_id, 'collector', collector.id, 'deactivate')
        return {'message': 'Collector deactivated', 'status': 200}

    def _get(self, company_id, pk):
        collector = self.__da.get_collector(company_id, pk)
        if collector is None:
            raise V2Error('Collector not found', 404)
        return collector

    def _validated(self, company_id, data, existing=None):
        serializer = CollectorSerializer(data=data)
        if not serializer.is_valid():
            raise V2Error('Validation failed', 400, first_error_message(serializer.errors))
        fields = dict(serializer.validated_data)
        device_ids = sorted(set(fields.pop('device_ids', []) or []))
        if self.__da.collector_id_exists(fields['collector_id'], existing.id if existing else None):
            raise V2Error(f"Collector id {fields['collector_id']} is already in use", 409)
        devices = DeviceDA().get_devices_by_ids(company_id, device_ids)
        if len(devices) != len(device_ids):
            raise V2Error('device_ids must be devices of your company')
        if any(d.device_type not in COLLECTOR_DEVICE_TYPES for d in devices):
            raise V2Error('Web/mobile/manual devices cannot be linked to a collector')
        return fields, device_ids
