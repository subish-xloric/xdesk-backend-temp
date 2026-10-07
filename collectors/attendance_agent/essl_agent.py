""" Reference eSSL collector (attendance-agent-essl).

Reads the eSSL / eTimeTrack `Att` table - the same table and columns the
legacy xDesk attendance module queries today (EmployeeCode, LogDate,
Direction, DeviceSerialNo) - converts rows to the standard payload and sends
them to Attendance V2. All eSSL-specific knowledge lives in this file.

Run:
    export ATTV2_API_BASE_URL=https://<host>/api/attendance/v2/
    export ATTV2_COLLECTOR_ID=COL-001
    export ATTV2_COLLECTOR_KEY=<key issued in Attendance V2 > Collectors>
    export ATTV2_DEVICE_ID=ESSL-001          # device code configured centrally
    export ESSL_ODBC_CONNECTION="DRIVER={ODBC Driver 18 for SQL Server};SERVER=...;DATABASE=...;UID=...;PWD=...;TrustServerCertificate=yes"
    python essl_agent.py
"""

import os

# Old SQL Server builds only speak TLS 1.0, which OpenSSL 3 rejects by default.
# Must be set before anything loads OpenSSL (hashlib, requests in core, pyodbc).
os.environ.setdefault('OPENSSL_CONF', os.path.join(os.path.dirname(os.path.abspath(__file__)),
                                                   'openssl_legacy_tls.cnf'))

import hashlib
from datetime import datetime
from zoneinfo import ZoneInfo

from core import PunchSource, StandardPunch, run

# eSSL Direction column -> standard direction. Anything else is sent as
# "no direction" and the central engine decides from the punch sequence.
DIRECTIONS = {'in': 'IN', 'out': 'OUT'}


class EsslMssqlSource(PunchSource):
    source_name = 'essl'

    def __init__(self, connection_string, device_timezone, serial_to_device=None):
        import pyodbc                                  # only this collector needs the MSSQL driver
        self._pyodbc = pyodbc
        self.connection_string = connection_string
        self.tz = ZoneInfo(device_timezone)
        # Optional: several physical devices behind one eSSL server,
        # "SERIAL1=ESSL-001,SERIAL2=ESSL-002" -> per-punch device code.
        self.serial_to_device = serial_to_device or {}
        self.connection = None

    def _cursor(self):
        if self.connection is None:
            self.connection = self._pyodbc.connect(self.connection_string, timeout=15)
        return self.connection.cursor()

    def fetch_since(self, since):
        local_since = since.astimezone(self.tz).replace(tzinfo=None)
        print('local_since...........', local_since)
        try:
            cursor = self._cursor()
            cursor.execute(
                'SELECT EmployeeCode, LogDate, Direction, DeviceSerialNo FROM Att '
                'WHERE LogDate >= ? ORDER BY LogDate', local_since)        # parameterised, no string SQL
            rows = cursor.fetchall()
            #print('rows', rows)
        except Exception:
            self.close()                                 # reconnect on the next poll
            raise
        return [self._to_standard(row) for row in rows if str(row[0] or '').strip()]

    def _to_standard(self, row):
        employee_code, log_date, direction, serial = str(row[0]).strip(), row[1], row[2], row[3]
        punch_time = log_date.replace(microsecond=0, tzinfo=self.tz)
        serial = str(serial or '').strip()
        # The Att table has no stable row id, so derive one deterministically:
        # the same row always produces the same id, making retries idempotent.
        key = f'{serial}|{employee_code}|{log_date:%Y%m%d%H%M%S}'
        return StandardPunch(
            employee_code=employee_code,
            punch_time=punch_time,
            external_punch_id='ESSL-' + hashlib.sha1(key.encode()).hexdigest()[:24],
            punch_type=DIRECTIONS.get(str(direction or '').strip().lower()),
            raw_data={'EmployeeCode': employee_code, 'LogDate': log_date.isoformat(sep=' '),
                      'Direction': direction, 'DeviceSerialNo': serial},
            device_id=self.serial_to_device.get(serial),
        )

    def close(self):
        if self.connection is not None:
            try:
                self.connection.close()
            finally:
                self.connection = None


def _serial_map(value):
    #pairs = [p.split('=', 1) for p in (value or '').split(',') if '=' in p]
    items = value or ()

    if isinstance(items, str):
        items = items.split(',')

    pairs = [p.split('=', 1) for p in items if '=' in p]
    print('pairs', pairs)
    return {serial.strip(): code.strip() for serial, code in pairs}


if __name__ == '__main__':
    if 1==1: # not os.environ.get('ESSL_ODBC_CONNECTION'):
        #raise SystemExit('ESSL_ODBC_CONNECTION is required')
        #os.environ['ESSL_ODBC_CONNECTION']
        #os.environ.get('ESSL_TIMEZONE', 'Asia/Kolkata')

        os.environ['ATTV2_API_BASE_URL'] = 'https://magdalena-errable-nonburdensomely.ngrok-free.dev/api/attendance/v2/'
        os.environ['ATTV2_COLLECTOR_ID'] = 'COL-DM-ESSL-01'
        os.environ['ATTV2_COLLECTOR_KEY'] = 'attv2_qQleHu7Wd0XFPxzgJYm2kapZwnLFkfa0XhCT5XK5gJg'
        os.environ['ATTV2_DEVICE_ID'] = 'DM-FF-IN'
        


        ESSL_ODBC_CONNECTION="DRIVER={ODBC Driver 17 for SQL Server};SERVER=SEZ-SR-6\\MSSQL2014;DATABASE=ESSL;UID=essldm;PWD=essldm;Encrypt=no;TrustServerCertificate=yes;"
        #os.environ.get('ESSL_SERIAL_DEVICE_MAP')
        ESSL_SERIAL_DEVICE_MAP= ('SERIAL1=DM-FF-IN')

    run(EsslMssqlSource(ESSL_ODBC_CONNECTION,
                        'Asia/Kolkata',
                        _serial_map(ESSL_SERIAL_DEVICE_MAP)))
