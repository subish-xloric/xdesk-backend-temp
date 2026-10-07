""" Web / mobile check-in: the employee punches through the application. It is
just another source - the punch becomes a raw punch + event exactly like a
collector punch and goes through the same engine. The employee and company
come from the JWT and the verified active company, never from the body. """

import uuid

from django.db import transaction

from pTracker.api.attendance_v2.attendance_v2_helper import active_company_id
from pTracker.api.attendance_v2.attendance_v2_helper import guarded
from pTracker.api.attendance_v2.attendance_v2_helper import first_error_message
from pTracker.api.attendance_v2.attendance_v2_helper import now_local
from pTracker.api.attendance_v2.attendance_v2_helper import fmt_dt
from pTracker.api.attendance_v2.attendance_v2_helper import V2Error
from pTracker.api.attendance_v2.attendance_query_biz import daily_dict
from pTracker.api.attendance_v2.day_plan_biz import RuleSettings
from pTracker.api.attendance_v2.processing_biz import AttendanceProcessorBL
from pTracker.api.attendance_v2.serializers import CheckInSerializer
from pTracker.dataaccess.attendance_v2_access.device_da import DeviceDA
from pTracker.dataaccess.attendance_v2_access.punch_da import PunchDA
from pTracker.dataaccess.attendance_v2_access.daily_da import DailyDA
from pTracker.dataaccess.attendance_v2_access.org_da import OrgDA
from pTracker.dataaccess.attendance_v2_access.constants import SELF_CHECKIN_DEVICE_TYPES
from pTracker.dataaccess.attendance_v2_access.constants import PUNCH_IN
from pTracker.dataaccess.attendance_v2_access.constants import PUNCH_OUT
from pTracker.dataaccess.attendance_v2_access.constants import RAW_PROCESSED
from pTracker.dataaccess.attendance_v2_access.constants import SESSION_MISSING_OUT


class SelfCheckInBL:

    def __init__(self):
        self.__device_da = DeviceDA()
        self.__punch_da = PunchDA()

    @guarded('checkin_status')
    def status(self, user_id):
        company_id = active_company_id(user_id)
        company = OrgDA().get_company(company_id)
        now = now_local()
        processor = AttendanceProcessorBL(company)
        work_date = processor.planner(user_id, now.date(), now.date()).work_date_for(now)
        daily = DailyDA().get_daily(company_id, user_id, work_date)
        open_session = bool(daily) and DailyDA().get_sessions(
            company_id, {user_id}, work_date, work_date).filter(status=SESSION_MISSING_OUT).exists()
        devices = self.__device_da.get_devices(company_id, device_types=SELF_CHECKIN_DEVICE_TYPES)
        last_event = self.__punch_da.get_last_active_event(company_id, user_id, now.replace(hour=0, minute=0,
                                                                                           second=0))
        return {
            'work_date': work_date.isoformat(),
            'suggested_punch_type': PUNCH_OUT if open_session else PUNCH_IN,
            'last_punch_time': fmt_dt(last_event.event_time) if last_event else None,
            'daily': daily_dict(daily) if daily else None,
            'devices': [{'id': d.id, 'name': d.name, 'device_type': d.device_type,
                         'requires_wfh_approval': d.requires_wfh_approval} for d in devices],
            'enabled': bool(devices),
            'status': 200,
        }

    @guarded('checkin')
    def check_in(self, user_id, data):
        company_id = active_company_id(user_id)
        serializer = CheckInSerializer(data=data)
        if not serializer.is_valid():
            raise V2Error('Validation failed', 400, first_error_message(serializer.errors))
        fields = serializer.validated_data
        device = self._device(company_id, fields.get('device_id'), fields['channel'])
        now = now_local()
        if device.requires_wfh_approval and not OrgDA().has_approved_wfh(user_id, now.date()):
            raise V2Error('An approved work-from-home request is required for remote check-in', 403)

        company = OrgDA().get_company(company_id)
        processor = AttendanceProcessorBL(company)
        rules = RuleSettings.from_row(DailyDA().get_settings(company_id))
        punch_type = fields.get('punch_type') or self.status(user_id).get('suggested_punch_type', PUNCH_IN)
        last = self.__punch_da.get_last_active_event(company_id, user_id, now.replace(hour=0, minute=0, second=0))
        window = max(rules.duplicate_punch_window_minutes, 1)
        if last and last.event_type == punch_type and (now - last.event_time).total_seconds() < window * 60:
            raise V2Error(f'You already punched {punch_type} a moment ago', 409)

        with transaction.atomic():
            raw = self.__punch_da.create_raw_punch(
                company_id=company_id, device=device, employee_id=user_id,
                external_employee_id=str(user_id), external_punch_id=f'self:{uuid.uuid4().hex}',
                punch_time=now, raw_punch_type=punch_type, punch_type=punch_type, source=device.device_type,
                location=device.location, raw_data={'channel': fields['channel']}, received_at=now,
                status=RAW_PROCESSED, processed_at=now)
            event = self.__punch_da.create_event(
                company_id=company_id, employee_id=user_id, event_time=now, event_type=punch_type,
                location_id=device.location_id, device_id=device.id, source=device.device_type, raw_punch=raw)
            processor.process_new_events([event])
        daily = DailyDA().get_daily(company_id, user_id, event.attendance_date)
        return {'message': f'Punched {punch_type} at {now.strftime("%H:%M")}', 'punch_type': punch_type,
                'daily': daily_dict(daily) if daily else None, 'status': 201}

    def _device(self, company_id, device_id, channel):
        if device_id:
            device = self.__device_da.get_device(company_id, device_id)
            if device is None or not device.is_active or device.device_type not in SELF_CHECKIN_DEVICE_TYPES:
                raise V2Error('Check-in device not found', 404)
            return device
        devices = list(self.__device_da.get_devices(company_id, device_types=[channel]))
        if not devices:
            raise V2Error(f'{channel.capitalize()} check-in is not enabled for your company', 403)
        return devices[0]
