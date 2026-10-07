""" Input validation for Attendance V2. Plain serializers only - they check
shape and ranges; ownership/company checks live in the biz layer, which is
the only place that knows the caller's company. """

import json

from rest_framework import serializers

from pTracker.api.attendance_v2.attendance_v2_helper import parse_iso_datetime
from pTracker.api.attendance_v2.attendance_v2_helper import v2_setting
from pTracker.dataaccess.attendance_v2_access.constants import LOCATION_TYPES
from pTracker.dataaccess.attendance_v2_access.constants import DEVICE_TYPES
from pTracker.dataaccess.attendance_v2_access.constants import COLLECTOR_STATUSES
from pTracker.dataaccess.attendance_v2_access.constants import PUNCH_IN
from pTracker.dataaccess.attendance_v2_access.constants import PUNCH_OUT
from pTracker.dataaccess.attendance_v2_access.constants import PUNCH_UNSPECIFIED
from pTracker.dataaccess.attendance_v2_access.constants import OVERTIME_BASES
from pTracker.dataaccess.attendance_v2_access.constants import ASSIGNMENT_SCOPES
from pTracker.dataaccess.attendance_v2_access.constants import UNSPECIFIED_MODES
from pTracker.dataaccess.attendance_v2_access.constants import SELF_CHECKIN_DEVICE_TYPES

CODE_VALIDATOR = serializers.RegexField(r'^[A-Za-z0-9][A-Za-z0-9._-]{0,49}$', max_length=50)

# Accepted spellings of a direction; anything else is stored as raw type only.
PUNCH_TYPE_ALIASES = {
    'IN': PUNCH_IN, 'I': PUNCH_IN, 'CHECKIN': PUNCH_IN, 'CHECK_IN': PUNCH_IN,
    'OUT': PUNCH_OUT, 'O': PUNCH_OUT, 'CHECKOUT': PUNCH_OUT, 'CHECK_OUT': PUNCH_OUT,
    'UNSPECIFIED': PUNCH_UNSPECIFIED, 'UNKNOWN': PUNCH_UNSPECIFIED, '': PUNCH_UNSPECIFIED,
}


def normalize_punch_type(value):
    if value is None:
        return PUNCH_UNSPECIFIED
    return PUNCH_TYPE_ALIASES.get(str(value).strip().upper().replace(' ', '_'), PUNCH_UNSPECIFIED)


class IsoDateTimeField(serializers.Field):
    def to_internal_value(self, data):
        try:
            return parse_iso_datetime(data)
        except ValueError as exc:
            raise serializers.ValidationError(str(exc))

    def to_representation(self, value):
        return value.isoformat() if value else None


# --- collector contract -------------------------------------------------

class PunchItemSerializer(serializers.Serializer):
    employee_code = serializers.CharField(max_length=64, trim_whitespace=True)
    punch_time = IsoDateTimeField()
    punch_type = serializers.CharField(max_length=32, required=False, allow_null=True, allow_blank=True)
    external_punch_id = serializers.CharField(max_length=120, required=False, allow_null=True,
                                              allow_blank=True)
    # Optional per-punch overrides of the batch-level values.
    device_id = serializers.CharField(max_length=50, required=False)
    location_code = serializers.CharField(max_length=50, required=False, allow_null=True, allow_blank=True)
    source = serializers.CharField(max_length=20, required=False, allow_blank=True)
    raw_data = serializers.DictField(required=False, allow_null=True)

    def validate_raw_data(self, value):
        if value is not None and len(json.dumps(value, default=str)) > v2_setting('MAX_RAW_DATA_BYTES'):
            raise serializers.ValidationError('raw_data is too large')
        return value


class PunchBatchSerializer(serializers.Serializer):
    collector_id = serializers.CharField(max_length=64)
    device_id = serializers.CharField(max_length=50, required=False)
    location_code = serializers.CharField(max_length=50, required=False, allow_null=True, allow_blank=True)
    source = serializers.CharField(max_length=20, required=False, allow_blank=True)
    # Items are validated one by one in the biz layer, so a single bad punch is
    # reported against its external_punch_id instead of failing the whole batch.
    punches = serializers.ListField(child=serializers.DictField(), allow_empty=False)

    def validate_punches(self, value):
        limit = v2_setting('MAX_BATCH_SIZE')
        if len(value) > limit:
            raise serializers.ValidationError(f'At most {limit} punches per request')
        return value


