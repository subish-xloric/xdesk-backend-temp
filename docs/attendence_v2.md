# Attendance V2 — Device-Independent Attendance Architecture

## Objective

We currently have an existing Attendance module in the application that is tightly coupled with **eSSL**. The current application directly communicates with the eSSL device/database/API and fetches punch data.

We do **not** want to significantly modify or risk breaking the existing attendance implementation.

Instead, create a new **Attendance V2** implementation alongside the existing module.

The goal of Attendance V2 is to make attendance **device-independent** so that we can support eSSL, ZKTeco, other biometric devices, Web Check-in, Mobile Check-in, API-based attendance, and future devices without changing the core attendance business logic.

DO not make any change in responce of current exsiting API

---

# 1. Important Existing-System Requirement

First inspect the existing project and understand:

* Current Attendance module
* Existing attendance models
* Existing eSSL integration
* Existing views/API endpoints
* Existing serializers
* Existing services/business logic
* Existing frontend attendance screens
* Existing employee/user relationships
* Existing company structure
* Existing location/facility structure, if any
* Existing authentication and permissions

### IMPORTANT

Do **not** modify the current Attendance module unnecessarily.

The current attendance functionality must continue working exactly as it does today.

Attendance V2 should be implemented as a **new version/module**, reusing existing common models/utilities where appropriate, but keeping the V2 implementation logically separated from the legacy implementation.

Before making changes, identify the current attendance implementation and clearly document which files/models are legacy and which files will belong to Attendance V2.

---

# 2. Main Architecture

The new architecture should be:

```text
Biometric Device
      |
      v
External Python Collector
      |
      | HTTPS / REST API
      v
Attendance V2 API
      |
      v
Raw Punch
      |
      v
Normalized Attendance Event
      |
      v
Attendance Session
      |
      v
Daily Attendance
```

Examples:

```text
eSSL Device
    |
    v
Python eSSL Collector
    |
    v
Attendance V2 API
```

```text
ZKTeco Device
    |
    v
Python ZKTeco Collector
    |
    v
Attendance V2 API
```

```text
Web Check-in
    |
    v
Attendance V2 API
```

```text
Mobile Check-in
    |
    v
Attendance V2 API
```

The core application must **not contain device-specific eSSL/ZKTeco logic** in the V2 attendance business logic.

---

# 3. External Python Collector

The external collector will be a separate Python application/script.

For example:

```text
attendance-agent-essl
attendance-agent-zkteco
```

Each device type may have a different collector because each manufacturer/device exposes attendance data differently.

For example:

```text
eSSL
  -> eSSL Python Collector

ZKTeco
  -> ZKTeco Python Collector
```

Both collectors must send the same standardized payload to the Attendance V2 API.

---

# 4. DATABASE IN THE EXTERNAL COLLECTOR


The external Python collector 



* SQLite


The collector should be lightweight.

Its responsibility is only:

```text
Connect to device
      ↓
Fetch punch records
      ↓
Transform/map device-specific data
      ↓
Send records to central Attendance V2 API
```

The central application/database is responsible for persistence, duplicate detection, processing, attendance calculation, etc.

If retry handling is required, implement a simple in-memory/retry mechanism or a mechanism appropriate for the collector environment, but do not introduce a local database.

---

# 5. Collector Responsibilities

The Python collector should:

1. Connect to the device.
2. Fetch new punch records.
3. Read the device-specific employee identifier.
4. Read punch date/time.
5. Read punch state/type if available.
6. Identify the configured device.
7. Convert the device-specific response into a common payload.
8. Send the payload to the central Attendance V2 API.
9. Handle API errors.
10. Log synchronization errors.
11. Provide useful logging for troubleshooting.

The collector should **not**:

* Calculate employee working hours.
* Decide company attendance rules.
* Calculate overtime.
* Decide late/early status.
* Pair IN/OUT records.
* Maintain the central attendance database.
* Implement company-specific attendance policies.

Those responsibilities belong to the central application.

---

# 6. Standard Attendance API Payload

Create a standard API contract independent of the biometric vendor.

Example:

```json
{
    "collector_id": "COL-001",
    "device_id": "ESSL-001",
    "employee_code": "EMP1025",
    "punch_time": "2026-09-23T08:52:14+05:30",
    "punch_type": "IN",
    "source": "essl",
    "location_code": "BLD-A-GF-PROD",
    "external_punch_id": "ESSL-20260923-1025-0001"
}
```

