""" Example ZKTeco collector (attendance-agent-zkteco) - shows that a new
device type needs only a new PunchSource; the central API and attendance
rules are unchanged. Talks to the device directly over the ZK protocol using
the optional `pyzk` package (pip install pyzk).

    export ZK_DEVICE_IP=192.168.1.201   ZK_DEVICE_PORT=4370   ZK_TIMEZONE=Asia/Kolkata
    (plus the ATTV2_* variables, see essl_agent.py)
    python zkteco_agent.py
"""

import os
from zoneinfo import ZoneInfo

from core import PunchSource, StandardPunch, run

# ZK "punch" codes: 0 check-in, 1 check-out, others (break/overtime) have no
# fixed meaning across firmware, so they are sent without a direction.
PUNCH_CODES = {0: 'IN', 1: 'OUT'}


class ZkTecoSource(PunchSource):
    source_name = 'zkteco'

    def __init__(self, ip, port, device_timezone, password=0):
        from zk import ZK
        self.zk = ZK(ip, port=port, timeout=10, password=password, ommit_ping=True)
        self.tz = ZoneInfo(device_timezone)
        self.serial = None

    def fetch_since(self, since):
        conn = self.zk.connect()
        try:
            self.serial = self.serial or conn.get_serialnumber()
            records = conn.get_attendance()         # the device returns its whole log
        finally:
            conn.disconnect()
        punches = []
        for record in records:
            punch_time = record.timestamp.replace(microsecond=0, tzinfo=self.tz)
            if punch_time < since:
                continue
            punches.append(StandardPunch(
                employee_code=str(record.user_id).strip(),
                punch_time=punch_time,
                external_punch_id=f'ZK-{self.serial}-{record.user_id}-{record.timestamp:%Y%m%d%H%M%S}',
                punch_type=PUNCH_CODES.get(record.punch),
                raw_data={'user_id': record.user_id, 'timestamp': record.timestamp.isoformat(sep=' '),
                          'status': record.status, 'punch': record.punch, 'serial': self.serial},
            ))
        return sorted(punches, key=lambda p: p.punch_time)


if __name__ == '__main__':
    run(ZkTecoSource(os.environ['ZK_DEVICE_IP'], int(os.environ.get('ZK_DEVICE_PORT', 4370)),
                     os.environ.get('ZK_TIMEZONE', 'Asia/Kolkata'), int(os.environ.get('ZK_DEVICE_PASSWORD', 0))))
