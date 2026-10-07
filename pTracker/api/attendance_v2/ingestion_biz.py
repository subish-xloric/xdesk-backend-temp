""" Receives punches and heartbeats from external collectors.

Trust model: the authenticated collector decides the company. The payload's
collector_id must be the authenticated one, every device must be linked to
that collector, locations must belong to the same company, and employee codes
resolve only to active members of that company. Nothing company-, device- or
employee-related from the payload is used without that check.

Idempotency: (device, external_punch_id) is unique. A punch without an id gets
a deterministic one (hash of device + employee code + punch time), so a retry
of the same record is reported as a duplicate, never stored twice.
"""

import hashlib
from datetime import timedelta

from django.db import IntegrityError, transaction

from pTracker.api.attendance_v2.attendance_v2_helper import V2Error
from pTracker.api.attendance_v2.attendance_v2_helper import now_local
from pTracker.api.attendance_v2.attendance_v2_helper import v2_setting
from pTracker.api.attendance_v2.attendance_v2_helper import request_id_from
from pTracker.api.attendance_v2.attendance_v2_helper import client_ip
from pTracker.api.attendance_v2.attendance_v2_helper import first_error_message
from pTracker.api.attendance_v2.processing_biz import AttendanceProcessorBL
from pTracker.api.attendance_v2.serializers import PunchBatchSerializer
from pTracker.api.attendance_v2.serializers import PunchItemSerializer
from pTracker.api.attendance_v2.serializers import HeartbeatSerializer
from pTracker.api.attendance_v2.serializers import normalize_punch_type
from pTracker.common.company_modules import get_enabled_module_codes
from pTracker.common.exception_handler import ExceptionHandler
from pTracker.common.logs import Logs
from pTracker.dataaccess.attendance_v2_access.device_da import CollectorDA
from pTracker.dataaccess.attendance_v2_access.location_da import LocationDA
from pTracker.dataaccess.attendance_v2_access.punch_da import PunchDA
from pTracker.dataaccess.attendance_v2_access.org_da import OrgDA
from pTracker.dataaccess.attendance_v2_access.constants import COLLECTOR_DEVICE_TYPES
from pTracker.dataaccess.attendance_v2_access.constants import COLLECTOR_STATUS_ONLINE
from pTracker.dataaccess.attendance_v2_access.constants import RAW_PENDING
from pTracker.dataaccess.attendance_v2_access.constants import RAW_PROCESSED
from pTracker.dataaccess.attendance_v2_access.constants import RAW_UNRESOLVED_EMPLOYEE
from pTracker.dataaccess.attendance_v2_access.constants import SYNC_SUCCESS
from pTracker.dataaccess.attendance_v2_access.constants import SYNC_PARTIAL
from pTracker.dataaccess.attendance_v2_access.constants import SYNC_FAILED
from pTracker.dataaccess.attendance_v2_access.constants import SYNC_REJECTED
from pTracker.dataaccess.attendance_v2_access.constants import SYNC_KIND_HEARTBEAT

MAX_LOGGED_ERRORS = 100


def fallback_punch_id(device_code, employee_code, punch_time):
    digest = hashlib.sha256(f'{device_code}|{employee_code}|{punch_time.isoformat()}'.encode()).hexdigest()
    return f'auto:{digest[:40]}'


