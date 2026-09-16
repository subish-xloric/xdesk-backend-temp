# CLAUDE.md

This file provides guidance to Claude Code (claude.ai/code) when working with code in this repository.

## Project

xDesk (internal name `pTracker`) is a Python/Django REST backend for an internal HR/ops platform (attendance, leave, timesheet, projects, onboarding/offboarding, finance/payroll & tax, appraisal, assessment, recruitment, tickets, rewards, assets, wiki).

Primary stack:
- Python 3.13 / Django 5.2 / Django REST Framework
- MySQL (default DB) + MSSQL (`essl_db`, biometric device DB) — multi-database setup, see Architecture below
- Redis + Celery (background jobs, scheduled reports, notifications)
- JWT auth via `djangorestframework-simplejwt` + `dj-rest-auth`

## Commands

There is no Makefile, package.json, or CI config in this repo — everything runs through `manage.py` / Docker.

- Run dev server: `python manage.py runserver` (or `docker-compose up`, which serves on port 8009 and also starts Redis + a Celery worker on queue `mailSender`)
- Django shell: `python manage.py shell`
- Run a Celery worker manually: `celery -A pTracker worker -l info -Q mailSender`
- Tests: `python manage.py test` — **no test files currently exist in the repo**; there is nothing to run yet, and no pytest/tox/lint config is present.
- Linting/formatting: none configured (no flake8/black/ruff config found). Just follow PEP 8 manually.
- Migrations: `python manage.py makemigrations` / `migrate` exist as Django commands, but see the "Database" note below — almost all models are unmanaged, so these commands normally have nothing to do.

Settings module is fixed to `pTracker.settings`, and [pTracker/settings/__init__.py](pTracker/settings/__init__.py) unconditionally does `from .development import *`. The `production.py` and `qa.py` settings files exist but are **not** wired up by any env var switch in this repo — deployment-time selection of settings must happen outside what's checked in here (e.g. by editing that import or overriding `DJANGO_SETTINGS_MODULE`). Don't assume `ENVIRONMENT`-style env vars control this.

Config is loaded from a `.env` file at the repo root via `python-dotenv` (see [pTracker/settings/base.py](pTracker/settings/base.py)) — DB credentials, `SECRET_KEY`, `FERNET_KEY`, AWS keys, email account credentials, biometric device (`ATT_DEVICE`) serials/IPs, etc. all come from there. No `.env.example` is checked in.

## Architecture

**Layered structure, consistent across every feature module in `pTracker/api/<module>/`:**

1. `views.py` — thin DRF `APIView` classes. They set `authentication_classes`/`permission_classes` and immediately delegate to a business-logic class, e.g. `FinanceBL().manage_payslip(request, ...)`. Views should stay thin; put logic in the biz layer, not here.
2. `<module>_biz.py` (one or more per app, classes suffixed `BL`, e.g. `FinanceBL`, `TaxBL`, `TDSBL`) — business logic layer. Owns validation, orchestration, transactions, PDF/report generation, etc. Calls into the DA layer for persistence.
3. `pTracker/dataaccess/ptracker_access/<module>_da.py` (classes suffixed `DA`, e.g. `FinanaceDA`, `UserDA`) — data access layer. All ORM querying lives here; biz classes should not call `Model.objects` directly.
4. `pTracker/dataaccess/ptracker_access/<module>_models.py` — Django models, all defined with `managed = False` and an explicit `db_table`.

When adding a feature to an existing module, follow this same views → biz → da → models chain rather than querying the ORM from views or business logic directly.

**Database / migrations note:** virtually all models across `pTracker/dataaccess/ptracker_access/*_models.py` are `managed = False` mapping to pre-existing tables in an externally-managed MySQL schema — there are **no `migrations/` directories anywhere in the repo**. Model changes here describe an existing table, they don't create one; do not add fields/tables assuming `makemigrations`/`migrate` will apply them without confirming how schema changes are actually rolled out for this project.

**Multiple databases** are configured in `DATABASES` (see [pTracker/settings/development.py](pTracker/settings/development.py)): `default` (MySQL, main app DB), `essl_db` (MSSQL, biometric attendance devices — see `pTracker/dataaccess/essl_access/`), `hrms_dm_db` / `hrms_em_db` (MySQL, HRMS DM/EM instances — see `pTracker/dataaccess/hrms_access/`). Be deliberate about which DB a query needs to target (`.using(...)`), especially in the attendance/HRMS-related modules.

