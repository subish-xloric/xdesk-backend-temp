# Access Control Migration — Session Log

**Read this file first if you're picking this work back up in a new session.**

This documents an in-progress migration of xDesk (`pTracker`) from hardcoded,
per-employee Django-group role checks (`role_id in (1, 2, 3)` scattered through
the biz layer) to the company-scoped Module/Role/Capability system that already
existed in `pTracker/dataaccess/platform_access/` but was unused. It covers both
the Django backend and the Angular frontend (`xdesk-frontend`).

Nothing here has been committed to git — everything is uncommitted working-tree
changes in both repos. Check `git status` / `git diff` in each repo to see the
real, current diff; this file explains *why* those diffs look the way they do
and what's still outstanding. React Native was never available on the machine
this work was done on and has not been touched.

---

## 1. Why, and the model

**Goal:** each company can enable a different set of product modules
(Attendance, Leave, Payroll, ...), and what a signed-in user can do should
follow their company's role setup, not a hardcoded role id. The frontend must
never be the security boundary — the backend re-checks everything itself.

**Data model** (already existed in `platform_access`, this project wired it up):

```
Company ──< CompanyModule >── Module ──requires── Module
   │
   ├─< Role >── Capability          (per-company; a role bundles capabilities)
   └─< Membership (user, company, branch?, role, extra_capabilities, status)
```

- A **Module** (e.g. `leave`, `payroll`) is a sellable product area. A company
  only has access to a module if it has an enabled `CompanyModule` row.
- A **Capability** (e.g. `leave.approve`, `payroll.manage_ctc`) is an atomic
  permission. Capabilities are prefixed by the module they belong to.
- A **Role** is company-scoped and bundles capabilities.
- A **Membership** links one user to one company (optionally one branch) with
  one role, plus `extra_capabilities` for one-off per-user grants on top of
  the role.
- A user's **effective capability** = capability is on their role OR on
  `extra_capabilities`, AND the capability's module is enabled for the
  company, AND the membership is `active`.

**Key decisions made with the user (recorded, not to be re-litigated):**

1. **No legacy fallback.** A user with no active membership gets no access at
   all (fail-closed). This is a deliberate break from the old "if no
   membership, use the old role_id check" bridging idea.
2. **Company selection:** chosen once after login (auto-picked if the user has
   only one active company), with a switcher in the header. Not a per-page
   dropdown. The client sends the chosen company on every request via
   `X-Company-Id`; the backend re-verifies membership in that company on every
   request — the header is a request, never trusted on its own.
3. **Data-scope pattern:** most "team vs company-wide vs self" checks
   (`role_id in (1,2,3)` = everyone, `role_id == 4` = own team only) became a
   `<module>.view_all` / `<module>.view_team` capability pair, read via
   `data_scope(user_id, module)` → `'all'` / `'team'` / `None`.

---

## 2. Backend: what was built (in call order)

### Request-scoped company context — `pTracker/common/company_context.py`
Resolves which company a request acts for from the `X-Company-Id` header,
verifying the caller has an active membership there. No header + exactly one
company → auto-picked. No header + several companies → `400 company_required`.
Header naming a company the user isn't in → `403 company_forbidden`. Result is
held in a `ContextVar` for the life of the request (`set_active_company` /
`get_active_company` / `clear_active_company`), including a per-request memo
dict so repeated capability checks in a loop don't re-hit the DB.

