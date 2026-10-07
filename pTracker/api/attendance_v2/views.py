""" Attendance V2 employee/admin endpoints (JWT). Views stay thin: the company
comes from the verified active company (ModuleGateMiddleware) and all
permission and scope checks happen in the biz layer. """

from rest_framework.permissions import IsAuthenticated
from rest_framework.response import Response
from rest_framework.views import APIView
from rest_framework_simplejwt.authentication import JWTAuthentication as JSONWebTokenAuthentication

from pTracker.api.attendance_v2.location_biz import LocationBL
from pTracker.api.attendance_v2.device_biz import DeviceBL
from pTracker.api.attendance_v2.device_biz import CollectorBL
from pTracker.api.attendance_v2.shift_biz import ShiftBL
from pTracker.api.attendance_v2.shift_biz import SettingsBL
from pTracker.api.attendance_v2.attendance_query_biz import AttendanceQueryBL
from pTracker.api.attendance_v2.correction_biz import CorrectionBL
from pTracker.api.attendance_v2.checkin_biz import SelfCheckInBL
from pTracker.api.attendance_v2.audit_biz import AuditBL


def respond(response):
    return Response(response, status=response.get('status', 200))


class V2View(APIView):
    authentication_classes = [JSONWebTokenAuthentication]
    permission_classes = [IsAuthenticated]


class MyAccessView(V2View):
    def get(self, request):
        return respond(AttendanceQueryBL().my_access(request.user.id))


class DashboardView(V2View):
    def get(self, request):
        return respond(AttendanceQueryBL().dashboard(request.user.id, request.query_params))


class EmployeeListView(V2View):
    def get(self, request):
        return respond(AttendanceQueryBL().list_employees(request.user.id, request.query_params))


class BranchListView(V2View):
    def get(self, request):
        return respond(AttendanceQueryBL().list_branches(request.user.id))


# --- locations / devices / collectors ---------------------------------------

class LocationListCreateView(V2View):
    def get(self, request):
        return respond(LocationBL().list_locations(request.user.id, request.query_params))

    def post(self, request):
        return respond(LocationBL().create_location(request.user.id, request.data))


class LocationDetailView(V2View):
    def get(self, request, location_id):
        return respond(LocationBL().get_location(request.user.id, location_id))

    def put(self, request, location_id):
        return respond(LocationBL().update_location(request.user.id, location_id, request.data))

    def delete(self, request, location_id):
        return respond(LocationBL().deactivate_location(request.user.id, location_id))


class DeviceListCreateView(V2View):
    def get(self, request):
        return respond(DeviceBL().list_devices(request.user.id, request.query_params))

    def post(self, request):
        return respond(DeviceBL().create_device(request.user.id, request.data))


class DeviceDetailView(V2View):
    def get(self, request, device_id):
        return respond(DeviceBL().get_device(request.user.id, device_id))

    def put(self, request, device_id):
        return respond(DeviceBL().update_device(request.user.id, device_id, request.data))

    def delete(self, request, device_id):
        return respond(DeviceBL().deactivate_device(request.user.id, device_id))


class CollectorListCreateView(V2View):
    def get(self, request):
        return respond(CollectorBL().list_collectors(request.user.id, request.query_params))

    def post(self, request):
        return respond(CollectorBL().create_collector(request.user.id, request.data))


class CollectorDetailView(V2View):
    def get(self, request, pk):
        return respond(CollectorBL().get_collector(request.user.id, pk))

    def put(self, request, pk):
        return respond(CollectorBL().update_collector(request.user.id, pk, request.data))

    def delete(self, request, pk):
        return respond(CollectorBL().deactivate_collector(request.user.id, pk))


class CollectorRotateKeyView(V2View):
    def post(self, request, pk):
        return respond(CollectorBL().rotate_key(request.user.id, pk))


class RawPunchListView(V2View):
    def get(self, request):
        return respond(AttendanceQueryBL().list_raw_punches(request.user.id, request.query_params))


class SyncLogListView(V2View):
    def get(self, request):
        return respond(AttendanceQueryBL().list_sync_logs(request.user.id, request.query_params))


# --- attendance ---------------------------------------------------------------

class DailyAttendanceListView(V2View):
    def get(self, request):
        return respond(AttendanceQueryBL().list_daily(request.user.id, request.query_params))


class DailyAttendanceDetailView(V2View):
    def get(self, request):
        return respond(AttendanceQueryBL().daily_detail(request.user.id, request.query_params))


class SessionListView(V2View):
    def get(self, request):
        return respond(AttendanceQueryBL().list_sessions(request.user.id, request.query_params))


class EventListView(V2View):
    def get(self, request):
        return respond(AttendanceQueryBL().list_events(request.user.id, request.query_params))


class ManualEventView(V2View):
    def post(self, request):
        return respond(CorrectionBL().add_manual_event(request.user.id, request.data))


class VoidEventView(V2View):
    def post(self, request, event_id):
        return respond(CorrectionBL().void_event(request.user.id, event_id, request.data))


class ReprocessView(V2View):
    def post(self, request):
        return respond(CorrectionBL().reprocess(request.user.id, request.data))


class CheckInView(V2View):
    def get(self, request):
        return respond(SelfCheckInBL().status(request.user.id))

    def post(self, request):
        return respond(SelfCheckInBL().check_in(request.user.id, request.data))


# --- shift management ---------------------------------------------------------

class ShiftListCreateView(V2View):
    def get(self, request):
        return respond(ShiftBL().list_shifts(request.user.id, request.query_params))

    def post(self, request):
        return respond(ShiftBL().create_shift(request.user.id, request.data))


class ShiftDetailView(V2View):
    def get(self, request, shift_id):
        return respond(ShiftBL().get_shift(request.user.id, shift_id))

    def put(self, request, shift_id):
        return respond(ShiftBL().update_shift(request.user.id, shift_id, request.data))

    def patch(self, request, shift_id):
        return respond(ShiftBL().update_shift(request.user.id, shift_id, request.data, partial=True))

    def delete(self, request, shift_id):
        return respond(ShiftBL().deactivate_shift(request.user.id, shift_id))


class ShiftScheduleView(V2View):
    def get(self, request, shift_id):
        return respond(ShiftBL().get_schedule(request.user.id, shift_id))

    def put(self, request, shift_id):
        return respond(ShiftBL().replace_schedule(request.user.id, shift_id, request.data))


class ShiftAssignmentListCreateView(V2View):
    def get(self, request):
        return respond(ShiftBL().list_assignments(request.user.id, request.query_params))

    def post(self, request):
        return respond(ShiftBL().create_assignment(request.user.id, request.data))


class ShiftAssignmentDetailView(V2View):
    def patch(self, request, assignment_id):
        return respond(ShiftBL().end_assignment(request.user.id, assignment_id, request.data))

    def delete(self, request, assignment_id):
        return respond(ShiftBL().delete_assignment(request.user.id, assignment_id))


class ShiftCalendarView(V2View):
    def get(self, request):
        return respond(ShiftBL().calendar(request.user.id, request.query_params))


class SettingsView(V2View):
    def get(self, request):
        return respond(SettingsBL().get_settings(request.user.id))

    def put(self, request):
        return respond(SettingsBL().update_settings(request.user.id, request.data))


class AuditLogListView(V2View):
    def get(self, request):
        return respond(AuditBL().list_logs(request.user.id, request.query_params))
