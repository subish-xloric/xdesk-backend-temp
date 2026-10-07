""" Django only auto-imports an app's `models` module. The Attendance V2 model
definitions live in the *_models.py files next to this one (split by concern,
like platform_access); this file just makes sure Django's app loader finds them.

Unlike the legacy ptracker_access models these are managed=True and have
migrations: the attv2_* tables are new and owned by this app.
"""

from pTracker.dataaccess.attendance_v2_access.location_models import AttendanceLocation
from pTracker.dataaccess.attendance_v2_access.device_models import AttendanceDevice
from pTracker.dataaccess.attendance_v2_access.device_models import AttendanceCollector
from pTracker.dataaccess.attendance_v2_access.punch_models import AttendanceSyncLog
from pTracker.dataaccess.attendance_v2_access.punch_models import AttendanceRawPunch
from pTracker.dataaccess.attendance_v2_access.punch_models import AttendanceEvent
from pTracker.dataaccess.attendance_v2_access.shift_models import AttendanceShift
from pTracker.dataaccess.attendance_v2_access.shift_models import AttendanceShiftSchedule
from pTracker.dataaccess.attendance_v2_access.shift_models import AttendanceShiftAssignment
from pTracker.dataaccess.attendance_v2_access.daily_models import EmployeeDailyAttendance
from pTracker.dataaccess.attendance_v2_access.daily_models import AttendanceSession
from pTracker.dataaccess.attendance_v2_access.daily_models import AttendanceSettings
from pTracker.dataaccess.attendance_v2_access.audit_models import AttendanceAuditLog

__all__ = [
    'AttendanceLocation', 'AttendanceDevice', 'AttendanceCollector',
    'AttendanceSyncLog', 'AttendanceRawPunch', 'AttendanceEvent',
    'AttendanceShift', 'AttendanceShiftSchedule', 'AttendanceShiftAssignment',
    'EmployeeDailyAttendance', 'AttendanceSession', 'AttendanceSettings',
    'AttendanceAuditLog',
]
