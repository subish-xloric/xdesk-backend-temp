""" Vendor-neutral part of an Attendance V2 collector.

A collector only moves data: read punches from a device (a PunchSource),
convert them to the standard payload, POST them to the central API, retry on
failure. It never pairs IN/OUT, applies shifts or computes hours - the central
Attendance V2 engine does that.

No local database: the sync position is kept in memory. After a restart the
collector re-reads a look-back window (COLLECTOR_LOOKBACK_HOURS) and simply
re-sends it; the API is idempotent on (device, external_punch_id), so already
received punches come back as "duplicates" and nothing is stored twice.
"""

import logging
import os
import threading
import time
import uuid
from dataclasses import dataclass, field
from datetime import datetime, timedelta

import requests

log = logging.getLogger('attendance_agent')


@dataclass
class StandardPunch:
    """ The standard contract, independent of the device vendor. """
    employee_code: str
    punch_time: datetime               # timezone-aware
    external_punch_id: str             # stable id; must not change between reads
    punch_type: str = None             # 'IN' / 'OUT' / None when the device has no state
    raw_data: dict = field(default_factory=dict)
    device_id: str = None              # device code configured centrally; defaults to the agent's

    def to_payload(self):
        payload = {
            'employee_code': self.employee_code,
            'punch_time': self.punch_time.isoformat(),
            'external_punch_id': self.external_punch_id,
            'punch_type': self.punch_type,
            'raw_data': self.raw_data or None,
        }
        if self.device_id:
            payload['device_id'] = self.device_id
        return payload


class PunchSource:
    """ Implemented once per vendor. fetch_since() returns StandardPunch
    objects for punches at or after `since`, oldest first. """
    source_name = 'other'

    def fetch_since(self, since):
        raise NotImplementedError

    def close(self):
        pass


@dataclass
class AgentConfig:
    api_base_url: str                  # e.g. https://xdesk.example.com/api/attendance/v2/
    collector_id: str
    collector_key: str
    device_id: str
    version: str = '1.0.0'
    poll_seconds: int = 60
    heartbeat_seconds: int = 120
    lookback_hours: int = 48
    batch_size: int = 200
    timeout_seconds: int = 30
    max_pending: int = 20000           # in-memory retry buffer cap
    verify_tls: bool = True

    @classmethod
    def from_env(cls):
        """ Credentials only ever come from the environment, never source code. """
        missing = [n for n in ('ATTV2_API_BASE_URL', 'ATTV2_COLLECTOR_ID', 'ATTV2_COLLECTOR_KEY', 'ATTV2_DEVICE_ID')
                   if not os.environ.get(n)]
        if missing:
            raise SystemExit(f'Missing environment variables: {", ".join(missing)}')
        url = os.environ['ATTV2_API_BASE_URL'].rstrip('/') + '/'
        if not url.startswith('https://') and os.environ.get('ATTV2_ALLOW_HTTP') != '1':
            raise SystemExit('ATTV2_API_BASE_URL must use https:// (set ATTV2_ALLOW_HTTP=1 only for local testing)')
        return cls(
            api_base_url=url,
            collector_id=os.environ['ATTV2_COLLECTOR_ID'],
            collector_key=os.environ['ATTV2_COLLECTOR_KEY'],
            device_id=os.environ['ATTV2_DEVICE_ID'],
            poll_seconds=int(os.environ.get('ATTV2_POLL_SECONDS', 60)),
            heartbeat_seconds=int(os.environ.get('ATTV2_HEARTBEAT_SECONDS', 120)),
            lookback_hours=int(os.environ.get('ATTV2_LOOKBACK_HOURS', 48)),
            batch_size=min(int(os.environ.get('ATTV2_BATCH_SIZE', 200)), 500),
            verify_tls=os.environ.get('ATTV2_VERIFY_TLS', '1') != '0',
        )


class PermanentError(Exception):
    """ The API rejected the request itself (400/401/403/404) - retrying the
    same request will not help; it needs configuration to be fixed. """


