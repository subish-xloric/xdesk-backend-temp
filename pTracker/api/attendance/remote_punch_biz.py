from datetime import datetime

from pTracker.api.attendance_v2.attendance_v2_helper import active_company_id
from pTracker.api.attendance_v2.attendance_v2_helper import guarded
from pTracker.api.attendance_v2.attendance_v2_helper import now_local
from pTracker.api.attendance_v2.attendance_v2_helper import V2Error
from pTracker.api.attendance_v2.checkin_biz import SelfCheckInBL
from pTracker.dataaccess.attendance_v2_access.constants import DEVICE_MOBILE
from pTracker.dataaccess.attendance_v2_access.constants import DEVICE_WEB
from pTracker.dataaccess.attendance_v2_access.constants import PUNCH_IN
from pTracker.dataaccess.attendance_v2_access.constants import PUNCH_OUT
from pTracker.dataaccess.attendance_v2_access.device_da import DeviceDA
from pTracker.dataaccess.attendance_v2_access.org_da import OrgDA

# The punch button is hidden this long after a punch (same as the legacy flow).
PUNCH_BUTTON_COOLDOWN_SECONDS = 180


class RemotePunchBL():
    """ Work-from-home remote punch on Attendance V2.

    Replaces the legacy flow that wrote straight into the eSSL biometric DB.
    The punch is recorded through V2's self check-in on one of the company's
    web/mobile check-in devices, so it shows up in V2 attendance, the
    dashboard and reports. As before, it needs an approved WFH request for
    today. Responses: {'message', 'status'} or {'error', 'status'}.
    """

    @guarded('remote_punch')
    def punch(self, user_id, direction, channel):
        punch_type = {'in': PUNCH_IN, 'out': PUNCH_OUT}.get(str(direction or '').strip().lower())
        if punch_type is None:
            raise V2Error('direction must be IN or OUT', 400)
        if not OrgDA().has_approved_wfh(user_id, now_local().date()):
            raise V2Error('An approved work-from-home request for today is required for a remote punch', 403)

        device = self.__remote_device(active_company_id(user_id), channel)
        result = SelfCheckInBL().check_in(user_id, {'channel': device.device_type, 'device_id': device.id,
                                                    'punch_type': punch_type})
        if result.get('error'):
            return {'error': result['error'], 'status': result.get('status', 400)}
        verb = 'in' if punch_type == PUNCH_IN else 'out'
        return {'message': f'You successfully punched {verb} remotely.', 'status': 200}

    @guarded('remote_punch_check')
    def punch_check(self, user_id):
        """ Next direction for the punch button ('IN'/'OUT') and whether to show
        it: hidden right after a punch and when remote check-in isn't set up. """
        status = SelfCheckInBL().status(user_id)
        if status.get('error'):
            return {'error': status['error'], 'status': status.get('status', 400)}
        is_display = bool(status.get('enabled'))
        last_punch = status.get('last_punch_time')
        if last_punch:
            elapsed = (now_local() - datetime.strptime(last_punch, '%Y-%m-%dT%H:%M:%S')).total_seconds()
            if elapsed < PUNCH_BUTTON_COOLDOWN_SECONDS:
                is_display = False
        return {'direction': status.get('suggested_punch_type', PUNCH_IN), 'is_display': is_display,
                'status': 200}

    def __remote_device(self, company_id, channel):
        """ The company's check-in device for the client's channel, falling back
        to its other self check-in type (a company may configure only one). """
        preferred = DEVICE_MOBILE if channel == DEVICE_MOBILE else DEVICE_WEB
        fallback = DEVICE_WEB if preferred == DEVICE_MOBILE else DEVICE_MOBILE
        for device_type in (preferred, fallback):
            devices = DeviceDA().get_devices(company_id, device_types=[device_type])
            if devices:
                return devices[0]
        raise V2Error('Remote punch is not enabled for your company', 403)
