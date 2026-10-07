# Release Notes — Attendance V2 (device-independent attendance)

**Release date:** 2026-09-28
**Repos:** `xdesk-backend`, `xdesk-frontend`
**Spec:** [docs/attendence_v2.md](attendence_v2.md)
**SQL:** [docs/sql/attendance_v2_up.sql](sql/attendance_v2_up.sql) · rollback [docs/sql/attendance_v2_down.sql](sql/attendance_v2_down.sql)

## 1. Summary

Attendance V2 is a new attendance module that runs **alongside** the existing eSSL-based attendance. Punches now arrive
from any source through one standard API. Supported sources are eSSL, ZKTeco and other biometric devices through an
external collector, plus web/mobile check-in, API integrations and manual corrections. A central engine turns the
punches into sessions and daily attendance using company-configured shifts.

```
Device ─> External collector (vendor specific) ─HTTPS─> /api/attendance/v2/punches/
                                                           │
Web / mobile check-in ─────────────────────────────────────┤
Manual correction ─────────────────────────────────────────┤
                                                           v
              Raw punch ─> Event ─> (shift + calendar + leave rules) ─> Sessions ─> Daily attendance
```

**The legacy attendance module is unchanged.** It keeps the same endpoints, code, tables and responses. No existing
API response changed.

## 2. Legacy vs V2 components

| Area | Legacy (unchanged) | Attendance V2 (new) |
|---|---|---|
| API | `pTracker/api/attendance/*` at `/api/attendance/`, `/v1/api/attendance/` | `pTracker/api/attendance_v2/*` at `/api/attendance/v2/` |
| Data access | `dataaccess/ptracker_access/attendance.py`, `dataaccess/essl_access/attendance.py` (MSSQL `Att`) | `dataaccess/attendance_v2_access/*_da.py` |
| Tables | `daily_attendance`, `wfh_requests`, eSSL `Att` | 14 new `attv2_*` tables (section 4) |
| Frontend | `modules/attendance`, `modules/work-from-home` | `modules/attendance-v2` at `/attendance-v2` |
| Device coupling | Reads eSSL DB directly | None: collectors send a standard payload |

**Reused (not duplicated):**
- Company / Branch / Membership / Role / Capability from `platform_access`.
- Company isolation via `X-Company-Id` and `ModuleGateMiddleware`.
- `has_capability` / `data_scope` (`attendance.view_all` / `view_team`).
- Team structure `emp_lead_mapping`.
- Holiday calendar (`holidays`, `additional_working_days`, via `platform_company.legacy_company_id`).
- Approved leave (`leaves`, status 2).
- Approved WFH (`wfh_requests`).
- Employee code = `auth_user.username`, the same identifier the legacy module and eSSL use.

## 3. What's new

### Backend
- **Collector API** (machine-to-machine):
  - Authentication uses `X-Collector-Id` + `X-Collector-Key`. The key is issued once and stored only as a SHA-256 hash.
  - HTTPS is enforced when `DEBUG` is off, and requests are rate-limited per collector.
  - Batch submission accepts up to 500 punches per request.
  - The response reports `accepted` / `duplicates` / `failed` counts, with per-punch errors, a `request_id` and a `sync_id`.
- **Idempotency.** Uniqueness is on `(device, external_punch_id)`. When a device gives no id, the server derives a deterministic one from device + employee code + time, so a retried punch is never stored twice.
- **Unknown employee codes** are kept as `unresolved_employee` raw punches for troubleshooting. They are linked automatically when the same punch is sent again after the employee is set up.
- **Engine**:
  - Supports multiple IN/OUT sessions per day, missing IN/OUT, double-punch suppression, and devices that record no direction (alternate IN/OUT or first/last punch).
  - Overnight shifts are handled: a 22:05 IN and 05:58 OUT form one session on the shift's work date.
  - Calculates late arrival (after grace), early departure, break (from punches or the configured break window), overtime (after shift end, or beyond expected minutes, with a minimum), and present / half-day thresholds.
  - Handles holiday, weekly off, and full or half-day leave.
- **Shift management**:
  - Shifts carry per-weekday schedule overrides (weekly offs, different Friday timings, …).
  - Assignments can target an employee, a team (reporting lead), a branch or the company default. When several apply, the most specific wins in that order.
  - Assignments are never overwritten. A shift change closes the running assignment the day before and keeps it in history. A temporary change automatically resumes the original shift afterwards.
  - **History is stable.** Each daily row stores a snapshot of the shift rules it was calculated with. Editing a shift does not silently change past days; use *Recalculate* with “apply current shift rules” to do that deliberately.
- **Corrections**: add a missed punch, or void a wrong one (the original is never deleted), then recalculate a range.
- **Monitoring**:
  - The raw punch store keeps each device's original record.
  - A sync log records every batch.
  - Collector heartbeat (version, status, last seen / last successful sync) with automatic offline detection.
  - An audit log records config, shift, assignment and correction changes. Secrets are never logged.