The exact fields should be finalized after inspecting the existing system and the data actually available from eSSL.

Do not blindly assume that every device provides an IN/OUT state.

The API should support devices where the punch state is unavailable and allow the central system to determine the event based on attendance rules/sequence if required.

---

# 7. Attendance Locations

The system must support companies with:

* Multiple buildings
* Multiple floors
* Multiple office spaces
* Multiple production areas
* Multiple meeting rooms
* Multiple facilities within one building

Do not hardcode a fixed number of buildings/floors/areas.

Prefer a hierarchical location structure.

Example:

```text
Company
 |
 +-- Building A
 |     |
 |     +-- Ground Floor
 |     |      |
 |     |      +-- Reception
 |     |      +-- Production Floor
 |     |
 |     +-- First Floor
 |            |
 |            +-- HR
 |            +-- Meeting Room 1
 |
 +-- Building B
        |
        +-- Ground Floor
               |
               +-- Production Area
```

A self-referencing `AttendanceLocation` model can be considered:

```text
AttendanceLocation
------------------
id
company
parent
name
code
location_type
is_active
```

Possible location types:

```text
company
building
floor
area
room
```

Inspect the existing project first. If an appropriate existing location/facility model already exists, reuse it rather than unnecessarily creating duplicate structures.

---

# 8. Attendance Device

Create a central device configuration model for Attendance V2.

Example:

```text
AttendanceDevice
----------------
id
company
location
name
code
device_type
serial_number
ip_address
is_active
```

Possible device types:

```text
essl
zkteco
other_biometric
web
mobile
api
manual
```

Do not hardcode eSSL as the only device type.

Example:

```text
Device: ESSL-001
Company: ABC
Location: Building A / Ground Floor / Production
Type: eSSL
```

Another:

```text
Device: ZK-001
Company: ABC
Location: Building B / Ground Floor / Reception
Type: ZKTeco
```

---

# 9. Attendance Collector

Create a central configuration model representing the external Python collector.

Example:

```text
AttendanceCollector
-------------------
id
company
device
collector_id
collector_type
version
last_seen_at
last_sync_at
last_success_at
status
is_active
```

This is NOT the Python application's database.

It is simply central configuration/monitoring information about the collector.

For example:

```text
Collector: COL-001
Type: eSSL
Device: ESSL-001
Version: 1.0.0
Last Sync: 2026-09-23 08:55
Status: Online
```

---

# 10. Raw Punch

Create a central raw punch table.

The raw punch should preserve the original data received from the collector.

Example:

```text
AttendanceRawPunch
------------------
id
company
collector
device
employee
external_employee_id
external_punch_id
punch_time
raw_punch_type
source
location
raw_data
received_at
processed
```

`raw_data` can be JSON.

This is important because different devices may provide different fields.

Example eSSL raw data:

```json
{
    "user": "1025",
    "timestamp": "2026-09-23 08:52:14",
    "state": 0,
    "device": "ESSL001"
}
```

The original information should remain available for troubleshooting/auditing.

---

# 11. Duplicate Protection

The API must be idempotent.

The same punch may be sent more than once because of:

* Network failures
* API timeout
* Collector retry
* Device synchronization issues

Do not create duplicate attendance records.

Where possible, use:

```text
device_id + external_punch_id
```

as a unique identifier.

If the device does not provide a reliable unique punch ID, design a deterministic fallback after inspecting the device data.

The API should return a meaningful response for already-processed punches rather than creating another attendance event.

---

# 12. Normalized Attendance Event

After receiving the raw punch, normalize it into a common attendance event.

Example:

```text
AttendanceEvent
---------------
id
company
employee
event_time
event_type
location
device
source
raw_punch
is_manual
created_at
```

Possible event types:

```text
IN
OUT
```

But do not assume that all devices provide IN/OUT information.

The design should support:

```text
Explicit IN/OUT
```

and

```text
Unspecified punch
```

where the central attendance engine determines the appropriate event/session.

---

# 13. Attendance Session

Support multiple IN/OUT periods during the same working day.

Example:

```text
08:55 IN
12:15 OUT
13:05 IN
18:10 OUT
```

This should become:

```text
Session 1
08:55 - 12:15

Session 2
13:05 - 18:10
```

Do not assume that one employee has only one IN and one OUT per day.

Create an `AttendanceSession` model or equivalent business layer.