class AttendanceApiClient:

    def __init__(self, config):
        self.config = config
        self.session = requests.Session()
        self.session.headers.update({
            'X-Collector-Id': config.collector_id,
            'X-Collector-Key': config.collector_key,     # never logged
            'Content-Type': 'application/json',
            'User-Agent': f'attendance-agent/{config.version}',
        })

    def _post(self, path, body):
        request_id = uuid.uuid4().hex
        response = self.session.post(self.config.api_base_url + path, json=body,
                                     headers={'X-Request-ID': request_id},
                                     timeout=self.config.timeout_seconds, verify=self.config.verify_tls)
        if response.status_code in (400, 401, 403, 404):
            raise PermanentError(f'{response.status_code} request_id={request_id} {response.text[:500]}')
        if response.status_code == 429 or response.status_code >= 500:
            raise requests.HTTPError(f'{response.status_code} request_id={request_id}', response=response)
        response.raise_for_status()
        return response.json()

    def send_punches(self, punches):
        a=[p.to_payload() for p in punches]
        print('aaaaaaaaaaaaaaaaaa', a)
        body = {'collector_id': self.config.collector_id, 'device_id': self.config.device_id,
                'punches': [p.to_payload() for p in punches]}
        return self._post('punches/', body)

    def heartbeat(self, status='online', message=None):
        body = {'collector_id': self.config.collector_id, 'version': self.config.version,
                'device_id': self.config.device_id, 'status': status}
        if message:
            body['message'] = message[:500]
        return self._post('collector/heartbeat/', body)


class CollectorAgent:

    def __init__(self, source, config):
        self.source = source
        self.config = config
        self.client = AttendanceApiClient(config)
        self.pending = {}                         # external_punch_id -> StandardPunch (retry buffer)
        self.watermark = datetime.now().astimezone() - timedelta(hours=config.lookback_hours)
        self.last_error = None
        self._stop = threading.Event()

    def run_forever(self):
        log.info('Collector %s starting (device %s), look-back from %s',
                 self.config.collector_id, self.config.device_id, self.watermark.isoformat())
        threading.Thread(target=self._heartbeat_loop, daemon=True).start()
        backoff = self.config.poll_seconds
        while not self._stop.is_set():
            try:
                self.sync_once()
                self.last_error = None
                backoff = self.config.poll_seconds
            except PermanentError as exc:
                self.last_error = str(exc)
                log.error('API rejected the request, check collector configuration: %s', exc)
                backoff = max(self.config.poll_seconds, 300)
            except Exception as exc:               # device or network problem: retry with back-off
                self.last_error = f'{type(exc).__name__}: {exc}'
                log.warning('Sync failed (%s); retrying in %ss', self.last_error, backoff)
                backoff = min(backoff * 2, 900)
            self._stop.wait(backoff)

    def stop(self):
        self._stop.set()
        self.source.close()

    def sync_once(self):
        read_from = self.watermark
        fetched = self.source.fetch_since(read_from)
        for punch in fetched:
            self.pending[punch.external_punch_id] = punch
        if len(self.pending) > self.config.max_pending:
            log.error('Retry buffer over %s punches; oldest will be re-read from the device after restart',
                      self.config.max_pending)
        if fetched:
            # Keep a small overlap: punches written late with an older timestamp are still read.
            newest = max(p.punch_time for p in fetched)
            self.watermark = max(self.watermark, newest - timedelta(minutes=10))

        batch_ids = list(self.pending)[:self.config.batch_size]
        while batch_ids:
            batch = [self.pending[i] for i in batch_ids]
            result = self.client.send_punches(batch)
            log.info('Sent %s: accepted=%s duplicates=%s failed=%s request_id=%s', len(batch),
                     result.get('accepted'), result.get('duplicates'), result.get('failed'), result.get('request_id'))
            for error in result.get('errors') or []:
                # Per-punch validation errors (e.g. unknown employee code) are
                # logged, not retried forever; the central raw-punch store keeps them.
                log.warning('Punch rejected: %s', error)
            for i in batch_ids:
                self.pending.pop(i, None)
            batch_ids = list(self.pending)[:self.config.batch_size]

    def _heartbeat_loop(self):
        while not self._stop.is_set():
            try:
                status = 'error' if self.last_error else 'online'
                self.client.heartbeat(status, self.last_error)
            except Exception as exc:
                log.warning('Heartbeat failed: %s', exc)
            self._stop.wait(self.config.heartbeat_seconds)


def run(source):
    logging.basicConfig(level=os.environ.get('ATTV2_LOG_LEVEL', 'INFO'),
                        format='%(asctime)s %(levelname)s %(name)s %(message)s')
    agent = CollectorAgent(source, AgentConfig.from_env())
    try:
        agent.run_forever()
    except KeyboardInterrupt:
        agent.stop()
        time.sleep(0.1)