- **Web / mobile check-in** goes through the same pipeline. It is enabled per company by creating a `web` / `mobile` device, which can optionally require an approved WFH request.
- **Nightly job** (`finalize_attendance_v2`, Celery beat at 23:30 for the previous day) builds absent / leave / holiday / weekly-off / incomplete rows. The same logic can be run manually: `python manage.py process_attendance_v2 [--date YYYY-MM-DD] [--to-date …] [--company ID]`.

### Frontend (Angular, menu **Attendance V2**)
Screens: Dashboard (with web check-in), Daily Attendance (sessions, punches and corrections in a detail view), Shift
Calendar, Shifts (with weekly schedule), Shift Assignments, Locations, Devices, Collectors (one-time key display, key
rotation, live status), Raw Punches, Sync Logs, and Settings (rules, recalculate, audit log). Menu items and routes
follow the V2 capabilities; the API re-checks every call.

### Reference collector
[`collectors/attendance_agent/`](../collectors/attendance_agent/README.md) is a stand-alone Python agent with no
database. Its vendor-neutral core (`core.py`) handles batching, retry with back-off, heartbeat and restart-safe
re-send. It ships with an eSSL source (`essl_agent.py`, reading the same `Att` table as the legacy module, with
parameterised SQL) and a ZKTeco example (`zkteco_agent.py`, `pyzk`). Credentials come from environment variables only.

## 4. Database changes

**No ALTER to any existing table.** New tables only (Django app `attendance_v2_access`, managed, with migrations):

| Table | Purpose |
|---|---|
| `attv2_location` | Company location hierarchy (building / floor / area / room, any depth), optional link to `platform_branch` |
| `attv2_device` | Device config (eSSL, ZKTeco, other biometric, web, mobile, API, manual) |
| `attv2_collector`, `attv2_collector_devices` | Collector config/monitoring, hashed key, allowed devices |
| `attv2_sync_log` | One row per punch batch (and failed heartbeats) |
| `attv2_raw_punch` | Original punch as received; unique `(device_id, external_punch_id)` |
| `attv2_event` | Normalized punch (IN / OUT / UNSPECIFIED, work date, manual/void flags) |
| `attv2_shift`, `attv2_shift_schedule`, `attv2_shift_assignment` | Shifts, weekday overrides, dated assignments |
| `attv2_daily_attendance` | Daily summary + shift snapshot; unique `(company, employee, date)` |
| `attv2_session` | IN/OUT pairs per work date |
| `attv2_settings` | Company-wide rules (duplicate window, undirected-punch mode, offline threshold, calendar/leave use) |
| `attv2_audit_log` | Change history |

Data rows: 3 new capabilities in `platform_capability`: `attendance.manage_devices`, `attendance.manage_shifts`,
`attendance.correct`.

## 5. Changes to existing files

Backend (all additive):
- `pTracker/settings/base.py`: `pTracker.dataaccess.attendance_v2_access` added to `INSTALLED_APPS`.
- `pTracker/urls.py`: `api/attendance/v2/` mounted before `api/attendance/`.
- `pTracker/common/module_registry.py`: `pTracker.api.attendance_v2` gated as the `attendance` module.
- `pTracker/common/module_gate_middleware.py`: non-employee principals (collectors) now pass through to their own view permissions, as the middleware docstring already described. Previously any non-PlatformUser principal was treated as an employee. Employee behaviour is unchanged.
- `pTracker/celery_beat.py`, `pTracker/celery_imports.py`: new `finalize_attendance_v2` task.
- `pTracker/dataaccess/platform_access/migrations/0014_seed_attendance_v2_capabilities.py`: new.

Frontend: `src/app/_nav.ts` (new menu), `src/app/app.routing.ts` (lazy route), `src/environments/api-urls.ts`,
`src/environments/app-urls.ts`.

## 6. API (`/api/attendance/v2/`)

| Endpoint | Methods | Access |
|---|---|---|
| `punches/`, `collector/heartbeat/` | POST | Collector key |
| `me/access/`, `dashboard/`, `employees/`, `branches/`, `check-in/` | GET (+POST check-in) | Any member; data by scope |
| `daily/`, `daily/detail/`, `sessions/`, `events/`, `shift-calendar/` | GET | Self / team / all by `attendance.view_*` |
| `corrections/`, `events/<id>/void/`, `reprocess/` | POST | `attendance.correct` + employee in scope |
| `locations/`, `locations/<id>/` | GET (any) / POST PUT DELETE | `attendance.manage_devices` |
| `devices/…`, `collectors/…`, `collectors/<id>/rotate-key/`, `raw-punches/`, `sync-logs/` | CRUD / GET | `attendance.manage_devices` |
| `shifts/…`, `shifts/<id>/schedule/`, `employee-shifts/…`, `settings/` | GET (any) / writes | `attendance.manage_shifts` |
| `audit-logs/` | GET | any V2 admin capability |

Errors are `{ "error": "...", "errors": [...], "status": N }` with 400 / 401 / 403 / 404 / 409 / 500. Unexpected
errors return a reference id and are logged server-side with company, user or collector, and request id. They never
include internals or keys. Another company's ids return 404.