class HeartbeatSerializer(serializers.Serializer):
    collector_id = serializers.CharField(max_length=64)
    version = serializers.CharField(max_length=50, required=False, allow_blank=True)
    device_id = serializers.CharField(max_length=50, required=False, allow_blank=True)
    status = serializers.ChoiceField(choices=[c[0] for c in COLLECTOR_STATUSES], required=False)
    message = serializers.CharField(max_length=500, required=False, allow_blank=True)


# --- configuration --------------------------------------------------------

class LocationSerializer(serializers.Serializer):
    name = serializers.CharField(max_length=150)
    code = CODE_VALIDATOR
    location_type = serializers.ChoiceField(choices=[c[0] for c in LOCATION_TYPES])
    parent_id = serializers.IntegerField(required=False, allow_null=True)
    branch_id = serializers.IntegerField(required=False, allow_null=True)
    is_active = serializers.BooleanField(required=False)


class DeviceSerializer(serializers.Serializer):
    name = serializers.CharField(max_length=150)
    code = CODE_VALIDATOR
    device_type = serializers.ChoiceField(choices=[c[0] for c in DEVICE_TYPES])
    location_id = serializers.IntegerField(required=False, allow_null=True)
    serial_number = serializers.CharField(max_length=100, required=False, allow_null=True, allow_blank=True)
    ip_address = serializers.IPAddressField(required=False, allow_null=True, allow_blank=True)
    requires_wfh_approval = serializers.BooleanField(required=False)
    is_active = serializers.BooleanField(required=False)


class CollectorSerializer(serializers.Serializer):
    collector_id = serializers.RegexField(r'^[A-Za-z0-9][A-Za-z0-9._-]{2,63}$', max_length=64)
    name = serializers.CharField(max_length=150)
    collector_type = serializers.ChoiceField(choices=[c[0] for c in DEVICE_TYPES])
    device_ids = serializers.ListField(child=serializers.IntegerField(), required=False)
    is_active = serializers.BooleanField(required=False)


class ShiftSerializer(serializers.Serializer):
    name = serializers.CharField(max_length=100)
    code = serializers.RegexField(r'^[A-Za-z0-9][A-Za-z0-9._-]{0,29}$', max_length=30)
    description = serializers.CharField(max_length=500, required=False, allow_null=True, allow_blank=True)
    start_time = serializers.TimeField()
    end_time = serializers.TimeField()
    expected_work_minutes = serializers.IntegerField(min_value=1, max_value=1440)
    grace_in_minutes = serializers.IntegerField(min_value=0, max_value=720, required=False)
    grace_out_minutes = serializers.IntegerField(min_value=0, max_value=720, required=False)
    break_minutes = serializers.IntegerField(min_value=0, max_value=720, required=False)
    break_start = serializers.TimeField(required=False, allow_null=True)
    break_end = serializers.TimeField(required=False, allow_null=True)
    is_flexible = serializers.BooleanField(required=False)
    min_present_minutes = serializers.IntegerField(min_value=0, max_value=1440, required=False, allow_null=True)
    half_day_minutes = serializers.IntegerField(min_value=0, max_value=1440, required=False, allow_null=True)
    overtime_enabled = serializers.BooleanField(required=False)
    overtime_basis = serializers.ChoiceField(choices=[c[0] for c in OVERTIME_BASES], required=False)
    min_overtime_minutes = serializers.IntegerField(min_value=0, max_value=720, required=False)
    checkin_window_before_minutes = serializers.IntegerField(min_value=0, max_value=720, required=False)
    checkout_window_after_minutes = serializers.IntegerField(min_value=0, max_value=720, required=False)
    is_active = serializers.BooleanField(required=False)

    def validate(self, attrs):
        if attrs.get('start_time') is not None and attrs.get('start_time') == attrs.get('end_time'):
            raise serializers.ValidationError('start_time and end_time cannot be equal')
        if bool(attrs.get('break_start')) != bool(attrs.get('break_end')):
            raise serializers.ValidationError('break_start and break_end must be given together')
        present, half = attrs.get('min_present_minutes'), attrs.get('half_day_minutes')
        if present is not None and half is not None and half > present:
            raise serializers.ValidationError('half_day_minutes cannot exceed min_present_minutes')
        return attrs


