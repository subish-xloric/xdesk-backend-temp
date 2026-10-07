""" Choice values shared by the Attendance V2 models and business layer.

Nothing in here is vendor specific: device types are only labels used for
display, filtering and to decide which ingestion channel a device may use
(collector vs web/mobile check-in). Attendance rules never branch on them.
"""

LOCATION_TYPES = (
    ('company', 'Company'),
    ('building', 'Building'),
    ('floor', 'Floor'),
    ('area', 'Area'),
    ('room', 'Room'),
)

DEVICE_ESSL = 'essl'
DEVICE_ZKTECO = 'zkteco'
DEVICE_OTHER_BIOMETRIC = 'other_biometric'
DEVICE_WEB = 'web'
DEVICE_MOBILE = 'mobile'
DEVICE_API = 'api'
DEVICE_MANUAL = 'manual'
DEVICE_TYPES = (
    (DEVICE_ESSL, 'eSSL'),
    (DEVICE_ZKTECO, 'ZKTeco'),
    (DEVICE_OTHER_BIOMETRIC, 'Other biometric'),
    (DEVICE_WEB, 'Web check-in'),
    (DEVICE_MOBILE, 'Mobile check-in'),
    (DEVICE_API, 'API integration'),
    (DEVICE_MANUAL, 'Manual'),
)
# Devices whose punches arrive through an external collector.
COLLECTOR_DEVICE_TYPES = (DEVICE_ESSL, DEVICE_ZKTECO, DEVICE_OTHER_BIOMETRIC, DEVICE_API)
# Devices an employee punches on through the application itself.
SELF_CHECKIN_DEVICE_TYPES = (DEVICE_WEB, DEVICE_MOBILE)

COLLECTOR_STATUS_UNKNOWN = 'unknown'
COLLECTOR_STATUS_ONLINE = 'online'
COLLECTOR_STATUS_OFFLINE = 'offline'
COLLECTOR_STATUS_ERROR = 'error'
COLLECTOR_STATUSES = (
    (COLLECTOR_STATUS_UNKNOWN, 'Unknown'),
    (COLLECTOR_STATUS_ONLINE, 'Online'),
    (COLLECTOR_STATUS_OFFLINE, 'Offline'),
    (COLLECTOR_STATUS_ERROR, 'Error'),
)

PUNCH_IN = 'IN'
PUNCH_OUT = 'OUT'
PUNCH_UNSPECIFIED = 'UNSPECIFIED'
PUNCH_TYPES = (
    (PUNCH_IN, 'In'),
    (PUNCH_OUT, 'Out'),
    (PUNCH_UNSPECIFIED, 'Unspecified'),
)

RAW_PENDING = 'pending'
RAW_PROCESSED = 'processed'
RAW_UNRESOLVED_EMPLOYEE = 'unresolved_employee'
RAW_ERROR = 'error'
RAW_STATUSES = (
    (RAW_PENDING, 'Pending'),
    (RAW_PROCESSED, 'Processed'),
    (RAW_UNRESOLVED_EMPLOYEE, 'Employee not identified'),
    (RAW_ERROR, 'Error'),
)

EVENT_ACTIVE = 'active'
EVENT_VOID = 'void'
EVENT_STATUSES = (
    (EVENT_ACTIVE, 'Active'),
    (EVENT_VOID, 'Void'),
)

SESSION_COMPLETE = 'complete'
SESSION_MISSING_OUT = 'missing_out'
SESSION_MISSING_IN = 'missing_in'
SESSION_STATUSES = (
    (SESSION_COMPLETE, 'Complete'),
    (SESSION_MISSING_OUT, 'Missing OUT'),
    (SESSION_MISSING_IN, 'Missing IN'),
)

DAY_WORKING = 'working'
DAY_WEEKLY_OFF = 'weekly_off'
DAY_HOLIDAY = 'holiday'
DAY_TYPES = (
    (DAY_WORKING, 'Working day'),
    (DAY_WEEKLY_OFF, 'Weekly off'),
    (DAY_HOLIDAY, 'Holiday'),
)

STATUS_PRESENT = 'present'
STATUS_HALF_DAY = 'half_day'
STATUS_ABSENT = 'absent'
STATUS_LEAVE = 'leave'
STATUS_HOLIDAY = 'holiday'
STATUS_WEEKLY_OFF = 'weekly_off'
STATUS_INCOMPLETE = 'incomplete'
STATUS_NOT_STARTED = 'not_started'
DAILY_STATUSES = (
    (STATUS_PRESENT, 'Present'),
    (STATUS_HALF_DAY, 'Half day'),
    (STATUS_ABSENT, 'Absent'),
    (STATUS_LEAVE, 'Leave'),
    (STATUS_HOLIDAY, 'Holiday'),
    (STATUS_WEEKLY_OFF, 'Weekly off'),
    (STATUS_INCOMPLETE, 'Incomplete (missing punch)'),
    (STATUS_NOT_STARTED, 'Not started'),
)

LEAVE_NONE = 'none'
LEAVE_FULL = 'full'
LEAVE_HALF = 'half'
LEAVE_PORTIONS = (
    (LEAVE_NONE, 'None'),
    (LEAVE_FULL, 'Full day'),
    (LEAVE_HALF, 'Half day'),
)

OVERTIME_AFTER_SHIFT_END = 'after_shift_end'
OVERTIME_BEYOND_EXPECTED = 'beyond_expected'
OVERTIME_BASES = (
    (OVERTIME_AFTER_SHIFT_END, 'Time worked after shift end'),
    (OVERTIME_BEYOND_EXPECTED, 'Work minutes beyond expected work minutes'),
)

SCOPE_EMPLOYEE = 'employee'
SCOPE_TEAM = 'team'
SCOPE_BRANCH = 'branch'
SCOPE_COMPANY = 'company'
ASSIGNMENT_SCOPES = (
    (SCOPE_EMPLOYEE, 'Employee'),
    (SCOPE_TEAM, 'Team (reporting lead)'),
    (SCOPE_BRANCH, 'Branch'),
    (SCOPE_COMPANY, 'Company default'),
)
# Shift resolution order for an attendance date: most specific wins.
ASSIGNMENT_PRIORITY = (SCOPE_EMPLOYEE, SCOPE_TEAM, SCOPE_BRANCH, SCOPE_COMPANY)

UNSPECIFIED_ALTERNATE = 'alternate'
UNSPECIFIED_FIRST_LAST = 'first_last'
UNSPECIFIED_MODES = (
    (UNSPECIFIED_ALTERNATE, 'Alternate IN / OUT'),
    (UNSPECIFIED_FIRST_LAST, 'First punch IN, last punch OUT'),
)

SYNC_SUCCESS = 'success'
SYNC_PARTIAL = 'partial'
SYNC_FAILED = 'failed'
SYNC_REJECTED = 'rejected'
SYNC_STATUSES = (
    (SYNC_SUCCESS, 'Success'),
    (SYNC_PARTIAL, 'Partial'),
    (SYNC_FAILED, 'Failed'),
    (SYNC_REJECTED, 'Rejected'),
)

SYNC_KIND_PUNCHES = 'punches'
SYNC_KIND_HEARTBEAT = 'heartbeat'
SYNC_KINDS = (
    (SYNC_KIND_PUNCHES, 'Punch batch'),
    (SYNC_KIND_HEARTBEAT, 'Heartbeat'),
)

WEEKDAYS = (
    (0, 'Monday'),
    (1, 'Tuesday'),
    (2, 'Wednesday'),
    (3, 'Thursday'),
    (4, 'Friday'),
    (5, 'Saturday'),
    (6, 'Sunday'),
)