## 7. Deployment steps

1. Deploy backend and frontend code.
2. Apply the schema: `python manage.py migrate attendance_v2_access`. **Do not run a plain `migrate`**, because other apps have unrelated pending migrations. Alternatively, run `docs/sql/attendance_v2_up.sql` (sections 1, 2 and 4).
3. Grant the new capabilities. Either re-run `create_memberships_from_groups` (wildcard roles pick them up), or run section 3 of the SQL. Review the role list first (see §9).
4. Restart the Celery worker and beat so `finalize_attendance_v2` is scheduled.
5. If TLS terminates at a proxy, make sure it forwards `X-Forwarded-Proto: https`. Otherwise collector calls are rejected when `DEBUG` is off.
6. In the app:
   - Create shifts and a **company default** assignment. Without any shift, no absent/off rows are produced; only days with punches are recorded.
   - Create locations, devices and collectors.
   - Install the collector with its key.
   - Optionally add a `web` device to enable web check-in.

Optional settings (`settings.ATTENDANCE_V2 = {...}`): `REQUIRE_HTTPS` (default `not DEBUG`), `COLLECTOR_RATE`
(`120/min`), `MAX_BATCH_SIZE` (500), `MAX_PUNCH_AGE_DAYS` (60), `MAX_FUTURE_SKEW_MINUTES` (10), `MAX_RAW_DATA_BYTES` (4096).

**Rollback:** `python manage.py migrate attendance_v2_access zero && python manage.py migrate platform_access 0013_seed_rewards_view_scope` (or `docs/sql/attendance_v2_down.sql`), then revert the code. This deletes all V2 data; legacy is unaffected.

## 8. Verification performed

- **Backend: 73 end-to-end checks** against the dev database (`ptracker_demo`). They ran through the real URLs, middleware and JWT auth, inside a transaction that was rolled back, and the V2 tables were confirmed empty afterwards. Coverage:
  - multiple buildings/locations, a hierarchy cycle, duplicate codes
  - invalid key / collector / device, and a collector-id mismatch
  - duplicate and retried batches; an invalid employee re-linked later
  - future and invalid timestamps
  - multiple IN/OUT, undirected punches with a double tap, missing OUT
  - night shift across midnight, late / overtime / break figures
  - scope (self / team / all), manual add and void
  - temporary shift change with history kept, overlap rejection
  - calendar with weekly off and a Friday override
  - shift edit without and with `refresh_shift`
  - web check-in and its double-punch 409
  - cross-company isolation (config, employees, collector posting another company's employee, a foreign `X-Company-Id`)
  - HTTPS enforcement, key rotation, dashboard
  - legacy `/api/attendance/` still routed
- **Collector: 6 checks** with the real agent code routed into the API (rolled back): network failure keeps punches buffered, retry delivers them, a restart re-send is idempotent, new punches are picked up, heartbeat works.
- **Nightly job:** smoke-tested (rolled back).
- **Frontend:** `ng build --configuration development` compiles cleanly.
- **SQL:** section 1 is the exact DDL applied by the migration; sections 2–4 were executed and rolled back on dev.
- **Dev DB state now:** the 14 tables are created, both migrations are recorded, and the 3 capabilities are granted to Digital Mesh Director / HR / Manager and EM Soft CEO / HR Manager. No V2 configuration data exists.

## 9. Known limitations and follow-ups

- **No automated test suite exists in this repo.** The checks above were run from scratch scripts and were not added to the repo, because the DB user cannot create a test database.
- **Not tested against real devices.** The collector was not run against a real eSSL MSSQL server or a ZKTeco device (`pyodbc` / `pyzk` are not installed on the dev machine). The Angular screens compile but were not click-tested in a browser.
- **Role grants need review.** Manager received the new admin capabilities only because its *sample* mapping has `attendance.*`. Confirm whether Managers should manage devices and shifts, or correct attendance.
- **No department model exists**, so shift priority is Employee → Team → Branch → Company. Branch comes from the employee's membership.
- **Timezone.** Times are stored as server-local naive datetimes (`USE_TZ=False`, `Asia/Kolkata`); collector timestamps with an offset are converted. Branches in other timezones are not yet handled separately.
- **Punches are processed synchronously** on receipt. For large historical back-fills, use the `process_attendance_v2` command.
- **Rate limiting uses the local-memory cache**, so the limit applies per application process.
- **Overtime is calculated but not integrated with payroll**; no payroll overtime rules were found.
- **The shift calendar is computed.** There is no separate roster table.
- **No mobile client changes.** The React Native app is not on this machine. The API already supports `channel: "mobile"` with a `mobile` device.
- **Parallel run with the legacy module.** The eSSL collector reads the legacy `Att` table, which also contains legacy web punches (`Web IN/OUT` rows). To attribute those to a separate V2 device, map their serial with `ESSL_SERIAL_DEVICE_MAP`.
