# Attendance V2 collector (reference implementation)

A small, stand-alone Python process that runs next to a biometric device (or
its vendor server), reads punches, and posts them to the xDesk Attendance V2
API. It is **not** part of the Django app and has no database.

```
Device ──> PunchSource (vendor specific) ──> core.CollectorAgent ──HTTPS──> /api/attendance/v2/punches/
```

| File | Purpose |
|---|---|
| `core.py` | Vendor-neutral: standard payload, API client, batching, retry/back-off, heartbeat |
| `essl_agent.py` | eSSL source: reads the eTimeTrack `Att` MSSQL table (same source the legacy module uses) |
| `zkteco_agent.py` | ZKTeco source over the ZK protocol (`pyzk`) - example for a second vendor |

A new device type = a new `PunchSource` subclass. Shift rules, IN/OUT pairing,
late/early/overtime are **never** implemented here.

## Setup

1. In xDesk: **Attendance V2 → Devices**: add the device (e.g. code `ESSL-001`, type eSSL, location).
2. **Attendance V2 → Collectors**: add a collector (e.g. `COL-001`), link the device, and copy the
   API key shown **once**. (Rotate it there if it leaks; the old key stops working immediately.)
3. On the collector machine:

```bash
pip install -r requirements.txt            # requests (+ pyodbc for eSSL, pyzk for ZKTeco)
export ATTV2_API_BASE_URL=https://magdalena-errable-nonburdensomely.ngrok-free.dev/api/attendance/v2/
export ATTV2_COLLECTOR_ID=COL-001
export ATTV2_COLLECTOR_KEY=<key>
export ATTV2_DEVICE_ID=ESSL-001
export ESSL_ODBC_CONNECTION="DRIVER={ODBC Driver 18 for SQL Server};SERVER=...;DATABASE=...;UID=...;PWD=..."
python essl_agent.py
```

Optional: `ATTV2_POLL_SECONDS` (60), `ATTV2_HEARTBEAT_SECONDS` (120), `ATTV2_LOOKBACK_HOURS` (48),
`ATTV2_BATCH_SIZE` (200, max 500), `ESSL_TIMEZONE` (Asia/Kolkata),
`ESSL_SERIAL_DEVICE_MAP` (`SERIAL1=ESSL-001,SERIAL2=ESSL-002` when one eSSL server serves several devices -
every mapped device must be linked to the collector centrally).

HTTPS is required; `ATTV2_ALLOW_HTTP=1` exists only for local testing.

## Reliability without a local database

* Sync position is kept in memory. On start-up the agent re-reads the last `ATTV2_LOOKBACK_HOURS`
  and re-sends them. The API is idempotent on `(device, external_punch_id)`, so re-sent punches are
  answered as `duplicates` and never stored twice.
* Network errors, timeouts, 429 and 5xx: the batch stays in the in-memory buffer and is retried with
  exponential back-off (up to 15 min).
* 400/401/403/404: configuration problem (bad key, device not linked, ...) - logged loudly, retried slowly.
* Per-punch errors (e.g. unknown employee code) are logged; the server keeps the raw punch and links it
  automatically when the same punch is sent again after the employee is set up.
* Heartbeat every `ATTV2_HEARTBEAT_SECONDS` reports version and `online`/`error`, shown in
  **Attendance V2 → Collectors**.

## Payload contract

```json
POST /api/attendance/v2/punches/
Headers: X-Collector-Id, X-Collector-Key, X-Request-ID (optional)
{
  "collector_id": "COL-001",
  "device_id": "ESSL-001",
  "punches": [
    {"employee_code": "1025", "punch_time": "2026-09-23T08:52:14+05:30",
     "punch_type": "IN", "external_punch_id": "ESSL-...", "raw_data": {"...": "..."}}
  ]
}
→ 200 {"success": true, "accepted": 10, "duplicates": 2, "failed": 0, "request_id": "...", "sync_id": 12}
```

`punch_type` is optional (`IN`/`OUT`/omitted). `external_punch_id` is optional; without it the server
derives a deterministic id from device + employee code + time. `device_id` / `location_code` may also be
given per punch. At most 500 punches per request.