It should retain:

```text
employee
company
attendance_date
check_in
check_out
check_in_location
check_out_location
check_in_event
check_out_event
duration
status
```

---

# 14. Daily Attendance

Create a daily summary layer.

Example:

```text
EmployeeDailyAttendance
-----------------------
employee
company
attendance_date
first_in
last_out
total_work_minutes
total_break_minutes
status
first_in_location
last_out_location
remarks
```

Ensure there is only one daily summary for an employee/company/date combination where appropriate.

---

# 15. Attendance Processing

The central application should be responsible for:

* Pairing IN/OUT
* Multiple sessions
* Missing OUT
* Duplicate punches
* Late arrival
* Early departure
* Working hours
* Break duration
* Overtime
* Shift rules
* Grace periods
* Attendance status
* Manual corrections

Do not put these rules into the eSSL/ZKTeco collector.

---

# 16. Authentication Between Collector and API

The external collector must authenticate securely with the Attendance V2 API.

Inspect the existing application's authentication architecture and implement an appropriate mechanism.

Possible approach:

```text
Collector ID
+
Collector API Key / Secret
```

or another secure token-based mechanism already consistent with the application.

Do not hardcode credentials inside source code.

Collector credentials should be configurable through environment/configuration.

---

# 17. Collector Heartbeat

The collector should periodically report its status to the central API.

Example:

```http
POST /api/attendance/v2/collector/heartbeat/
```

Payload:

```json
{
    "collector_id": "COL-001",
    "version": "1.0.0",
    "device_id": "ESSL-001",
    "status": "online"
}
```

The central application should be able to show:

```text
Collector
Last Seen
Last Successful Sync
Device
Status
Version
```

This will help administrators identify when an attendance collector/device has stopped communicating.

---

# 18. Sync API

Consider supporting batch submission instead of only one punch per HTTP request.

For example:

```http
POST /api/attendance/v2/punches/
```

```json
{
    "collector_id": "COL-001",
    "device_id": "ESSL-001",
    "punches": [
        {
            "employee_code": "EMP001",
            "punch_time": "2026-09-23T08:51:10+05:30",
            "external_punch_id": "10001"
        },
        {
            "employee_code": "EMP002",
            "punch_time": "2026-09-23T08:53:21+05:30",
            "external_punch_id": "10002"
        }
    ]
}
```

This can significantly reduce API calls when a collector synchronizes many records.

Inspect the existing project and choose a suitable approach rather than blindly implementing both individual and batch APIs.

---

# 19. API Response

The API should clearly report:

```json
{
    "success": true,
    "accepted": 10,
    "duplicates": 2,
    "failed": 0
}
```

For validation errors, return meaningful information so that the collector logs can identify the problem.

Example:

```json
{
    "success": false,
    "errors": [
        {
            "external_punch_id": "10025",
            "error": "Employee code EMP9999 does not exist"
        }
    ]
}
```

---

# 20. Versioning

Because the existing attendance implementation is tightly coupled with eSSL, create Attendance V2 using a clear namespace.

For example:

```text
/api/attendance/v2/
```

Do not replace the existing attendance API unless there is a strong technical reason.

Existing:

```text
/api/attendance/
```

New:

```text
/api/attendance/v2/
```

Similarly, keep V2 code logically separated.

Possible structure:

```text
attendance/
    legacy/
        ...

    v2/
        models.py
        serializers.py
        views.py
        urls.py
        services/
        processors/
        validators/
        ...
```

Adapt this to the existing Django project structure instead of forcing a new application structure if it conflicts with the project conventions.

---

# 21. Frontend

Inspect the current Angular frontend and existing attendance screens.

Do not break existing attendance functionality.

Create Attendance V2 screens where appropriate.

Potential sections:

```text
Attendance V2
 |
 +-- Dashboard
 +-- Attendance
 +-- Daily Attendance
 +-- Sessions
 +-- Locations
 +-- Devices
 +-- Collectors
 +-- Raw Punches
 +-- Sync Logs
 +-- Corrections
 +-- Settings
```

Only implement screens that fit the current application's existing architecture and requirements.

Follow the existing UI components, styling, permissions, alerts, loading states, validation and error-handling patterns.

---

# 22. Error Handling

Follow the existing project's error-handling standards.

Do not expose raw Django/Python exceptions to users.

For API errors:

```text
400 - Validation error
401 - Authentication error
403 - Permission error
404 - Resource not found
409 - Duplicate/conflict where appropriate
500 - Internal server error
```

Log server-side exceptions with enough context to troubleshoot:

```text
company
collector
device
employee
external_punch_id
request ID
exception
timestamp
```

Do not log secrets/API keys.

---

# 23. Logging and Sync Monitoring

The system should make it possible to determine:

```text
Did the collector send the punch?
Did the API receive it?
Was the employee identified?
Was the device valid?
Was it a duplicate?
Was it processed?
Was attendance generated?
```

Consider an attendance synchronization log if the existing project does not already have an appropriate generic logging mechanism.

Do not duplicate existing generic error/audit logging functionality if a suitable implementation already exists.

---

# 24. Multi-Company Support

This application is intended to support multiple companies.

Attendance V2 must always correctly scope data by company.

For example:

```text
Company A
    Device A1
    Device A2

Company B
    Device B1

Company C
    Device C1
    Device C2
```

A collector/device from Company A must never be able to submit attendance against Company B.

Company identification should be derived from authenticated collector/device configuration rather than blindly trusting a company ID sent by the collector.

---

# 25. Security

Review:

* API authentication
* Collector authentication
* Permission checks
* Company isolation
* Device validation
* Input validation
* Duplicate prevention
* Rate limiting if appropriate
* Sensitive information logging
* HTTPS requirement

Do not trust:

```text
company_id
employee_id
device_id
location_id
```

from the external collector without validating that the authenticated collector is actually authorized to use them.

---

# 26. Migration / Existing Data

Do not automatically migrate the existing legacy attendance data into V2 unless it is technically necessary.

First determine:

* What the existing attendance tables contain
* Whether existing attendance history must remain accessible
* Whether V2 should reference existing employees
* Whether V2 can coexist with legacy attendance

Prefer reusing the existing Employee/User/Company models rather than creating duplicate employee models.

---

# 27. Implementation Process

Before coding:

### Step 1 — Inspect

Analyze the existing project thoroughly.

Identify:

```text
Current attendance app
Current eSSL implementation
Attendance models
Employee model
Company model
Location model
Authentication
Permissions
Current API patterns
Current Angular attendance implementation
```

### Step 2 — Document

Create a short implementation plan showing:

```text
Existing
   ↓
Legacy Attendance

New
   ↓
Attendance V2
   ↓
Collector API
   ↓
Device-independent processing
```

### Step 3 — Design

Finalize:

* Models
* API endpoints
* Authentication
* Collector contract
* Processing flow
* Duplicate handling
* Location hierarchy

### Step 4 — Implement Backend

Implement V2 backend first.

### Step 5 — Implement Collector Contract

Create a simple reference Python eSSL collector/client demonstrating:

```text
Fetch from eSSL
    ↓
Convert to standard payload
    ↓
POST to V2 API
```

Do not implement a database in the collector.

### Step 6 — Frontend

Implement V2 frontend screens according to the existing Angular architecture.

### Step 7 — Test

Test:

* eSSL collector
* Duplicate punches
* Invalid employee
* Invalid device
* Invalid collector
* Multiple buildings
* Multiple locations
* Multiple IN/OUT
* Missing OUT
* Network failure
* API timeout
* Collector restart
* Multiple companies
* Manual attendance
* Web attendance
* Future ZKTeco collector compatibility

---

# 28. Important Design Principle

The most important architectural rule is:

```text
DEVICE-SPECIFIC LOGIC
        |
        v
EXTERNAL COLLECTOR
        |
        | STANDARD API CONTRACT
        v
CENTRAL ATTENDANCE V2
        |
        v
DEVICE-INDEPENDENT BUSINESS LOGIC
```

For example:

```text
eSSL Collector
     |
     | standard punch
     v

                Attendance V2
                     ^
                     |
ZKTeco Collector ---+
                     ^
                     |
Web Check-in --------+
                     ^
                     |
Mobile ---------------+
```

The Attendance V2 core must never contain logic such as:

```python
if device == "essl":
    ...
elif device == "zkteco":
    ...
```

Device-specific communication belongs in the external collector.

---

# 29. Final Requirement

Do not start by blindly creating models and files.

First inspect the existing codebase and understand the current attendance implementation.

Then propose the V2 architecture based on the actual project structure.

Clearly identify:

1. Existing legacy attendance components
2. Components that can be reused
3. New Attendance V2 components
4. New database models
5. New API endpoints
6. New frontend components
7. External Python collector structure
8. Migration/coexistence strategy

Then implement Attendance V2 while ensuring the **existing eSSL-based attendance module remains unaffected**.

The final architecture should allow us to add:

```text
eSSL
ZKTeco
Other biometric devices
Web Check-in
Mobile Check-in
API integrations
```

without redesigning the central Attendance V2 business logic each time.


# 30. Shift Management / Shift & Roster Module

Attendance V2 must include a **Shift Management module** that allows each company to define and manage employee working shifts.

The shift system must be **company-specific, configurable, and independent of biometric devices**.

Shift rules must be handled by the central Attendance V2 application, not by the external eSSL/ZKTeco collectors.

---

## 30.1 Shift Management Requirements

The system should support:

* Multiple shifts per company
* Different shifts for different departments/teams
* Different shifts for individual employees
* Fixed shifts
* Flexible shifts where required
* Overnight shifts
* Shift start/end times
* Grace periods
* Break configuration
* Expected working hours
* Late arrival rules
* Early departure rules
* Overtime rules
* Shift-based attendance calculation
* Shift assignment history
* Effective dates
* Active/inactive shifts

Example:

```text
Company A

Morning Shift
    Start: 08:30
    End: 17:30
    Grace: 15 minutes
    Break: 60 minutes

General Shift
    Start: 09:00
    End: 18:00
    Grace: 10 minutes
    Break: 60 minutes

Night Shift
    Start: 22:00
    End: 06:00
    Grace: 15 minutes
```

Do not hardcode these values.

---

## 30.2 Shift Model

Create an appropriate central model, for example:

```text
AttendanceShift
----------------
id
company
name
code
description
start_time
end_time
is_overnight
expected_work_minutes
grace_in_minutes
grace_out_minutes
break_minutes
overtime_enabled
is_active
created_at
updated_at
```

The exact fields should be finalized after inspecting the existing project and its employee/company models.

Reuse existing common models where appropriate.

---

## 30.3 Weekly Shift Configuration

A shift may have different timings on different days.

Support configuration such as:

```text
Monday
    09:00 - 18:00

Tuesday
    09:00 - 18:00

Wednesday
    09:00 - 18:00

Thursday
    09:00 - 18:00

Friday
    09:00 - 17:00

Saturday
    OFF

Sunday
    OFF
```

Consider a separate model such as:

```text
AttendanceShiftSchedule
------------------------
id
shift
weekday
start_time
end_time
is_working_day
expected_work_minutes
```

Do not assume every company follows Monday-Friday working patterns.

---

## 30.4 Employee Shift Assignment

Employees must be assignable to shifts.

Example:

```text
Employee
    ↓
Shift Assignment
    ↓
Morning Shift
```

Create an appropriate model such as:

```text
EmployeeShiftAssignment
-----------------------
id
company
employee
shift
effective_from
effective_to
is_active
created_at
updated_at
```

Important:

Shift assignments must support historical changes.

Example:

```text
Employee: EMP001

01-Jan-2026 → 31-Mar-2026
    General Shift

01-Apr-2026 → 30-Jun-2026
    Morning Shift

01-Jul-2026 → Current
    Night Shift
```

Attendance processing must use the shift that was applicable on the attendance date.

Do not simply use the employee's current shift when processing historical attendance.

---

## 30.5 Department / Team Shift Assignment

If the existing system contains departments, teams, designations, or similar organizational structures, inspect whether shifts should also be assignable at those levels.

Possible hierarchy:

```text
Company
   |
   +-- Department
          |
          +-- Team
                 |
                 +-- Employee
```

Support configurable assignment where appropriate:

```text
Company Default Shift
        ↓
Department Shift
        ↓
Team Shift
        ↓
Employee Shift
```

However, do not introduce unnecessary organizational models if they already exist in the application.

First inspect and reuse the existing company/department/team structure.

---

## 30.6 Shift Priority

When determining an employee's shift for a particular attendance date, define a clear priority.

Recommended processing order:

```text
Employee-specific shift
        ↓
Team-specific shift
        ↓
Department-specific shift
        ↓
Company default shift
```

The exact hierarchy should be confirmed against the existing application's organizational structure before implementation.

The selected shift must be recorded/referenced during attendance processing so that later changes to shift configuration do not incorrectly recalculate historical attendance.