**Shared/common code:**
- `pTracker/common/` — cross-cutting utilities: `exception_handler.py` (the DRF `EXCEPTION_HANDLER`, plus an `ExceptionHandler` helper class used throughout the biz layer for capturing tracebacks), `logs.py` (`Logs`), `utility.py` (`Utility`), `file_manager.py` (`FileManager`), `permissions.py` (custom DRF permission classes, e.g. IP-restriction backed by `PermissionsDA`), `crypto_handler.py`, `api_token_auth.py`, `git_lab.py`.
- `pTracker/cronjobs/` — scheduled/report-generation scripts (attendance reports, weekly summaries, offboarding processing, email sending) invoked by Celery beat.
- `pTracker/notification_center/` — email (`email_engine.py`) and push notification (`push_notification_engine.py`, Firebase/FCM) senders used by the various `*_notification_biz.py` files.
- `pTracker/celery.py` / `celery_config.py` / `celery_imports.py` / `celery_routes.py` / `celery_beat.py` — Celery app wiring, task imports, routing, and the periodic schedule (`PRO_SCHEDULE`). Redis is the broker/result backend.
- `pTracker/wiki/` — a separate Django-templates-based site (internal wiki), mounted at `/wiki/`, distinct from the DRF API apps.
- Websocket support (`pTracker/consumers.py`, `pTracker/routing.py`, Django Channels) is present but currently **commented out / disabled**.

**URL structure** (`pTracker/urls.py`): most API modules are mounted twice — once under `/api/<module>/` (original) and again under `/v1/api/<module>/` via a separate `urls_v1.py` in the same app (some apps also have `urls_v2_mob.py` for a mobile client, currently commented out in the root urlconf). When editing endpoints, check whether both the legacy and `v1` urlconf/views need the change — modules like `attendance`, `timesheet`, `leave`, `user`, `projects` maintain parallel `*_v1`-suffixed biz/view functions rather than reusing the original ones, so don't assume the v1 route calls the same code path as the non-v1 route.

Auth: JWT (`djangorestframework-simplejwt`) is the primary API auth method (`AUTH_HEADER_TYPES = ('JWT',)`), alongside DRF `TokenAuthentication`. Most `APIView`s explicitly set `authentication_classes = [JSONWebTokenAuthentication]` (an alias for the simplejwt `JWTAuthentication`) and `permission_classes = [IsAuthenticated]` — follow this explicit-per-view pattern rather than relying only on the `DEFAULT_AUTHENTICATION_CLASSES` in settings.

## General Rules

- Before modifying code, understand the existing implementation.
- Do not rewrite working code unnecessarily.
- Follow the existing project architecture and coding patterns (see Architecture above).
- Prefer small, focused changes.
- Do not introduce new dependencies unless necessary.
- Do not change database schema unless explicitly requested — and note the `managed = False` / no-migrations setup above before touching models.
- Do not change API behavior unless explicitly requested.
- Do not remove existing functionality without confirmation.
- Never hard-code passwords, API keys, tokens, or secrets.
- Never expose sensitive information in logs or API responses.

## Code Style

- Follow PEP 8.
- Use meaningful variable and function names.
- Keep functions focused and reasonably small.
- Avoid duplicate code.
- Add type hints where they improve clarity.
- Follow the existing project naming conventions (`XxxBL` for business logic classes, `XxxDA` for data access classes).
- Reuse existing utilities/services (`pTracker/common/`) before creating new ones.

## Django

- Follow Django conventions.
- Keep business logic out of templates.
- Use Django ORM instead of raw SQL unless there is a specific reason.
- Validate user input.
- Use Django/DRF authentication and permission mechanisms.
- Do not bypass permission checks.
- Use transactions for operations that must be atomic.
- Avoid N+1 queries.
- Do not modify migrations manually unless required (and note: this repo has none — see Architecture).

## Database

- MySQL is the primary database (plus MSSQL for `essl_db`; see Architecture above for the multi-database layout).
- Check existing models in `pTracker/dataaccess/ptracker_access/*_models.py` before creating new tables/fields.
- Consider indexes for frequently searched/filtering fields.
- Never delete or rename database fields without checking their usage.

## Security

Always check for:
- SQL injection
- XSS
- CSRF
- IDOR/BOLA
- Authentication/authorization issues
- File upload vulnerabilities
- Path traversal
- Sensitive data exposure
- Hard-coded secrets
- Unsafe deserialization
- Improper permission checks

## Before Completing a Task

After making changes:

1. Review the modified files.
2. Check for obvious errors.
3. Run relevant tests (note: no test suite currently exists in this repo — say so explicitly rather than claiming tests passed).
4. Run linting/formatting if configured (none is, currently).
5. Check migrations if models were changed (see the no-migrations note above).
6. Summarize exactly what was changed.
7. Mention any tests that were not run.

## Important

Do not make unrelated changes.

If requirements are unclear or there are multiple possible architectural approaches, explain the options before making a large change.
