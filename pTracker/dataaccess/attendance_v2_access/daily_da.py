from django.db.models import Count

from pTracker.dataaccess.attendance_v2_access.daily_models import EmployeeDailyAttendance
from pTracker.dataaccess.attendance_v2_access.daily_models import AttendanceSession
from pTracker.dataaccess.attendance_v2_access.daily_models import AttendanceSettings


class DailyDA:

    # --- daily summary ----------------------------------------------------
    def lock_daily(self, company_id, employee_id, attendance_date, defaults):
        """ Gets or creates the employee/date row and locks it for the rest of the
        transaction, so two concurrent batches for the same employee/date
        rebuild its sessions one after the other. """
        EmployeeDailyAttendance.objects.get_or_create(
            company_id=company_id, employee_id=employee_id, attendance_date=attendance_date,
            defaults=defaults)
        return EmployeeDailyAttendance.objects.select_for_update().get(
            company_id=company_id, employee_id=employee_id, attendance_date=attendance_date)

    def delete_daily(self, daily):
        daily.delete()

    def get_stored_snapshots(self, company_id, employee_id, start_date, end_date):
        return dict(EmployeeDailyAttendance.objects.filter(
            company_id=company_id, employee_id=employee_id, attendance_date__range=[start_date, end_date],
            shift_snapshot__isnull=False,
        ).values_list('attendance_date', 'shift_snapshot'))

    def get_daily(self, company_id, employee_id, attendance_date):
        return EmployeeDailyAttendance.objects.filter(
            company_id=company_id, employee_id=employee_id, attendance_date=attendance_date,
        ).select_related('shift', 'first_in_location', 'last_out_location').first()

    def save_daily(self, daily, **fields):
        for key, value in fields.items():
            setattr(daily, key, value)
        daily.save()
        return daily

    def get_daily_list(self, company_id, employee_ids, start_date, end_date, status=None):
        rows = EmployeeDailyAttendance.objects.filter(
            company_id=company_id, attendance_date__range=[start_date, end_date],
        ).select_related('shift', 'employee', 'first_in_location', 'last_out_location')
        if employee_ids is not None:
            rows = rows.filter(employee_id__in=list(employee_ids))
        if status:
            rows = rows.filter(status=status)
        return rows.order_by('-attendance_date', 'employee__first_name')

    def count_by_status(self, company_id, employee_ids, attendance_date):
        rows = EmployeeDailyAttendance.objects.filter(company_id=company_id, attendance_date=attendance_date)
        if employee_ids is not None:
            rows = rows.filter(employee_id__in=list(employee_ids))
        counts = dict(rows.values_list('status').annotate(total=Count('id')))
        counts['late'] = rows.filter(is_late=True).count()
        counts['missing_punch'] = rows.filter(has_missing_punch=True).count()
        return counts

    # --- sessions ---------------------------------------------------------
    def replace_sessions(self, daily, sessions):
        AttendanceSession.objects.filter(daily=daily).delete()
        AttendanceSession.objects.bulk_create([AttendanceSession(daily=daily, **s) for s in sessions])

    def get_sessions(self, company_id, employee_ids, start_date, end_date):
        sessions = AttendanceSession.objects.filter(
            company_id=company_id, attendance_date__range=[start_date, end_date],
        ).select_related('employee', 'check_in_location', 'check_out_location')
        if employee_ids is not None:
            sessions = sessions.filter(employee_id__in=list(employee_ids))
        return sessions.order_by('-attendance_date', 'employee_id', 'sequence')

    # --- company settings -------------------------------------------------
    def get_settings(self, company_id):
        return AttendanceSettings.objects.filter(company_id=company_id).first()

    def save_settings(self, company_id, updated_by, **fields):
        settings_row, _ = AttendanceSettings.objects.get_or_create(company_id=company_id)
        for key, value in fields.items():
            setattr(settings_row, key, value)
        settings_row.updated_by = updated_by
        settings_row.save()
        return settings_row