---

## 30.7 Overnight Shift

The system MUST support shifts crossing midnight.

Example:

```text
Night Shift

Start: 22:00
End:   06:00 next day
```

Attendance:

```text
22:05 IN
05:58 OUT
```

must be treated as one working session.

Do not assume:

```text
end_time > start_time
```

because overnight shifts may have:

```text
start_time > end_time
```

The attendance engine must correctly determine the attendance/work date for overnight shifts.

---

## 30.8 Shift-Based Attendance Processing

Attendance V2 processing should use the employee's applicable shift when calculating:

* Expected start time
* Expected end time
* Late arrival
* Early departure
* Grace period
* Expected working hours
* Break duration
* Overtime
* Attendance status

Example:

```text
Shift:

Start      09:00
End        18:00
Grace      15 minutes
```

Employee:

```text
IN   09:10
OUT  18:05
```

Result should be determined by the configured shift rules rather than hardcoded logic.

---

## 30.9 Late Arrival

The system should determine late arrival based on:

```text
Actual IN
vs
Shift Start + Grace Period
```

Example:

```text
Shift Start: 09:00
Grace:       15 minutes

Actual IN:   09:12
Result:      On Time

Actual IN:   09:18
Result:      Late
```

Do not implement these values as constants.

---

## 30.10 Early Departure

Similarly:

```text
Actual OUT
vs
Shift End
```

should be used to determine early departure according to configured rules.

Example:

```text
Shift End: 18:00

OUT 17:55
    → Early departure

OUT 18:05
    → Not early
```

The exact treatment should be configurable.

---

## 30.11 Overtime

The shift module should provide the expected working schedule required for overtime calculation.

Example:

```text
Shift End: 18:00

OUT: 18:45

Potential overtime:
45 minutes
```

Do not automatically assume that all time after shift end is overtime.

Support configurable overtime rules such as:

```text
Overtime Enabled: Yes
Minimum Overtime: 30 minutes
```

If the existing application has payroll or HR rules, inspect and integrate with those rules rather than duplicating them.

---

## 30.12 Breaks

The shift configuration should support break information.

Example:

```text
Shift: General

Start: 09:00
End: 18:00

Break:
12:30 - 13:30
```

If the application requires actual break tracking, support it through attendance events/sessions.

Do not assume that every company uses the same break duration.

---

## 30.13 Shift Calendar / Roster

Consider a company/employee shift calendar so administrators can see which shift applies on each date.

Example:

```text
Employee: EMP001

Date         Shift
--------------------------------
28-Sep-2026  Morning
29-Sep-2026  Morning
30-Sep-2026  Morning
01-Oct-2026  Night
02-Oct-2026  Night
03-Oct-2026  OFF
04-Oct-2026  OFF
```

This should allow future expansion into a proper employee roster system if required.

Do not build a complex roster system unless it is required by the existing business requirements.

---

## 30.14 Holidays and Days Off

Inspect whether the current application already has:

* Holiday models
* Leave management
* Weekly off configuration
* Company calendars

If these exist, reuse them.

Attendance processing should be capable of distinguishing:

```text
Working Day
Weekly Off
Holiday
Leave
Absent
```

Do not duplicate existing HR functionality unnecessarily.

---

## 30.15 Shift Change

Administrators should be able to change an employee's shift.

Example:

```text
Employee: EMP001

Current:
General Shift

Effective From:
01-Oct-2026

New:
Night Shift
```

The system must preserve the previous assignment for historical attendance.

Do not overwrite historical assignments.

---

## 30.16 Shift Management Frontend

Add a Shift Management section under Attendance V2 / HR.

Possible structure:

```text
Attendance V2
|
+-- Dashboard
+-- Attendance
+-- Daily Attendance
+-- Sessions
|
+-- Shift Management
|     |
|     +-- Shifts
|     +-- Shift Schedule
|     +-- Employee Assignments
|     +-- Shift Calendar
|
+-- Locations
+-- Devices
+-- Collectors
+-- Raw Punches
+-- Sync Logs
+-- Corrections
+-- Settings
```

Follow the existing Angular application's:

* UI components
* Styling
* Forms
* Tables
* Modals
* Alerts
* Validation
* Permissions
* Loading states
* Error handling

Do not introduce a completely different UI pattern.

---

## 30.17 Shift APIs

Create APIs under the Attendance V2 namespace where appropriate.

For example:

