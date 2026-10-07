# Attendance V2 — Technical Guide

How Attendance V2 works internally: architecture, data model, the processing engine, security, and how to extend
it. For what changed in the release and how to deploy it, see
[ATTENDANCE_V2_RELEASE_NOTES.md](ATTENDANCE_V2_RELEASE_NOTES.md). For the original requirements, see
[attendence_v2.md](attendence_v2.md).

---

## Contents

1. [The core idea](#1-the-core-idea)
2. [Code layout](#2-code-layout)
3. [Data model](#3-data-model)
4. [End-to-end flow of a punch](#4-end-to-end-flow-of-a-punch)
5. [Collector authentication and ingestion](#5-collector-authentication-and-ingestion)
6. [The day plan: shift, calendar and leave for one date](#6-the-day-plan-shift-calendar-and-leave-for-one-date)
7. [Work-date assignment (overnight shifts)](#7-work-date-assignment-overnight-shifts)
8. [Pairing punches into sessions](#8-pairing-punches-into-sessions)
9. [Daily calculation: hours, late, early, overtime, status](#9-daily-calculation-hours-late-early-overtime-status)
10. [Orchestration, concurrency and history](#10-orchestration-concurrency-and-history)
11. [Shift management](#11-shift-management)
12. [Other ways punches enter: check-in and corrections](#12-other-ways-punches-enter-check-in-and-corrections)
13. [Nightly finalization and recalculation](#13-nightly-finalization-and-recalculation)
14. [Multi-company isolation, permissions and scope](#14-multi-company-isolation-permissions-and-scope)
15. [Errors, logging and monitoring](#15-errors-logging-and-monitoring)
16. [The external collector](#16-the-external-collector)
17. [Frontend](#17-frontend)
18. [Configuration reference](#18-configuration-reference)
19. [Worked examples](#19-worked-examples)
20. [Extending Attendance V2](#20-extending-attendance-v2)
21. [Troubleshooting](#21-troubleshooting)

---

## 1. The core idea

The legacy module reads the eSSL database directly, so every rule in it assumes eSSL. V2 splits the problem in two:

```
DEVICE-SPECIFIC                              DEVICE-INDEPENDENT (this backend)
─────────────────                            ────────────────────────────────────────────────
eSSL server  ─> essl_agent.py  ─┐
ZKTeco       ─> zkteco_agent.py ─┼─ standard ─> Raw punch ─> Event ─> Sessions ─> Daily attendance
Any device   ─> <new source>    ─┘  payload             ▲
Web / mobile check-in ──────────────────────────────────┤
Manual correction ──────────────────────────────────────┘
                                                shift + calendar + leave + company rules
```

* **Collectors** only move data. They read a device, convert each record into the standard payload, and POST it.
  They never pair IN/OUT, apply shifts or calculate hours.
* **The backend** only sees standard punches. No business rule branches on the device type (`essl`, `zkteco`, …). The
  device type is only a label, plus a channel check: collector devices vs web/mobile devices.
* Adding a new device therefore means writing a new collector source. The backend stays unchanged.

V2 runs **alongside** the legacy module. The two share no tables they write to, and the legacy endpoints are
unchanged.

---

## 2. Code layout

The code follows the project's usual chain of views → biz (`…BL`) → data access (`…DA`) → models.

### Backend API — `pTracker/api/attendance_v2/`

| File | Responsibility |
|---|---|
| `urls.py` | Routes, mounted at `/api/attendance/v2/` (before the legacy `/api/attendance/` in `pTracker/urls.py`) |
| `views.py` | Thin JWT views for employees and admins |
| `collector_views.py` | Thin machine-to-machine views (`punches/`, `collector/heartbeat/`) |
| `collector_auth.py` | Collector authentication, principal, HTTPS permission, rate throttle, key generation |
| `serializers.py` | Input validation only: shapes, ranges, formats |
| `attendance_v2_helper.py` | Active company, capability/scope helpers, time parsing, pagination, `V2Error` and the `@guarded` error wrapper |
| `ingestion_biz.py` | `PunchIngestionBL`: validates and stores collector batches and heartbeats |
| `day_plan_biz.py` | `DayPlanBL`: which shift, schedule, holiday and leave apply on a date, plus work-date assignment |
| `processing_biz.py` | The engine: `pair_events()`, `summarize()` (pure functions) and `AttendanceProcessorBL` (orchestration) |
| `shift_biz.py` | `ShiftBL` (shifts, weekly schedules, assignments, calendar) and `SettingsBL` |
| `location_biz.py`, `device_biz.py` | Locations, devices and collectors (CRUD, key issue/rotation) |
| `attendance_query_biz.py` | Read side: daily, detail, sessions, events, raw punches, sync logs, dashboard, employees, branches |
| `correction_biz.py` | Manual punch, void, reprocess |
| `checkin_biz.py` | Web/mobile self check-in |
| `audit_biz.py` | `record_audit()` and the audit log listing |
| `daily_job_biz.py` | Nightly finalization used by Celery and the management command |

### Data access — `pTracker/dataaccess/attendance_v2_access/`

A **managed** Django app with migrations; its tables are new and owned by V2.

| File | Contents |
|---|---|
| `constants.py` | Every choice value (device types, statuses, scopes, …) |
| `*_models.py` | Models, split by concern (`location`, `device`, `punch`, `shift`, `daily`, `audit`); `models.py` re-exports them |
| `*_da.py` | All ORM queries: `LocationDA`, `DeviceDA`, `CollectorDA`, `PunchDA`, `ShiftDA`, `DailyDA`, `AuditDA` |
| `org_da.py` | `OrgDA`: **read-only** access to existing tables V2 reuses (memberships, `emp_lead_mapping`, `holidays`, `additional_working_days`, `leaves`, `wfh_requests`, `platform_branch`) |
| `migrations/0001_initial.py` | Schema |
| `management/commands/process_attendance_v2.py` | Manual or bulk finalization |

### Elsewhere

* `pTracker/cronjobs/attendance_v2_daily.py`: Celery task `finalize_attendance_v2`, scheduled in `celery_beat.py`.
* `pTracker/dataaccess/platform_access/migrations/0014_seed_attendance_v2_capabilities.py`: the 3 new capabilities.
* `collectors/attendance_agent/`: the reference external collector (§16).
* `xdesk-frontend/src/app/modules/attendance-v2/`: the Angular screens (§17).

---

## 3. Data model

```
platform_company ─┬─< attv2_location (self-referencing parent, optional platform_branch)
                  │         ▲
                  ├─< attv2_device ──(location)
                  │         ▲  ▲
                  ├─< attv2_collector >──< attv2_collector_devices
                  │
                  ├─< attv2_sync_log ─────────────┐
                  ├─< attv2_raw_punch ──(device, collector, sync_log, employee?, location?)
                  │         │ 1:1
                  ├─< attv2_event ──(employee, device?, location?, raw_punch?)
                  │         ▲ check_in_event / check_out_event
                  ├─< attv2_session ──(daily)
                  ├─< attv2_daily_attendance ──(employee, shift?, shift_snapshot JSON)
                  │
                  ├─< attv2_shift ─< attv2_shift_schedule (per weekday)
                  ├─< attv2_shift_assignment ──(shift; employee | team_lead | branch | company)
                  ├── attv2_settings (1:1)
                  └─< attv2_audit_log
```

Every table carries `company_id`, and every query filters on it.

### The three punch layers

| Layer | Table | What it holds | Mutability |
|---|---|---|---|
| **Raw punch** | `attv2_raw_punch` | Exactly what arrived: `external_employee_id`, `external_punch_id`, `punch_time`, `raw_punch_type`, the device's original record in `raw_data` (JSON), `status` (`pending` / `processed` / `unresolved_employee` / `error`) | Never edited, except for status and employee linking |
| **Event** | `attv2_event` | The normalized punch: employee, `event_time`, `event_type` (`IN` / `OUT` / `UNSPECIFIED`), `attendance_date` (the work date), source, `is_manual`, `status` (`active` / `void`) | Never deleted; corrections add or void events |
| **Derived** | `attv2_session`, `attv2_daily_attendance` | IN/OUT pairs and the daily summary | Rebuilt by the engine at any time |

### Important constraints

| Constraint | Why |
|---|---|
| `attv2_raw_punch (device_id, external_punch_id)` UNIQUE | Idempotency: the same punch can never be stored twice |
| `attv2_event.raw_punch_id` UNIQUE | One event per raw punch |
| `attv2_daily_attendance (company, employee, attendance_date)` UNIQUE | One summary per employee per day |
| `attv2_collector.collector_id` UNIQUE (global) | The collector is looked up *before* its company is known |
| `(company, code)` UNIQUE on location, device and shift | Codes are what collectors and admins refer to |

### How V2 links to existing data

* **Employee** = `auth_user` (FK). A collector's `employee_code` is matched against `auth_user.username`, the same
  identifier the legacy module and the eSSL `Att.EmployeeCode` use.
* **Company / Branch** = `platform_company` / `platform_branch`.
* **Holidays** = `holidays` and `additional_working_days`. These are keyed by the *legacy* company id, so V2 uses
  `platform_company.legacy_company_id`.
* **Leave** = `leaves` rows with `status = 2` (approved); `leave_day_type = 1` is a full day, anything else is a half
  day.
* **Team** = `emp_lead_mapping` (the same definition of "team" as the legacy modules).

---

## 4. End-to-end flow of a punch

```
Collector                 CollectorAuthentication        PunchIngestionBL                AttendanceProcessorBL
   │ POST /punches/            │                              │                                  │
   │──────────────────────────>│ verify id + key hash         │                                  │
   │                           │ (company from collector row) │                                  │
   │                           │────────────────────────────> │ 1 create sync_log                │
   │                           │                              │ 2 module 'attendance' enabled?   │
   │                           │                              │ 3 validate batch + collector_id  │
   │                           │                              │ 4 per punch: device linked?      │
   │                           │                              │   time sane? location in co.?    │
   │                           │                              │ 5 employee codes -> user ids     │
   │                           │                              │   (active members of co. only)   │
   │                           │                              │ 6 dedupe vs DB + within batch    │
   │                           │                              │ 7 insert raw_punch (+ event)     │
   │                           │                              │─────────────────────────────────>│ 8 work date per event
   │                           │                              │                                  │ 9 rebuild each affected
   │                           │                              │                                  │   employee/date:
   │                           │                              │                                  │   plan → pair → summarize
   │                           │                              │<─────────────────────────────────│
   │                           │                              │ 10 raw punches -> processed      │
   │                           │                              │ 11 finish sync_log, touch collector
   │<──────────────────────────────────────────────────────── │ {success, accepted, duplicates, failed, errors, request_id, sync_id}
```

Processing is **synchronous**: when the response returns, the daily attendance already reflects the new punches.

---

## 5. Collector authentication and ingestion

### 5.1 Authentication (`collector_auth.py`)

Headers on every collector request:

```
X-Collector-Id:  COL-001
X-Collector-Key: attv2_<43 url-safe chars>      # 256 bits of randomness
X-Request-ID:    <optional; echoed back and stored on the sync log>
```

* The key is generated by `secrets.token_urlsafe(32)` and shown **once**, when the collector is created or its key is
  rotated. Only `sha256(key)` (`api_key_hash`) and a display prefix are stored. A fast hash is appropriate because the
  secret is random, not a password.
* The key comparison uses `hmac.compare_digest`. A hash is computed even for an unknown collector id, so response
  timing does not reveal which ids exist. Every failure returns the same generic `401 Invalid collector credentials`.
* A disabled collector, or a collector whose company is inactive, gets a 401.
* The request principal is a `CollectorPrincipal`, **not** an `auth_user`. `ModuleGateMiddleware` passes non-employee
  principals through to the view's own permissions.
* View permissions:
  * `CollectorTransportIsSecure` requires HTTPS when `REQUIRE_HTTPS` is on (the default whenever `DEBUG` is off). It
    honours `X-Forwarded-Proto` for TLS terminated at a proxy.
  * `IsCollector` rejects anything that isn't a collector principal.
* `CollectorRateThrottle` limits each collector (default `120/min`).
* An employee JWT cannot call the collector endpoints, and a collector key cannot call the employee endpoints.

### 5.2 Payload

```json
{
  "collector_id": "COL-001",
  "device_id": "ESSL-001",
  "location_code": "BLD-A-GF-PROD",
  "source": "essl",
  "punches": [
    {
      "employee_code": "1025",
      "punch_time": "2026-09-23T08:52:14+05:30",
      "punch_type": "IN",
      "external_punch_id": "ESSL-9f2c…",
      "device_id": "ESSL-002",
      "location_code": "BLD-B-REC",
      "raw_data": { "any": "vendor fields" }
    }
  ]
}
```

| Field | Rule |
|---|---|
| `collector_id` | Required. Must equal the authenticated collector, otherwise 403 |
| `device_id` (batch or per punch) | Device **code**. Must be active, linked to this collector, and a collector-type device (`essl` / `zkteco` / `other_biometric` / `api`), otherwise 403 or a per-punch error |
| `employee_code` | ≤ 64 chars; resolved only against **active members of the collector's company** |
| `punch_time` | ISO-8601. With an offset, it is converted to `settings.TIME_ZONE`; without one, it is taken as local. It is rejected if more than `MAX_FUTURE_SKEW_MINUTES` in the future or older than `MAX_PUNCH_AGE_DAYS` |
| `punch_type` | Optional. `IN` / `I` / `CHECKIN`… → IN; `OUT` / `O` / `CHECKOUT`… → OUT; missing or anything else → `UNSPECIFIED`. The original value is kept in `raw_punch_type` |
| `external_punch_id` | Optional, ≤ 120 chars. Without it the server derives `auto:` + `sha256(device_code \| employee_code \| punch_time)` |
| `location_code` (batch or per punch) | Optional; must be an active location of the same company. Defaults to the device's location |
| `source` | Informational only. It is stored in `raw_data.reported_source`; the trusted source is the **device's type** |
| `raw_data` | Optional JSON object, ≤ `MAX_RAW_DATA_BYTES` |
| batch size | 1 to `MAX_BATCH_SIZE` (500) |

### 5.3 Per-punch outcome

Each punch lands in exactly one bucket:

| Outcome | Condition | Stored? | Counted as |
|---|---|---|---|
| Validation error | Bad time, unknown device or location, … | No | `failed` + entry in `errors` |
| **Unknown employee** | Code isn't an active member of this company | Raw punch with status `unresolved_employee` (no event) | `failed`, `"Employee code X does not exist"` |
| Duplicate | `(device, external_punch_id)` already exists, or appears twice in the batch | No | `duplicates` |
| Resend of an unresolved punch | Existing raw punch is `unresolved_employee` | Linked now if the employee exists (event created) | `accepted`; otherwise `failed` again |
| Accepted | Everything valid | Raw punch + event, then processed | `accepted` |

A concurrent insert of the same punch (a race between two requests) hits the unique constraint. It is caught
(`IntegrityError` inside a savepoint) and reported as a duplicate.

**Why unknown employees are stored:** "did the collector send it / was the employee identified" must be answerable
(spec §23). A punch that arrives before an employee is set up is not lost; the collector's next re-send links it.

### 5.4 Response and HTTP status

```json
{ "success": false, "accepted": 10, "duplicates": 2, "failed": 1,
  "errors": [{ "external_punch_id": "10025", "employee_code": "EMP9999", "error": "Employee code EMP9999 does not exist" }],
  "request_id": "…", "sync_id": 42, "status": 200 }
```

* `200` means the batch was processed (see the counts). `success` is true only when `failed == 0`.
* `400` means the request itself is invalid: payload shape, batch size, bad JSON.
* `401` means bad credentials. `403` means a `collector_id` mismatch, a device not linked, HTTPS required, or the
  company's module is disabled. `429` means throttled. `500` means an internal error (logged; the response carries the
  request id).
* Collector contract: retry on network errors, 429 and 5xx. Do **not** blindly retry 400/401/403/404 (fix the
  configuration). Per-punch errors are logged, not retried forever.

### 5.5 Heartbeat

`POST collector/heartbeat/` with `{collector_id, version, device_id?, status?, message?}` updates `last_seen_at`,
`version`, `reported_status` and `last_ip`. A non-`online` status also records `last_error` and writes a `heartbeat`
sync log row. The admin screens compute an **effective status**:

```
last_seen_at is null                              → unknown
now − last_seen_at > collector_offline_after_minutes → offline
otherwise                                         → the reported status (online / error)
```

---

## 6. The day plan: shift, calendar and leave for one date

`DayPlanBL` answers one question: **"for employee E on work date D, which rules apply?"** The result is a `DayPlan`:

| Field | Meaning |
|---|---|
| `snapshot` | The shift rules in force (dict), or `None` if no shift applies |
| `day_type` | `working` / `weekly_off` / `holiday` |
| `leave_portion` | `none` / `half` / `full` |
| `start_dt`, `end_dt` | Shift start/end as datetimes; `end_dt` is on the next day for an overnight shift |
| `window_start`, `window_end` | Which punches can belong to D: `start_dt − checkin_window_before`, `end_dt + checkout_window_after`. Without a shift, it is the calendar day `[00:00, 24:00)` |
| `expected_work_minutes` | 0 on non-working days or full leave; halved on half-day leave |

The planner is created once per employee and date range. It loads everything in a handful of queries (assignments,
lead history, branch, holidays, extra working days, leave), with a 2-day margin each side, and caches plans per date.

### 6.1 Shift resolution (priority)

```
for scope in (employee, team, branch, company):          # most specific first
    candidates = active assignments of that scope that
                   - target this employee on D:
                       employee → assignment.employee_id == E
                       team     → assignment.team_lead_id == E's lead ON DATE D (emp_lead_mapping from/to dates)
                       branch   → assignment.branch_id == E's membership branch
                       company  → always
                   - and effective_from ≤ D ≤ (effective_to or ∞)
    if candidates: return the one with the latest effective_from
return None
```

The team lead is resolved **for the date being processed**, so historical team moves are respected. There is no
department level, because the application has no department model.

### 6.2 Snapshot

When a shift is found, `build_snapshot(shift, D)` freezes the rules for that date. It applies D's weekday override from
`attv2_shift_schedule`, if one exists: `is_working_day`, custom start/end, and expected minutes.

```json
{ "shift_id": 3, "shift_code": "GEN", "shift_name": "General", "is_working_day": true,
  "start_time": "09:00:00", "end_time": "18:00:00", "expected_work_minutes": 480,
  "grace_in_minutes": 15, "grace_out_minutes": 0, "break_minutes": 60, "break_start": null, "break_end": null,
  "is_flexible": false, "min_present_minutes": 360, "half_day_minutes": 240,
  "overtime_enabled": true, "overtime_basis": "after_shift_end", "min_overtime_minutes": 30,
  "checkin_window_before_minutes": 240, "checkout_window_after_minutes": 480 }
```

A weekday with **no** schedule row is a working day with the shift's own timings. Weekly offs are always explicit, so
nothing assumes Monday–Friday.

### 6.3 Calendar and leave

```
day_type = holiday     if D in holidays (company's legacy id)   and D not in additional_working_days
         = weekly_off  if snapshot says not a working day       and D not in additional_working_days
         = working     otherwise
leave    = full / half from approved `leaves` rows (if use_leave_records)
```

`use_holiday_calendar` and `use_leave_records` in `attv2_settings` switch these sources off per company.

---

## 7. Work-date assignment (overnight shifts)

A punch's **work date** is not always its calendar date. A night shift from 22:00 to 06:00 must count 05:58 as part of
the previous day. `DayPlanBL.work_date_for(t)`:

```
day = t.date()
current  = plan(day)
previous = plan(day − 1)
if t < previous.window_end and t < current.window_start:
    return day − 1                       # still inside yesterday's (overnight) window
following = plan(day + 1)
if t >= following.window_start and t >= current.window_end:
    return day + 1                       # e.g. a shift starting just after midnight
return day
```

Worked cases (window before = 240 min, after = 480 min):

| Shifts | Punch | previous.window_end | current.window_start | Work date |
|---|---|---|---|---|
| Night 22–06 both days | Tue 05:58 | Tue 14:00 | Tue 18:00 | **Mon** |
| Night 22–06 | Mon 22:05 | Mon 14:00 (from Sun) | Mon 18:00 | Mon |
| General 09–18 | Tue 01:00 | Tue 02:00 | Tue 05:00 | Mon (late-night work) |
| General 09–18 | Tue 03:00 | Tue 02:00 | Tue 05:00 | Tue |

The work date is stored on the event (`attendance_date`) and recomputed whenever the employee/date range is
reprocessed. If the date changes, both the old and the new dates are rebuilt.

---

## 8. Pairing punches into sessions

`pair_events(events, rules)` is a pure function. Its input is the day's **active** events in time order.

### Step 1 — drop accidental double punches

An event is ignored when it falls within `duplicate_punch_window_minutes` (default 2) of the previously **accepted**
event **and** has the same direction as it, or either of the two is `UNSPECIFIED`. An explicit IN followed by an
explicit OUT is never merged.

### Step 2 — build sessions

**Mode `first_last`** applies only when *all* remaining events are `UNSPECIFIED`: first = IN, last = OUT, and the punches
in between are ignored.

**Otherwise** a state machine runs (this also covers the `alternate` mode for undirected punches):

```
open = None
for e in events:
    direction = e.type, or (OUT if open else IN) when UNSPECIFIED
    IN : if open: close open as MISSING_OUT;  open = e
    OUT: if open: session(open, e) COMPLETE; open = None
         else   : session(None, e) MISSING_IN
at the end: if open → MISSING_OUT
```

Example:

```
08:55 IN, 12:15 OUT, 13:05 IN, 18:10 OUT   →  S1 08:55–12:15 (complete), S2 13:05–18:10 (complete)
09:00 IN, 13:00 IN, 18:00 OUT              →  S1 09:00–? (missing OUT), S2 13:00–18:00
09:20, 09:21, 18:00  (no direction)         →  09:21 ignored (double tap) → S1 09:20–18:00
```

---

## 9. Daily calculation: hours, late, early, overtime, status

`summarize(plan, sessions, now)` is a pure function. All thresholds come from the snapshot.

### 9.1 Minutes

```
gross   = Σ duration of COMPLETE sessions
breaks  = Σ gaps between one session's OUT and the next session's IN
unpaid  = if break_start/break_end configured: minutes of complete sessions overlapping that window
          else if break_minutes > 0 and gross > break_minutes: max(break_minutes − breaks, 0)
work    = gross − unpaid                 → total_work_minutes
```

The unpaid-break rule means an employee who never punches out for lunch still has the configured break deducted,
while one who punched a 50-minute lunch has only the missing 10 minutes deducted.

### 9.2 Late / early departure

Both apply only on a working day, with a shift that is not flexible and no leave that day.

```
late   : first IN  > start_dt + grace_in   → late_minutes = first IN − start_dt,  is_late
early  : last OUT  < end_dt   − grace_out  → early_minutes = end_dt − last OUT,   is_early_departure
```

`late_minutes` is measured from the shift start, not from the end of the grace period.

### 9.3 Overtime (only if `overtime_enabled`)

```
non-working day (holiday / weekly off / full leave): overtime = work
basis after_shift_end : overtime = last OUT − end_dt
basis beyond_expected : overtime = work − expected_work_minutes
overtime counts only if ≥ min_overtime_minutes, else 0
```

### 9.4 Status

```
no sessions:
    holiday → holiday ; weekly_off → weekly_off ; full leave → leave
    now < window_end → not_started ; else → absent
any MISSING_IN / MISSING_OUT session:
    now < window_end → present (the day is still in progress)
    else             → incomplete   (needs a correction)
non-working day with work → present
otherwise (thresholds halved on half-day leave):
    min_present_minutes unset or work ≥ it → present
    half_day_minutes set and work ≥ it     → half_day
    else                                   → absent ("Below minimum working minutes")
```

`remarks` collects notes such as "No shift assigned", "Half-day leave", "Worked on a leave day", "Missing punch" and
"N duplicate punch(es) ignored".

---

## 10. Orchestration, concurrency and history

`AttendanceProcessorBL.process_day(employee, date, planner)` runs in one DB transaction:

```
1. lock_daily(): get_or_create the daily row, then SELECT … FOR UPDATE on it
2. plan = planner.plan(date)
3. events = active events with attendance_date = date
4. if no events and (no shift or date in the future): delete the daily row, stop
5. sessions, ignored = pair_events(events)
6. summary = summarize(plan, sessions, now)
7. save the daily row (incl. shift_id + shift_snapshot); replace its sessions
```

* **Concurrency:** the row lock serializes two batches touching the same employee/date, so sessions are never rebuilt
  by two transactions at once.
* **Rebuildable:** sessions and daily rows are always derived from events, so recalculating any range is safe and
  repeatable.
* **History is stable:** `planner()` feeds the snapshots already stored on **past** daily rows back into the planner.
  Editing a shift, or adding a back-dated assignment, therefore does not change days that were already calculated.
  Today and future dates always re-resolve, so an assignment made today applies today. To deliberately recalculate
  history with the current rules, use reprocess with `refresh_shift = true`.
* **No shift → no absences.** Without a shift the engine does not know which days are working days, so only days with
  punches get a row.

---

## 11. Shift management

### Assignments never overwrite history

`POST employee-shifts/` for a target (employee / team lead / branch / company), with `effective_from = F` and an
optional `effective_to = T`:

```
lock all active assignments of that target (SELECT … FOR UPDATE)
if any existing assignment STARTS within [F, T]     → 409 (end or delete it explicitly)
for the running assignment that started before F and covers F:
    set its effective_to = F − 1                    (audited "end")
    if it was meant to run past T:
        create its remainder from T + 1 to its original end   (audited "Resumes after a temporary assignment")
create the new assignment                           (audited "assign")
```

Example: an employee on General from 01-Sep (open-ended) is given Night for 25–26 Sep. The result is three rows:
General 01–24 Sep, Night 25–26 Sep, General from 27 Sep.

* `PATCH employee-shifts/<id>/ {effective_to}` changes the end date. It may not overlap the target's next assignment.
* `DELETE` works only for assignments that haven't started yet (it sets `is_active = false`). Started assignments are
  history and can only be ended.
* A shift used by current or future assignments cannot be deactivated.
* A past `effective_from` returns a hint to reprocess with `refresh_shift`, because past days keep their snapshot.

### Shift calendar

`GET shift-calendar/?employee_id&from_date&to_date` (at most 62 days) runs the same planner as the engine for each date:
the shift or OFF, holiday, leave, expected minutes and the overnight flag. There is no separate roster table; the
calendar is always consistent with what attendance processing will use.

---

## 12. Other ways punches enter: check-in and corrections

### Web / mobile check-in (`checkin_biz.py`)

* The employee and company come from the JWT and the verified active company; the body only carries `punch_type`,
  `device_id` and `channel`.
* Check-in is enabled per company by creating an active device of type `web` or `mobile`. If that device has
  `requires_wfh_approval`, an approved `wfh_requests` row covering today is required (the legacy rule), otherwise 403.
* The punch type is optional: the default is the suggested next direction (OUT while a session is open).
* The same punch type within the duplicate window returns 409.
* The punch becomes a raw punch (`external_punch_id = self:<uuid>`, located at the device's location) and an event,
  then goes through **the same** `process_new_events` as collector punches.
* `GET check-in/` returns the status: work date, suggested direction, last punch and today's summary.

### Corrections (`correction_biz.py`, capability `attendance.correct`)

* **Add punch**: creates an event with `is_manual = true`, `source = manual` and a reason. The time cannot be in the
  future. It is processed immediately.
* **Void**: sets `status = void` with a reason, who and when, then rebuilds that day. The original punch is never
  deleted.
* **Reprocess** `{from_date, to_date (≤ 62 days), employee_ids?, refresh_shift}`: recomputes the work dates of every
  event around the range, then rebuilds each day up to today. It is capped at 5,000 employee-days per request; use
  the management command for bigger jobs.
* The employee must be inside the caller's company **and** data scope (§14). Every correction is audited.

---

## 13. Nightly finalization and recalculation

A day with no punches never triggers processing, so absences have to be created by a job:

* **Celery beat** `finalize_attendance_v2` runs at **23:30** for **yesterday**. By then even an overnight shift's
  window (end + 8 h by default) has closed, so an open session becomes `incomplete` instead of `present`.
* `AttendanceDailyJobBL.run(date)` covers every active company with the `attendance` module enabled, and every active
  member in it. One failing company is logged and does not stop the others.
* Manual run: `python manage.py process_attendance_v2 --date 2026-09-24 [--to-date …] [--company 4]`. Use it for
  back-fills and after bulk shift changes.

---

## 14. Multi-company isolation, permissions and scope

### Company isolation

| Caller | Where the company comes from | Never trusted |
|---|---|---|
| Employee / admin (JWT) | `X-Company-Id`, verified against an **active membership** on every request by `ModuleGateMiddleware` → `active_company_id(user_id)` | Any company id in a body or query |
| Collector | The `attv2_collector.company_id` of the authenticated collector | Payload company, employee, device and location ids |

Every DA query filters by that company. Ids from another company behave as **not found (404)**, so they cannot be
probed. An employee code of another company's employee is reported exactly like an unknown code. Every reference in a
write (parent location, branch, device, shift, employee, team lead) is checked to belong to the same company.

The package `pTracker.api.attendance_v2` is registered as the `attendance` product module, so a company without that
module enabled gets 403 on every V2 endpoint. Collector requests check the module explicitly.

### Capabilities

| Capability | Grants |
|---|---|
| `attendance.view_all` | See every employee's V2 attendance (existing capability) |
| `attendance.view_team` | See own team (`emp_lead_mapping`) plus self (existing capability) |
| *(none)* | Own attendance only |
| `attendance.manage_devices` | Locations (write), devices, collectors, keys, raw punches, sync logs |
| `attendance.manage_shifts` | Shifts, schedules, assignments (write and full list), company attendance settings |
| `attendance.correct` | Manual punch, void, reprocess (only for employees within the caller's scope) |

Locations, shifts, settings and the calendar are readable by any member, because they're needed for filters and
check-in. Checks run in the biz layer (`require_capability`, `ensure_employee_visible`, `narrow_employee_ids`). The
Angular menus only hide things; they are not the security boundary.

---

## 15. Errors, logging and monitoring

* **Expected errors** are raised as `V2Error(message, status, errors)` and returned as
  `{"error": …, "errors": [...], "status": N}`. Serializer errors are flattened to `"field: message"` strings.
* **Unexpected errors:** every biz entry point is wrapped in `@guarded(name)`. It logs the traceback to the existing
  `Logs` table, tagged `[attendance_v2]` with the operation, a reference id, the company and the user. The client gets
  `500 "Something went wrong. Reference: <id>"` with no internals. Collector ingestion errors are logged with the
  company, collector id and request id.
* **Never logged:** collector keys. The audit log stores configuration diffs only.

### "What happened to this punch?" (spec §23)

| Question | Where to look |
|---|---|
| Did the collector send it? | Collector's own log (it logs `request_id` per batch) |
| Did the API receive it? | `attv2_sync_log` (per batch: counts, errors, request id, IP) |
| Was the device valid? | Rejected batch / per-punch error in the sync log |
| Was the employee identified? | `attv2_raw_punch.status = unresolved_employee` |
| Was it a duplicate? | `duplicate_count` in the sync log; the raw punch exists once |
| Was it processed / attendance generated? | Raw punch `processed_at` → event `attendance_date` → daily row and sessions |
| Is the collector alive? | Collector `last_seen_at` / `last_success_at` / `effective_status`; dashboard |
| Who changed what? | `attv2_audit_log` |

---

## 16. The external collector

`collectors/attendance_agent/` is a separate Python process, not part of Django.

```
PunchSource (vendor)            CollectorAgent (core.py)                        AttendanceApiClient
  fetch_since(since) ──────────> pending{external_punch_id → punch}  ──batch──> POST punches/
  → [StandardPunch]              watermark (in memory)                          POST collector/heartbeat/ (thread)
```

* `StandardPunch` is the contract: `employee_code`, an aware `punch_time`, a stable `external_punch_id`, an optional
  `punch_type`, `raw_data` and an optional per-punch `device_id`.
* **No local database.** At start-up the watermark is `now − ATTV2_LOOKBACK_HOURS`, so after a restart the collector
  re-reads and re-sends that window. The server's idempotency turns the re-sends into `duplicates`. The watermark keeps
  a 10-minute overlap so late-written rows are not missed.
* **Retry:** a batch leaves the in-memory `pending` buffer only after a successful response. Network errors, 429 and
  5xx use exponential back-off from `poll_seconds` up to 15 min. 400/401/403/404 are treated as configuration errors
  and retried slowly (every 5 min) with loud logs.
* **Heartbeat thread:** reports `online`, or `error` with the last error message.
* **eSSL source:** runs `SELECT EmployeeCode, LogDate, Direction, DeviceSerialNo FROM Att WHERE LogDate >= ?`
  (parameterised). Its `external_punch_id` is `ESSL-` + `sha1(serial|code|LogDate)`, which is deterministic because
  `Att` has no row id. `Direction` in/out maps to IN/OUT. `ESSL_SERIAL_DEVICE_MAP` sends punches from several physical
  devices under their own device codes.
* **ZKTeco source:** uses `pyzk`. Punch code 0 maps to IN and 1 to OUT; other codes are sent without a direction.
* HTTPS is enforced (`ATTV2_ALLOW_HTTP=1` exists for local testing only). Credentials come from environment variables
  only.

---

## 17. Frontend

`xdesk-frontend/src/app/modules/attendance-v2/` is a lazy module at `/attendance-v2`, using `data: { module: 'attendance' }`.

* `AttendanceV2Service` wraps `/api/attendance/v2/`. The global interceptor adds the JWT and `X-Company-Id`.
  `errorMessage()` turns `{error, errors}` into a readable message.
* `V2PageBase` provides shared alerts, loading state and the `me/access/` flags (`scope`, `can_manage_devices`,
  `can_manage_shifts`, `can_correct`) that decide which buttons show.
* Screens:

  | Screen | What it does |
  |---|---|
  | Dashboard | Web check-in plus status counts and collector health |
  | Daily Attendance | Filters and a list; the detail modal shows sessions and punches, and admins can add, remove or recalculate |
  | Shift Calendar | The computed shift calendar for an employee |
  | Shifts | Shift form plus the weekly schedule editor |
  | Shift Assignments | Assign or change shifts, end dates |
  | Locations | The location hierarchy |
  | Devices | Device configuration |
  | Collectors | One-time key panel, rotation, auto-refreshing status |
  | Raw Punches | Expandable `raw_data` per punch |
  | Sync Logs | Per-batch errors |
  | Settings | Rules, recalculate, audit log |

* Routes for device administration carry `capability: 'attendance.manage_devices'` for `AccessGuard`. The `_nav.ts`
  **Attendance V2** menu adds its entries from the same capabilities.

---

## 18. Configuration reference

### Django settings (optional) — `settings.ATTENDANCE_V2 = {...}`

| Key | Default | Meaning |
|---|---|---|
| `REQUIRE_HTTPS` | `not DEBUG` | Reject plain-HTTP collector calls |
| `COLLECTOR_RATE` | `120/min` | Throttle per collector (local-memory cache, per process) |
| `MAX_BATCH_SIZE` | 500 | Punches per request |
| `MAX_PUNCH_AGE_DAYS` | 60 | Reject older punches |
| `MAX_FUTURE_SKEW_MINUTES` | 10 | Clock-skew tolerance |
| `MAX_RAW_DATA_BYTES` | 4096 | `raw_data` size limit |

Timestamps are stored as **naive server-local** time, because the project runs `USE_TZ = False` with
`TIME_ZONE = 'Asia/Kolkata'`.

### Company settings — `attv2_settings` (Settings screen)

| Field | Default |
|---|---|
| `duplicate_punch_window_minutes` | 2 |
| `unspecified_punch_mode` | `alternate` (or `first_last`) |
| `collector_offline_after_minutes` | 15 |
| `use_holiday_calendar` | true |
| `use_leave_records` | true |

### Shift fields (per shift)

| Field(s) | Meaning |
|---|---|
| `start_time`, `end_time` | End ≤ start means an overnight shift |
| `expected_work_minutes` | Expected work for the day |
| `grace_in_minutes`, `grace_out_minutes` | Grace before late / early departure applies |
| `break_minutes`, `break_start`, `break_end` | Break length and optional fixed break window |
| `is_flexible` | No late / early marking |
| `min_present_minutes`, `half_day_minutes` | Thresholds for present / half day |
| `overtime_enabled`, `overtime_basis`, `min_overtime_minutes` | Overtime rules |
| `checkin_window_before_minutes` (240), `checkout_window_after_minutes` (480) | Punch window around the shift |

Weekday overrides go in `attv2_shift_schedule`.

---

## 19. Worked examples

These are the actual cases checked against the dev database. Setup: General shift 09:00–18:00, expected 480, grace-in
15, break 60 (no fixed window), overtime after shift end with a 30-minute minimum, present ≥ 360, half day ≥ 240,
Saturday and Sunday off, Friday 09:00–17:00.

| Day | Punches | Sessions | Result |
|---|---|---|---|
| Tue 15 | 09:10 IN, 12:15 OUT, 13:05 IN, 18:45 OUT | 185 + 340 min | gross 525, break 50, unpaid 60 − 50 = 10 → **work 515**; not late (09:10 ≤ 09:15); **OT 45** (18:45 − 18:00 ≥ 30); present |
| Wed 16 | 09:20, 09:21, 18:00 (no direction) | 09:21 ignored → 09:20–18:00 | gross 520, no punched break → unpaid 60 → work 460; **late 20 min**; present |
| Thu 17 | 09:00 IN only | missing OUT | after the window closes → **incomplete**. Adding a manual 18:05 OUT → present; voiding it → incomplete again |
| Night shift, Tue 22 → Wed 23 | 22:05 IN, 05:58 OUT (+1 day) | one session on **Tue 22** | work 473; nothing recorded on Wed 23 |
| Sat 19 / Sun 20 | none | — | weekly_off |
| Grace changed 15 → 30 after the fact | reprocess Wed 16 | — | still late (the stored snapshot is kept); with `refresh_shift` → not late |

---

## 20. Extending Attendance V2

| To add… | Do this | Do **not** |
|---|---|---|
| A new device vendor | Write a `PunchSource` subclass in `collectors/attendance_agent/` that returns `StandardPunch`es; add a device (type `other_biometric` or a new choice) and a collector in the UI | Add vendor branches to the backend |
| A new ingestion channel (e.g. a kiosk app) | Create raw punch + event and call `AttendanceProcessorBL.process_new_events` (see `checkin_biz.py`) | Write daily rows directly |
| A new attendance rule | Add a column to `AttendanceShift` or `AttendanceSettings`, copy it into `build_snapshot()` / `RuleSettings`, and use it in `summarize()` / `pair_events()` | Hard-code a value or a company check |
| A new org level for shifts (e.g. department) | Add a scope to `ASSIGNMENT_SCOPES` / `ASSIGNMENT_PRIORITY`, a target FK, and matching in `DayPlanBL._targets_employee` and `ShiftDA.get_assignments_covering` | — |
| Payroll overtime | Read `attv2_daily_attendance.overtime_minutes` | Recompute overtime elsewhere |

`pair_events()` and `summarize()` have no DB access. When a test suite is added to this repo, they are the natural
place to start unit tests.

---

## 21. Troubleshooting

| Symptom | Likely cause / check |
|---|---|
| Collector gets 401 | Wrong or rotated key, collector deactivated, or company inactive |
| Collector gets 403 "HTTPS is required" | Proxy isn't sending `X-Forwarded-Proto: https`, or the collector uses `http://` |
| 403 "Device … is not configured for this collector" | Device not linked to the collector, inactive, or a web/mobile type |
| Punches `failed`: "Employee code … does not exist" | The code isn't an active member of that company (`auth_user.username` + active membership). Fix it, then let the collector re-send |
| Nobody shows as absent | No shift assigned (add a company default), or the nightly job isn't running (check Celery beat) |
| Days marked `incomplete` | Missing OUT (or IN) after the shift window closed. Add a manual punch |
| A night-shift OUT lands on the wrong day | Check the shift timings and the punch windows; the planner uses the previous day's `window_end` |
| A shift edit didn't change old days | Expected: past days keep their snapshot. Reprocess with "apply current shift rules" |
| Collector shows offline | No heartbeat within `collector_offline_after_minutes`. Check the agent process and network |
| Web check-in button missing | No active `web` device for the company |
