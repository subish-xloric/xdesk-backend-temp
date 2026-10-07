""" Attendance V2 - mounted at /api/attendance/v2/ (see pTracker/urls.py),
alongside and independent of the legacy /api/attendance/ endpoints. """

from django.urls import path

from pTracker.api.attendance_v2 import views
from pTracker.api.attendance_v2 import collector_views


urlpatterns = [
    # Collector contract (machine-to-machine)
    path('punches/', collector_views.CollectorPunchView.as_view(), name='attv2_collector_punches'),
    path('collector/heartbeat/', collector_views.CollectorHeartbeatView.as_view(), name='attv2_collector_heartbeat'),

    path('me/access/', views.MyAccessView.as_view(), name='attv2_my_access'),
    path('dashboard/', views.DashboardView.as_view(), name='attv2_dashboard'),
    path('employees/', views.EmployeeListView.as_view(), name='attv2_employees'),
    path('branches/', views.BranchListView.as_view(), name='attv2_branches'),

    path('locations/', views.LocationListCreateView.as_view(), name='attv2_locations'),
    path('locations/<int:location_id>/', views.LocationDetailView.as_view(), name='attv2_location_detail'),
    path('devices/', views.DeviceListCreateView.as_view(), name='attv2_devices'),
    path('devices/<int:device_id>/', views.DeviceDetailView.as_view(), name='attv2_device_detail'),
    path('collectors/', views.CollectorListCreateView.as_view(), name='attv2_collectors'),
    path('collectors/<int:pk>/', views.CollectorDetailView.as_view(), name='attv2_collector_detail'),
    path('collectors/<int:pk>/rotate-key/', views.CollectorRotateKeyView.as_view(), name='attv2_collector_rotate'),
    path('raw-punches/', views.RawPunchListView.as_view(), name='attv2_raw_punches'),
    path('sync-logs/', views.SyncLogListView.as_view(), name='attv2_sync_logs'),

    path('daily/', views.DailyAttendanceListView.as_view(), name='attv2_daily'),
    path('daily/detail/', views.DailyAttendanceDetailView.as_view(), name='attv2_daily_detail'),
    path('sessions/', views.SessionListView.as_view(), name='attv2_sessions'),
    path('events/', views.EventListView.as_view(), name='attv2_events'),
    path('corrections/', views.ManualEventView.as_view(), name='attv2_corrections'),
    path('events/<int:event_id>/void/', views.VoidEventView.as_view(), name='attv2_event_void'),
    path('reprocess/', views.ReprocessView.as_view(), name='attv2_reprocess'),
    path('check-in/', views.CheckInView.as_view(), name='attv2_check_in'),

    path('shifts/', views.ShiftListCreateView.as_view(), name='attv2_shifts'),
    path('shifts/<int:shift_id>/', views.ShiftDetailView.as_view(), name='attv2_shift_detail'),
    path('shifts/<int:shift_id>/schedule/', views.ShiftScheduleView.as_view(), name='attv2_shift_schedule'),
    path('employee-shifts/', views.ShiftAssignmentListCreateView.as_view(), name='attv2_assignments'),
    path('employee-shifts/<int:assignment_id>/', views.ShiftAssignmentDetailView.as_view(),
         name='attv2_assignment_detail'),
    path('shift-calendar/', views.ShiftCalendarView.as_view(), name='attv2_shift_calendar'),

    path('settings/', views.SettingsView.as_view(), name='attv2_settings'),
    path('audit-logs/', views.AuditLogListView.as_view(), name='attv2_audit_logs'),
]