```text
/api/attendance/v2/shifts/
/api/attendance/v2/shifts/{id}/
/api/attendance/v2/shift-schedules/
/api/attendance/v2/employee-shifts/
/api/attendance/v2/shift-calendar/
```

Inspect existing API conventions before finalizing endpoint names.

Support appropriate:

```text
GET
POST
PUT/PATCH
DELETE
```

according to the application's existing API design.

---

## 30.18 Shift and Attendance Architecture

The final architecture should be:

```text
Biometric Device
       |
       v
External Collector
       |
       | Standard Punch API
       v
Attendance V2
       |
       v
Raw Punch
       |
       v
Attendance Event
       |
       +--------------------+
       |                    |
       v                    v
Employee              Shift Management
       |                    |
       +---------+----------+
                 |
                 v
        Attendance Processing
                 |
        +--------+---------+
        |        |         |
        v        v         v
     Sessions  Daily     Overtime
               Status
```

The important principle is:

```text
DEVICE
   ↓
COLLECTOR
   ↓
STANDARD ATTENDANCE EVENT
   ↓
SHIFT + COMPANY RULES
   ↓
ATTENDANCE PROCESSING
```

The collector must never contain shift-specific logic.

For example, do NOT implement:

```python
if employee == "EMP001":
    shift = "09:00-18:00"
```

or:

```python
if company == "ABC":
    grace_period = 15
```

All such rules belong to the central application.

---

## 30.19 Multi-Company Shift Isolation

Because Attendance V2 supports multiple companies, every shift must belong to a company.

Example:

```text
Company A
    Morning Shift
    Night Shift

Company B
    General Shift
    Production Shift
```

Company A users must not be able to access or assign Company B shifts.

Validate company ownership on:

* Shift
* Shift schedule
* Employee assignment
* Attendance processing
* API requests
* Frontend permissions

Never trust a company ID supplied directly by the client.

---

## 30.20 Shift Audit

Important shift changes should be auditable.

For example:

```text
Employee: EMP001
Old Shift: General
New Shift: Night
Effective From: 01-Oct-2026
Changed By: Admin
Changed At: 28-Sep-2026 14:20
```

Reuse the existing audit logging mechanism if one exists.

Do not create a duplicate audit framework unnecessarily.

---

## 30.21 Important Implementation Rule

Before implementing Shift Management:

1. Inspect the existing Employee model.
2. Inspect the Company model.
3. Inspect Department/Team models if available.
4. Inspect existing Leave/Holiday models.
5. Inspect existing attendance rules.
6. Inspect existing payroll/working-hours logic if available.
7. Determine whether any existing shift functionality already exists.
8. Reuse suitable existing models rather than creating duplicates.

Then propose the final Shift Management model and relationships.

---

## 30.22 Testing Requirements

Test at minimum:

```text
Normal fixed shift
Multiple shifts
Employee-specific shift
Department shift
Company default shift
Shift change
Historical shift assignment
Overnight shift
Multiple IN/OUT
Missing OUT
Late arrival
Grace period
Early departure
Overtime
Break
Weekly off
Holiday
Leave
Multiple companies
Unauthorized company shift access
Shift API validation
```

Also test:

```text
Employee changes from Shift A to Shift B
```

and verify that historical attendance continues to use Shift A while new attendance uses Shift B.

---

## 30.23 Final Architecture Requirement

The final Attendance V2 architecture must remain:

```text
LEGACY ATTENDANCE
        |
        | Existing eSSL implementation
        | MUST CONTINUE WORKING
        |
        +--------------------------------+

ATTENDANCE V2
        |
        +-- Collector Management
        +-- Device Management
        +-- Location Management
        +-- Raw Punches
        +-- Attendance Events
        +-- Shift Management
        +-- Shift Assignments
        +-- Attendance Sessions
        +-- Daily Attendance
        +-- Corrections
        +-- Sync Monitoring
        +-- Audit
        |
        v
Device-Independent Attendance Engine
```

Do not modify the existing eSSL attendance implementation unnecessarily.

The new Shift Management module must become part of the central Attendance V2 business layer and must work independently of whether attendance originates from:

```text
eSSL
ZKTeco
Other biometric devices
Web Check-in
Mobile Check-in
API integrations
Manual attendance
```

The ultimate goal is that adding a new attendance device should require only a new external collector, while **Shift Management and all attendance business rules remain unchanged**.


