""" Manual corrections: add a missed punch, void a wrong one, and reprocess a
date range. Requires attendance.correct and the employee must be inside the
caller's company and data scope. Original punches are never edited or deleted
- a correction is a new manual event or a void flag, both audited. """

from django.db import transaction

from pTracker.api.attendance_v2.attendance_v2_helper import active_company_id
from pTracker.api.attendance_v2.attendance_v2_helper import require_capability
from pTracker.api.attendance_v2.attendance_v2_helper import guarded
from pTracker.api.attendance_v2.attendance_v2_helper import first_error_message
from pTracker.api.attendance_v2.attendance_v2_helper import ensure_employee_visible
from pTracker.api.attendance_v2.attendance_v2_helper import visible_employee_ids
from pTracker.api.attendance_v2.attendance_v2_helper import now_local
from pTracker.api.attendance_v2.attendance_v2_helper import V2Error
from pTracker.api.attendance_v2.attendance_v2_helper import CAP_CORRECT
from pTracker.api.attendance_v2.audit_biz import record_audit
from pTracker.api.attendance_v2.attendance_query_biz import event_dict
from pTracker.api.attendance_v2.processing_biz import AttendanceProcessorBL
from pTracker.api.attendance_v2.serializers import ManualEventSerializer
from pTracker.api.attendance_v2.serializers import VoidEventSerializer
from pTracker.api.attendance_v2.serializers import ReprocessSerializer
from pTracker.dataaccess.attendance_v2_access.punch_da import PunchDA
from pTracker.dataaccess.attendance_v2_access.location_da import LocationDA
from pTracker.dataaccess.attendance_v2_access.org_da import OrgDA
from pTracker.dataaccess.attendance_v2_access.constants import EVENT_ACTIVE
from pTracker.dataaccess.attendance_v2_access.constants import EVENT_VOID
from pTracker.dataaccess.attendance_v2_access.constants import DEVICE_MANUAL


class CorrectionBL:

    def __init__(self):
        self.__punch_da = PunchDA()

    @guarded('add_manual_event')
    def add_manual_event(self, user_id, data):
        company_id = active_company_id(user_id)
        require_capability(user_id, CAP_CORRECT)
        serializer = ManualEventSerializer(data=data)
        if not serializer.is_valid():
            raise V2Error('Validation failed', 400, first_error_message(serializer.errors))
        fields = serializer.validated_data
        ensure_employee_visible(user_id, company_id, fields['employee_id'])
        if fields['event_time'] > now_local():
            raise V2Error('event_time cannot be in the future')
        location_id = fields.get('location_id')
        if location_id and not LocationDA().get_location(company_id, location_id):
            raise V2Error('location_id must be a location of your company')

        company = OrgDA().get_company(company_id)
        with transaction.atomic():
            event = self.__punch_da.create_event(
                company_id=company_id, employee_id=fields['employee_id'], event_time=fields['event_time'],
                event_type=fields['event_type'], location_id=location_id, source=DEVICE_MANUAL,
                is_manual=True, manual_reason=fields['reason'], created_by=user_id)
            AttendanceProcessorBL(company).process_new_events([event])
            record_audit(company_id, user_id, 'event', event.id, 'manual_add',
                         new={'employee_id': event.employee_id, 'event_time': event.event_time,
                              'event_type': event.event_type, 'attendance_date': event.attendance_date},
                         remarks=fields['reason'])
        return {'event': event_dict(self.__punch_da.get_event(company_id, event.id)), 'status': 201}

    @guarded('void_event')
    def void_event(self, user_id, event_id, data):
        company_id = active_company_id(user_id)
        require_capability(user_id, CAP_CORRECT)
        serializer = VoidEventSerializer(data=data)
        if not serializer.is_valid():
            raise V2Error('Validation failed', 400, first_error_message(serializer.errors))
        event = self.__punch_da.get_event(company_id, event_id)
        if event is None:
            raise V2Error('Event not found', 404)
        ensure_employee_visible(user_id, company_id, event.employee_id)
        if event.status == EVENT_VOID:
            raise V2Error('Event is already void', 409)

        company = OrgDA().get_company(company_id)
        reason = serializer.validated_data['reason']
        with transaction.atomic():
            self.__punch_da.update_event(event, status=EVENT_VOID, void_reason=reason, voided_by=user_id,
                                         voided_at=now_local())
            processor = AttendanceProcessorBL(company)
            if event.attendance_date:
                processor.process_day(event.employee_id, event.attendance_date,
                                      processor.planner(event.employee_id, event.attendance_date,
                                                        event.attendance_date))
            record_audit(company_id, user_id, 'event', event.id, 'void', old={'status': EVENT_ACTIVE},
                         new={'status': EVENT_VOID}, remarks=reason)
        return {'event': event_dict(self.__punch_da.get_event(company_id, event.id)), 'status': 200}

    @guarded('reprocess')
    def reprocess(self, user_id, data):
        company_id = active_company_id(user_id)
        require_capability(user_id, CAP_CORRECT)
        serializer = ReprocessSerializer(data=data)
        if not serializer.is_valid():
            raise V2Error('Validation failed', 400, first_error_message(serializer.errors))
        fields = serializer.validated_data
        requested = set(fields.get('employee_ids') or [])
        allowed = visible_employee_ids(user_id, company_id)
        if requested:
            for employee_id in requested:
                ensure_employee_visible(user_id, company_id, employee_id)
            employee_ids = sorted(requested)
        else:
            employee_ids = sorted(allowed if allowed is not None else OrgDA().get_member_ids(company_id))

        company = OrgDA().get_company(company_id)
        try:
            rebuilt = AttendanceProcessorBL(company).reprocess(
                employee_ids, fields['from_date'], fields['to_date'], fields['refresh_shift'])
        except ValueError as exc:
            raise V2Error(str(exc))
        record_audit(company_id, user_id, 'attendance', None, 'reprocess',
                     new={'from_date': fields['from_date'], 'to_date': fields['to_date'],
                          'employee_count': len(employee_ids), 'refresh_shift': fields['refresh_shift']})
        return {'message': f'{rebuilt} employee-day(s) recalculated', 'employees': len(employee_ids),
                'days_processed': rebuilt, 'status': 200}