class PunchIngestionBL:

    def __init__(self):
        self.__log = Logs()
        self.__exception = ExceptionHandler()
        self.__collector_da = CollectorDA()
        self.__location_da = LocationDA()
        self.__punch_da = PunchDA()
        self.__org_da = OrgDA()

    # --- punches ----------------------------------------------------------
    def ingest(self, collector, data, meta):
        request_id = request_id_from(meta)
        started = now_local()
        sync_log = self.__punch_da.create_sync_log(
            company_id=collector.company_id, collector=collector, request_id=request_id,
            remote_ip=client_ip(meta), status=SYNC_REJECTED, started_at=started)
        self.__collector_da.touch_collector(collector.pk, last_seen_at=started, last_sync_at=started,
                                            last_ip=client_ip(meta))
        try:
            response = self._ingest(collector, data, sync_log, started)
        except V2Error as exc:
            self._finish_rejected(collector, sync_log, exc.message, exc.errors)
            response = {'success': False, 'error': exc.message, 'status': exc.status}
            if exc.errors:
                response['errors'] = exc.errors
        except Exception:
            reference = sync_log.request_id
            self.__log.error(f'[attendance_v2] punch ingest failed request_id={reference} '
                             f'company={collector.company_id} collector={collector.collector_id} '
                             f'{self.__exception.get_exception()}')
            self._finish_rejected(collector, sync_log, 'Internal error')
            response = {'success': False, 'error': f'Internal error. Reference: {reference}', 'status': 500}
        response['request_id'] = request_id
        response['sync_id'] = sync_log.id
        return response

    def _ingest(self, collector, data, sync_log, received_at):
        if 'attendance' not in get_enabled_module_codes(collector.company_id):
            raise V2Error("Module 'attendance' is not enabled for this collector's company", 403)

        batch = PunchBatchSerializer(data=data)
        if not batch.is_valid():
            raise V2Error('Invalid payload', 400, first_error_message(batch.errors))
        payload = batch.validated_data
        if payload['collector_id'] != collector.collector_id:
            raise V2Error('collector_id does not match the authenticated collector', 403)

        default_device = self._device(collector, payload['device_id']) if payload.get('device_id') else None
        if default_device:
            self.__punch_da.update_sync_log(sync_log, device=default_device)

        errors, prepared = [], []
        for index, item in enumerate(payload['punches']):
            try:
                prepared.append(self._prepare(collector, item, payload, default_device, received_at))
            except V2Error as exc:
                errors.append({'index': index, 'external_punch_id': item.get('external_punch_id'),
                               'employee_code': item.get('employee_code'), 'error': exc.message})

        codes = {p['employee_code'] for p in prepared}
        employees = self.__org_da.resolve_employee_codes(collector.company_id, codes) if codes else {}

        accepted, duplicates, new_events = 0, 0, []
        by_device = {}
        for p in prepared:
            by_device.setdefault(p['device'].id, []).append(p)
        for device_id, items in by_device.items():
            existing = self.__punch_da.get_existing_raw_punches(device_id, [p['external_punch_id'] for p in items])
            seen = set()
            for p in items:
                employee_id = employees.get(p['employee_code'])
                known = existing.get(p['external_punch_id'])
                if known is not None and known.status == RAW_UNRESOLVED_EMPLOYEE:
                    # Stored earlier for an unknown code: link it if the employee
                    # exists now, otherwise keep reporting it so the collector
                    # log still shows the problem.
                    seen.add(p['external_punch_id'])
                    if employee_id:
                        accepted += 1
                        new_events.append(self._resolve_existing(known, employee_id))
                    else:
                        errors.append({'external_punch_id': p['external_punch_id_supplied'],
                                       'employee_code': p['employee_code'],
                                       'error': f"Employee code {p['employee_code']} does not exist"})
                    continue
                if known is not None or p['external_punch_id'] in seen:
                    duplicates += 1
                    continue
                seen.add(p['external_punch_id'])
                outcome = self._store(collector, sync_log, p, employee_id, received_at)
                if outcome == 'duplicate':
                    duplicates += 1
                    continue
                if employee_id is None:
                    errors.append({'external_punch_id': p['external_punch_id_supplied'],
                                   'employee_code': p['employee_code'],
                                   'error': f"Employee code {p['employee_code']} does not exist"})
                    continue
                accepted += 1
                new_events.append(outcome)

        if new_events:
            AttendanceProcessorBL(collector.company).process_new_events(new_events)
            for event in new_events:
                self.__punch_da.update_raw_punch(event.raw_punch, status=RAW_PROCESSED, processed_at=now_local())

        failed = len(errors)
        status = SYNC_SUCCESS if not failed else (SYNC_PARTIAL if accepted or duplicates else SYNC_FAILED)
        finished = now_local()
        self.__punch_da.update_sync_log(
            sync_log, status=status, received_count=len(payload['punches']), accepted_count=accepted,
            duplicate_count=duplicates, failed_count=failed, errors=errors[:MAX_LOGGED_ERRORS] or None,
            finished_at=finished)
        touch = {'last_success_at': finished} if status != SYNC_FAILED else \
            {'last_error_at': finished, 'last_error': 'All punches in the last batch failed'}
        self.__collector_da.touch_collector(collector.pk, **touch)

        response = {'success': failed == 0, 'accepted': accepted, 'duplicates': duplicates,
                    'failed': failed, 'status': 200}
        if errors:
            response['errors'] = errors
        return response

    def _device(self, collector, device_code):
        device = self.__collector_da.get_collector_device_by_code(collector, device_code)
        if device is None or device.device_type not in COLLECTOR_DEVICE_TYPES:
            raise V2Error(f'Device {device_code} is not configured for this collector', 403)
        return device

    def _prepare(self, collector, item, payload, default_device, received_at):
        serializer = PunchItemSerializer(data=item)
        if not serializer.is_valid():
            raise V2Error('; '.join(first_error_message(serializer.errors)))
        punch = serializer.validated_data

        device = self._device(collector, punch['device_id']) if punch.get('device_id') else default_device
        if device is None:
            raise V2Error('device_id is required')

        punch_time = punch['punch_time']
        if punch_time > received_at + timedelta(minutes=v2_setting('MAX_FUTURE_SKEW_MINUTES')):
            raise V2Error('punch_time is in the future')
        if punch_time < received_at - timedelta(days=v2_setting('MAX_PUNCH_AGE_DAYS')):
            raise V2Error(f"punch_time is older than {v2_setting('MAX_PUNCH_AGE_DAYS')} days")

        location = device.location
        location_code = punch.get('location_code') or payload.get('location_code')
        if location_code:
            location = self.__location_da.get_location_by_code(collector.company_id, location_code)
            if location is None:
                raise V2Error(f'Location {location_code} does not exist')

        supplied_id = (punch.get('external_punch_id') or '').strip() or None
        raw_data = dict(punch.get('raw_data') or {})
        reported_source = punch.get('source') or payload.get('source')
        if reported_source:
            raw_data.setdefault('reported_source', reported_source)
        return {
            'device': device,
            'employee_code': punch['employee_code'],
            'punch_time': punch_time,
            'raw_punch_type': (str(punch['punch_type'])[:32] if punch.get('punch_type') not in (None, '') else None),
            'punch_type': normalize_punch_type(punch.get('punch_type')),
            'location': location,
            'raw_data': raw_data or None,
            'external_punch_id_supplied': supplied_id,
            'external_punch_id': supplied_id or fallback_punch_id(device.code, punch['employee_code'], punch_time),
        }

    def _store(self, collector, sync_log, p, employee_id, received_at):
        """ Raw punch (+ event when the employee is known). Returns the event,
        None for an unresolved employee, or 'duplicate' if a concurrent request
        stored the same punch first. """
        try:
            with transaction.atomic():
                raw = self.__punch_da.create_raw_punch(
                    company_id=collector.company_id, collector=collector, device=p['device'], sync_log=sync_log,
                    employee_id=employee_id, external_employee_id=p['employee_code'],
                    external_punch_id=p['external_punch_id'], punch_time=p['punch_time'],
                    raw_punch_type=p['raw_punch_type'], punch_type=p['punch_type'],
                    source=p['device'].device_type, location=p['location'], raw_data=p['raw_data'],
                    received_at=received_at,
                    status=RAW_PENDING if employee_id else RAW_UNRESOLVED_EMPLOYEE,
                    error_message=None if employee_id else 'Employee code not found in company')
                if employee_id is None:
                    return None
                return self._event_for(raw, employee_id)
        except IntegrityError:
            return 'duplicate'

    def _event_for(self, raw, employee_id):
        event = self.__punch_da.create_event(
            company_id=raw.company_id, employee_id=employee_id, event_time=raw.punch_time,
            event_type=raw.punch_type, location_id=raw.location_id, device_id=raw.device_id,
            source=raw.source, raw_punch=raw)
        event.raw_punch = raw
        return event

    def _resolve_existing(self, raw, employee_id):
        """ A punch stored earlier for an unknown employee code, resent after the
        employee was set up: link it now instead of reporting it as done. """
        with transaction.atomic():
            self.__punch_da.update_raw_punch(raw, employee_id=employee_id, status=RAW_PENDING, error_message=None)
            return self._event_for(raw, employee_id)

    def _finish_rejected(self, collector, sync_log, message, errors=None):
        finished = now_local()
        self.__punch_da.update_sync_log(sync_log, status=SYNC_REJECTED, message=message[:500],
                                        errors=errors[:MAX_LOGGED_ERRORS] if errors else None,
                                        finished_at=finished)
        self.__collector_da.touch_collector(collector.pk, last_error_at=finished, last_error=message[:500])

    # --- heartbeat --------------------------------------------------------
    def heartbeat(self, collector, data, meta):
        serializer = HeartbeatSerializer(data=data)
        now = now_local()
        if not serializer.is_valid():
            return {'success': False, 'error': 'Invalid payload',
                    'errors': first_error_message(serializer.errors), 'status': 400}
        payload = serializer.validated_data
        if payload['collector_id'] != collector.collector_id:
            return {'success': False, 'error': 'collector_id does not match the authenticated collector',
                    'status': 403}
        if payload.get('device_id') and not self.__collector_da.get_collector_device_by_code(
                collector, payload['device_id']):
            return {'success': False, 'error': f"Device {payload['device_id']} is not configured for this "
                                               f"collector", 'status': 403}

        fields = {'last_seen_at': now, 'last_ip': client_ip(meta),
                  'reported_status': payload.get('status') or COLLECTOR_STATUS_ONLINE}
        if payload.get('version'):
            fields['version'] = payload['version']
        if payload.get('message') and fields['reported_status'] != COLLECTOR_STATUS_ONLINE:
            fields.update(last_error_at=now, last_error=payload['message'][:500])
        self.__collector_da.touch_collector(collector.pk, **fields)
        if fields['reported_status'] != COLLECTOR_STATUS_ONLINE:
            self.__punch_da.create_sync_log(
                company_id=collector.company_id, collector=collector, kind=SYNC_KIND_HEARTBEAT,
                request_id=request_id_from(meta), remote_ip=client_ip(meta), status=SYNC_FAILED,
                message=(payload.get('message') or f"Collector reported {fields['reported_status']}")[:500],
                started_at=now, finished_at=now)
        return {'success': True, 'server_time': now.isoformat(), 'status': 200}

