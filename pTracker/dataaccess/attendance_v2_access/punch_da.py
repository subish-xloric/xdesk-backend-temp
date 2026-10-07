from pTracker.dataaccess.attendance_v2_access.punch_models import AttendanceSyncLog
from pTracker.dataaccess.attendance_v2_access.punch_models import AttendanceRawPunch
from pTracker.dataaccess.attendance_v2_access.punch_models import AttendanceEvent
from pTracker.dataaccess.attendance_v2_access.constants import EVENT_ACTIVE


class PunchDA:

    # --- sync log ---------------------------------------------------------
    def create_sync_log(self, **fields):
        return AttendanceSyncLog.objects.create(**fields)

    def update_sync_log(self, sync_log, **fields):
        for key, value in fields.items():
            setattr(sync_log, key, value)
        sync_log.save()
        return sync_log

    def get_sync_logs(self, company_id, collector_id=None, status=None, start=None, end=None):
        logs = AttendanceSyncLog.objects.filter(company_id=company_id).select_related('collector', 'device')
        if collector_id:
            logs = logs.filter(collector_id=collector_id)
        if status:
            logs = logs.filter(status=status)
        if start:
            logs = logs.filter(started_at__gte=start)
        if end:
            logs = logs.filter(started_at__lt=end)
        return logs.order_by('-started_at')

    # --- raw punches ------------------------------------------------------
    def get_existing_raw_punches(self, device_id, external_ids):
        return {p.external_punch_id: p for p in AttendanceRawPunch.objects.filter(
            device_id=device_id, external_punch_id__in=list(external_ids))}

    def create_raw_punch(self, **fields):
        return AttendanceRawPunch.objects.create(**fields)

    def update_raw_punch(self, raw_punch, **fields):
        for key, value in fields.items():
            setattr(raw_punch, key, value)
        raw_punch.save(update_fields=list(fields.keys()))
        return raw_punch

    def get_raw_punches(self, company_id, filters):
        punches = AttendanceRawPunch.objects.filter(company_id=company_id).select_related(
            'device', 'collector', 'employee', 'location')
        if filters.get('device_id'):
            punches = punches.filter(device_id=filters['device_id'])
        if filters.get('collector_id'):
            punches = punches.filter(collector_id=filters['collector_id'])
        if filters.get('employee_id'):
            punches = punches.filter(employee_id=filters['employee_id'])
        if filters.get('status'):
            punches = punches.filter(status=filters['status'])
        if filters.get('start'):
            punches = punches.filter(punch_time__gte=filters['start'])
        if filters.get('end'):
            punches = punches.filter(punch_time__lt=filters['end'])
        if filters.get('search'):
            punches = punches.filter(external_employee_id__icontains=filters['search'])
        return punches.order_by('-punch_time', '-id')

    def get_unresolved_raw_punches(self, company_id, employee_codes=None):
        punches = AttendanceRawPunch.objects.filter(company_id=company_id, status='unresolved_employee')
        if employee_codes is not None:
            punches = punches.filter(external_employee_id__in=list(employee_codes))
        return punches.select_related('device')

    # --- events -----------------------------------------------------------
    def create_event(self, **fields):
        return AttendanceEvent.objects.create(**fields)

    def get_event(self, company_id, event_id):
        return AttendanceEvent.objects.filter(company_id=company_id, pk=event_id).first()

    def update_event(self, event, **fields):
        for key, value in fields.items():
            setattr(event, key, value)
        event.save(update_fields=list(fields.keys()))
        return event

    def get_active_events_between(self, company_id, employee_id, start, end):
        return list(AttendanceEvent.objects.filter(
            company_id=company_id, employee_id=employee_id, status=EVENT_ACTIVE,
            event_time__gte=start, event_time__lt=end,
        ).order_by('event_time', 'id'))

    def get_active_events_for_date(self, company_id, employee_id, attendance_date):
        return list(AttendanceEvent.objects.filter(
            company_id=company_id, employee_id=employee_id, status=EVENT_ACTIVE,
            attendance_date=attendance_date,
        ).order_by('event_time', 'id'))

    def set_event_dates(self, event_ids, attendance_date):
        AttendanceEvent.objects.filter(pk__in=list(event_ids)).update(attendance_date=attendance_date)

    def get_events(self, company_id, employee_ids, start_date, end_date, include_void=True):
        events = AttendanceEvent.objects.filter(
            company_id=company_id, employee_id__in=list(employee_ids),
            attendance_date__range=[start_date, end_date],
        ).select_related('device', 'location')
        if not include_void:
            events = events.filter(status=EVENT_ACTIVE)
        return events.order_by('event_time', 'id')

    def get_last_active_event(self, company_id, employee_id, since):
        return AttendanceEvent.objects.filter(
            company_id=company_id, employee_id=employee_id, status=EVENT_ACTIVE, event_time__gte=since,
        ).order_by('-event_time', '-id').first()