### Module gate — `pTracker/common/module_gate_middleware.py`
Django middleware. For any view whose Python package maps to a product module
(`pTracker/common/module_registry.py`'s `PACKAGE_TO_MODULE`), it resolves the
company context and checks the module is enabled; 403s with `{"module": ...}`
if not. Packages not in the registry (`pTracker.api.user`, the platform
operator API, wiki, dj_rest_auth) are never module-blocked, but `user`-package
views still get the company context resolved (`is_context_only_view_class`) so
`has_capability()` works there too, without ever hard-blocking those endpoints.

### Capability check — `pTracker/common/company_authorization.py`
```python
has_capability(user_id, capability_code, company_id=None)
data_scope(user_id, module, company_id=None)   # -> SCOPE_ALL | SCOPE_TEAM | None
```
`company_id=None` uses the active request context (and only applies if that
context's user matches `user_id` — so you can't accidentally borrow another
user's active-company context). Passing `company_id` explicitly lets you check
*someone else's* capability in the same company (used e.g. in ticket
assignment, where you check the assignee's/reporter's scope, not just the
caller's).

### Legacy `Utility.is_permitted()` bridge — `pTracker/common/permission_map.py`
The old `Utility.is_permitted(user_id, 'can_process_payslip')` pattern (Django
group/user `Permission` objects, ~30 codenames used across the codebase) now
maps each codename to a capability and calls `has_capability()`. Unmapped
codenames are denied (fail-closed). This meant most of `finance`, `interview`,
`rewards` etc. picked up the new system "for free" once this landed — call
sites using `Utility.is_permitted(...)` didn't need to change at all.

### Login / access API
- `AccessBL.get_login_access(user_id)` (`pTracker/api/user/access_biz.py`) —
  added to every login response (all 5 login code paths: web login, web 2FA,
  mobile login, biometric login, v1 login). Returns `companies`,
  `active_company`, `company_selection_required`, `enabled_modules`, plus
  `master_accountant`/`manage_assessment_menu` legacy flags recomputed from
  capabilities.
- `GET /api/auth/me/access/` and `GET /v1/api/user/me/access/` (also mounted
  under `/v1/api/auth/me/access/`) — `AccessBL.get_access()`. Returns
  `company`, `companies`, `memberships`, `modules`, `capabilities` for
  whatever company `X-Company-Id` names.

### Migration 0010–0013: new capabilities
Each of these mirrors the same "view_all / view_team" split, added as new
`Capability` rows only (no schema change):

| Migration | Capabilities added |
|---|---|
| `0010_seed_view_scope_capabilities` | `leave.view_all`, `leave.view_team`, `attendance.view_all`, `attendance.view_team` |
| `0011_seed_timesheet_ticket_view_scope` | `timesheet.view_all`, `timesheet.view_team`, `ticket.view_team` (`ticket.view_all` already existed) |
| `0012_seed_interview_assessment_view_scope` | `interview.view_all`, `interview.view_team`, `assessment.view_team` (`assessment.view_all` already existed) |
| `0013_seed_rewards_view_scope` | `rewards.view_all`, `rewards.view_team` |

`asset.manage_categories` / `asset.manage_vendors` / `asset.manage_purchase_orders`
already existed from `0007` but had never been granted to any role until this
project — the raw role checks were the only thing enforcing access to that
module.

### Sample membership/role data — management command
`pTracker/dataaccess/platform_access/management/commands/create_memberships_from_groups.py`

This is the **single most important file to open next session.** It is
explicitly marked as a sample/placeholder mapping for the business to correct,
and contains three tables at the top:

- `GROUP_TO_ROLE` — legacy Django auth Group name → platform Role name, per
  company (`Company.short_name`).
- `UNGROUPED_ROLE` — fallback role for an employee in no Django group.
- `ROLE_CAPABILITIES` — platform Role name → list of capability patterns
  (`'module.*'` expands to every capability of that module, `'*'` is
  everything). **Every time a new capability is added to the catalog, roles
  using wildcards need this command re-run for real (not `--dry-run`) or they
  won't pick it up** — `role.capabilities.set(...)` is a point-in-time
  snapshot, not live. This bit us mid-session (Director showed no
  interview/assessment access until re-run).
- `EXTRA_CAPABILITIES_BY_USER_ID` — one-off per-user grants
  (`Membership.extra_capabilities`), carrying over specific hardcoded
  exceptions found in the old code (e.g. `role_id == 2 or user_id == 7` in
  `leave_biz.py`, "Added Ajith as per his request").

Usage: `python3 manage.py create_memberships_from_groups --dry-run` first,
then without `--dry-run` to apply. `--update-existing` also updates an
existing membership's role if the employee has exactly one membership in that
company and the mapped role differs. `--profile-company-is legacy` if
`user_profile.company_id` holds the old 2/3-style ids instead of the new
platform `Company.id`.

Current state after this session's runs (2026-09-23), Digital Mesh (company 4)
role capability counts: Director 60+, HR ~49, Manager ~29, Team Lead ~18,
Developer 2. EM Soft mirrors with CEO/HR Manager/Branch Manager/Account.

### Company modules currently enabled (dev DB)
- Digital Mesh (company 4): `employee, attendance, leave, project, ticket, timesheet`
- EM Soft (company 5): `employee, attendance, leave`

Neither has `payroll`, `rewards`, `interview`, `assessment`, `appraisal`,
`asset`, `onboarding`, `offboard`, `induction`, `wiki`, `resource` enabled —
those modules are correctly blocked company-wide right now regardless of
role. This is expected, not a bug (confirmed multiple times while verifying
this work — temporarily enabling a module inside a rolled-back test
transaction is how each module's conversion was actually checked).

### Every biz-layer module converted this session
All hardcoded `role_id` / `role_name` / `roleID` / `roleName` checks are gone
from `pTracker/api/` and replaced with `has_capability()` / `data_scope()`,
module by module, in this order:
`onboarding`, `offboard`, `induction`, `appraisal`, `leave` (incl.
`leave_bulk_load_biz.py`), employee-profile-edit spots in `user`, `leave` +
`attendance` (full pass, incl. `mapping_biz.py` per an explicit spec: HR/CEO
→ everyone, Team Lead → own team, employee → self only — this **dropped** an
old hardcoded exception hiding specific user ids/usernames from certain roles,
since the given spec didn't call for it), `timesheet`, `ticket` (incl.
`ticket_helper.py`, `ticket_biz_v1.py`, `ticket_report_biz.py`), `interview`
(`candidate_biz.py`, `interview_biz.py`, `career_opening_biz.py`,
`interview_score_card_biz.py`), `assessment`, `user` (the rest —
`user_management_bl.py`, `user_management_bl_v1.py`), `rewards`, `finance`
(`emp_ctc_biz.py`, `tax_biz.py`), `projects` (`project_biz.py`,
`project_biz_v2.py`, `views.py`), `resource`, and finally
`asset_management` (`vendor_biz.py`, `purchase_order_biz.py`,
`asset_category_biz.py` — missed on the first sweep because it uses
`roleID`/`roleName`, different capitalization, which the earlier greps didn't
catch) and one line in `appraisal_biz.py:574` that had been missed because it
passed `role_id` down into the **data-access layer**
(`AppraisalDA.get_all_my_appraisal_forms_by_appraisal_period`) instead of
checking it in the biz layer — fixed by changing that DA method to take a
`see_all: bool` instead of a role id.

**Deliberately left alone** (not access-control gates, informational only):
`pTracker/api/user/views.py`'s `role_id`/`role_name` fields in the login
response — these are legacy fields relayed to old clients, sitting alongside
the new `AccessBL().get_login_access()` snapshot, not used to decide access.

**Lower-confidence / flagged for business review, not verified against
anything:**
- `tax_biz.py`'s `get_or_create_chat` and
  `get_dropdown_params_for_initiate_assessment` — the old `role_id == 3`
  check had no equivalent `Utility.is_permitted(...)` call nearby to confirm
  the mapping against, so `payroll.manage_tax_claims` was chosen as the
  closest existing capability. Worth a second look from someone who knows the
  finance/tax module's intended role.
- The whole `ROLE_CAPABILITIES` sample mapping — every conversion that needed
  a *new* capability grant (e.g. adding `employee.manage` to Manager,
  `resource.manage_allocation` and `asset.*` to HR, `interview.view_all` to
  Manager) was chosen to **exactly preserve old behavior**, not because
  anyone confirmed that's the business's intended design going forward.

### Verification approach used throughout
No test suite exists in this repo. `pyodbc`/`libodbc.so.2` isn't installed in
this environment, so the real login/module endpoints were never hit directly —
instead, each conversion was checked by:
1. `python3 -m py_compile` on every touched file (and a full-tree sweep at the
   end of each session).
2. A script run via `PYTHONPATH=. python3 <script>.py` (not `manage.py shell`,
   because that also needs `pyodbc`) that stubs `sys.modules['pyodbc']`,
   calls `django.setup()`, and exercises the real biz-layer functions inside
   `django.db.transaction.atomic()` blocks that always end by raising to force
   a rollback — so nothing written during a verification run is kept. Company
   modules were sometimes temporarily enabled inside that same transaction to
   test a module's permission logic in isolation from the module gate.
3. Cycling one real test user through each role in a company (e.g. Director →
   Manager → Team Lead → Developer) and confirming the scope/capability
   classification and the actual function's behavior line up at each tier.

These verification scripts lived in the session's scratchpad directory
(`/tmp/claude-.../scratchpad/verify*.py`), which does **not** persist between
sessions — they're gone now. If you need to re-verify something, the pattern
above is exactly how to write a new one.

---

## 3. Frontend (Angular, `xdesk-frontend`) — now a real git repo

The frontend repo was **not** a git repo for most of this project; the user
ran `git init` + committed everything as "initial commit" partway through, so
all of this is now real, diffable git history there. Check `git log`/`git
diff` in that repo directly.

- **`src/app/common/services/access.service.ts`** + **`access-storage.ts`** —
  `AccessService` holds the signed-in user's companies, active company,
  modules and capabilities (backed by `localStorage` via `access-storage.ts`
  for cross-reload persistence; this is a UI convenience only, never a
  security boundary). `can()`, `canAny()`, `hasModule()`.
- **`src/app/common/guards/access.guard.ts`** — route guard reading
  `data: { module, capability }` off the route.
- **HTTP interceptor** (`common/interceptors/auth-interceptor.ts`) — sends
  `X-Company-Id` on every API call; on `company_required`/`company_forbidden`
  it clears the stored company and redirects to the picker; on a
  module-disabled 403 it refreshes the access snapshot.
- **Company picker** — `modules/auth/components/select-company/` + a header
  switcher in `containers/default-layout/`. Shown when
  `company_selection_required` comes back from login.
- **`app.routing.ts`** — every lazy-loaded feature module route now carries
  `data: { module: '<code>' }` and the layout route has `canActivateChild:
  [AccessGuard]`.
- **`_nav.ts`** — every menu item carries a `module` tag (menus for a
  disabled module are hidden); the old `AdminUserRoles`/`role_id`-based
  `if` blocks that built up `adminNavItems`/`hRNavItems`/etc. are now
  `this.access.can('<capability>')` / `canAny(...)` checks.
- **`common/utility/index.ts`** legacy helpers
  (`hasAdminPrivilege`, `hasHrPrivilege`, `isDeveloper`, `isOffboardingExclude`,
  `isManagerAbove`) — kept with their original names/signatures (so the ~100
  existing call sites didn't need to change) but now backed by
  `storedCan()`/`storedCanAny()` capability checks instead of `role_id`.
- Legacy login/2FA components — apply the login response's access snapshot,
  redirect to the picker when `company_selection_required`, reject login
  entirely (log back out) if the user has no active membership anywhere.

No changes were needed for timesheet, ticket, interview, or assessment on the
Angular side — the capability-based helpers above already covered them once
built.

---

## 4. Known gaps / what to do next

1. **`create_memberships_from_groups.py`'s sample mapping needs a real
   business review.** Every role name (`Manager`, `Team Lead`, `Branch
   Manager`, etc. — these were actually renamed once already by the user
   directly in the platform admin between sessions, and the mapping file was
   updated to match) and every capability grant in `ROLE_CAPABILITIES` is a
   guess aimed at preserving old behavior, not a confirmed design.
2. **Company modules** — only Digital Mesh and EM Soft exist in the dev DB,
   and both have a small module subset enabled (see §2). Enabling more
   modules (`enable_company_modules` management command) is what unblocks
   payroll/rewards/interview/assessment/etc. for real use/testing.
3. **`tax_biz.py`'s `payroll.manage_tax_claims` mapping** — flagged above,
   worth a second look.
4. **React Native app** — never located on this machine; nothing done there.
5. **No automated tests exist anywhere in this repo.** Everything above was
   verified by hand with throwaway scripts as described in §2. If this
   project continues, consider whether it's worth adding a real test suite
   around `has_capability`/`data_scope`/`company_context`, since they're now
   load-bearing for every module's security.
6. **A data-integrity issue was found and fixed by the user directly**
   (three `Membership` rows had `company_id` pointing to Digital Mesh but
   `role_id` pointing to an EM-Soft-only role, from `user_profile.company_id`
   being changed externally between sessions). Worth being alert to similar
   drift if `user_profile.company_id` gets edited again outside of this
   system.

---

## 5. Quick reference — key files

| File | What it is |
|---|---|
| `pTracker/common/company_context.py` | Resolves + verifies the active company per request |
| `pTracker/common/module_gate_middleware.py` | Blocks requests to a disabled module |
| `pTracker/common/module_registry.py` | Maps Python packages → module codes |
| `pTracker/common/company_authorization.py` | `has_capability()`, `data_scope()` |
| `pTracker/common/company_modules.py` | Enabled-module lookup + cache |
| `pTracker/common/permission_map.py` | Legacy `Utility.is_permitted()` codename → capability |
| `pTracker/api/user/access_biz.py` | Login access snapshot + `/me/access/` |
| `pTracker/dataaccess/platform_access/migrations/0010-0013_*.py` | New capability seeds |
| `pTracker/dataaccess/platform_access/management/commands/create_memberships_from_groups.py` | **The sample role/membership mapping — start here** |
| `pTracker/dataaccess/platform_access/management/commands/enable_company_modules.py` | Enable/disable modules for a company |
| `xdesk-frontend/src/app/common/services/access.service.ts` | Frontend access state |
| `xdesk-frontend/src/app/common/guards/access.guard.ts` | Route guard |
| `xdesk-frontend/src/app/_nav.ts` | Menu definitions with module/capability tags |

---

*Written 2026-09-23, end of the session that did this migration. If you're an*
*AI assistant picking this up: read this whole file before touching anything,*
*then check `git status`/`git diff` in both repos to see the actual current*
*diff, since this file describes intent and history, not a live diff.*