class ScheduleDaySerializer(serializers.Serializer):
    weekday = serializers.IntegerField(min_value=0, max_value=6)
    is_working_day = serializers.BooleanField()
    start_time = serializers.TimeField(required=False, allow_null=True)
    end_time = serializers.TimeField(required=False, allow_null=True)
    expected_work_minutes = serializers.IntegerField(min_value=1, max_value=1440, required=False,
                                                     allow_null=True)

    def validate(self, attrs):
        if bool(attrs.get('start_time')) != bool(attrs.get('end_time')):
            raise serializers.ValidationError('start_time and end_time must be given together')
        if attrs.get('start_time') and attrs['start_time'] == attrs['end_time']:
            raise serializers.ValidationError('start_time and end_time cannot be equal')
        return attrs


class ScheduleSerializer(serializers.Serializer):
    days = ScheduleDaySerializer(many=True)

    def validate_days(self, value):
        weekdays = [d['weekday'] for d in value]
        if len(weekdays) != len(set(weekdays)):
            raise serializers.ValidationError('Each weekday may appear only once')
        return value


class AssignmentSerializer(serializers.Serializer):
    shift_id = serializers.IntegerField()
    scope = serializers.ChoiceField(choices=[c[0] for c in ASSIGNMENT_SCOPES])
    employee_id = serializers.IntegerField(required=False, allow_null=True)
    team_lead_id = serializers.IntegerField(required=False, allow_null=True)
    branch_id = serializers.IntegerField(required=False, allow_null=True)
    effective_from = serializers.DateField()
    effective_to = serializers.DateField(required=False, allow_null=True)
    remarks = serializers.CharField(max_length=500, required=False, allow_null=True, allow_blank=True)

    def validate(self, attrs):
        required = {'employee': 'employee_id', 'team': 'team_lead_id', 'branch': 'branch_id'}.get(attrs['scope'])
        if required and not attrs.get(required):
            raise serializers.ValidationError(f'{required} is required for scope {attrs["scope"]}')
        if attrs.get('effective_to') and attrs['effective_to'] < attrs['effective_from']:
            raise serializers.ValidationError('effective_to cannot be before effective_from')
        return attrs


class AssignmentEndSerializer(serializers.Serializer):
    effective_to = serializers.DateField()
    remarks = serializers.CharField(max_length=500, required=False, allow_null=True, allow_blank=True)


class SettingsSerializer(serializers.Serializer):
    duplicate_punch_window_minutes = serializers.IntegerField(min_value=0, max_value=60, required=False)
    unspecified_punch_mode = serializers.ChoiceField(choices=[c[0] for c in UNSPECIFIED_MODES], required=False)
    collector_offline_after_minutes = serializers.IntegerField(min_value=1, max_value=1440, required=False)
    use_holiday_calendar = serializers.BooleanField(required=False)
    use_leave_records = serializers.BooleanField(required=False)


# --- attendance actions ---------------------------------------------------

class ManualEventSerializer(serializers.Serializer):
    employee_id = serializers.IntegerField()
    event_time = IsoDateTimeField()
    event_type = serializers.ChoiceField(choices=[PUNCH_IN, PUNCH_OUT])
    location_id = serializers.IntegerField(required=False, allow_null=True)
    reason = serializers.CharField(max_length=500)


class VoidEventSerializer(serializers.Serializer):
    reason = serializers.CharField(max_length=500)


class ReprocessSerializer(serializers.Serializer):
    from_date = serializers.DateField()
    to_date = serializers.DateField()
    employee_ids = serializers.ListField(child=serializers.IntegerField(), required=False, allow_empty=True)
    refresh_shift = serializers.BooleanField(required=False, default=False)

    def validate(self, attrs):
        if attrs['from_date'] > attrs['to_date']:
            raise serializers.ValidationError('from_date must be on or before to_date')
        if (attrs['to_date'] - attrs['from_date']).days > 62:
            raise serializers.ValidationError('At most 62 days can be reprocessed at once')
        return attrs


class CheckInSerializer(serializers.Serializer):
    punch_type = serializers.ChoiceField(choices=[PUNCH_IN, PUNCH_OUT], required=False, allow_null=True)
    device_id = serializers.IntegerField(required=False, allow_null=True)
    channel = serializers.ChoiceField(choices=list(SELF_CHECKIN_DEVICE_TYPES), required=False, default='web')
