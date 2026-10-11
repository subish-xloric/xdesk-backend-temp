# Company confidential documents

Per-company file storage (company logo + confidential documents), added 2026-10-09.

## Storage layout

```
<COMPANY_DOCUMENT_STORAGE_ROOT>/<platform_company.uuid>/<category>/<32-hex>.<ext>
                                                        profile | documents | other
```

- Root: `COMPANY_DOCUMENT_STORAGE_ROOT` env var, default `CONFIDENTIAL_DOCS`
  (dev: `/x_desk_backend/dm-desk-docs/confidential_docs/`). Always the path *inside* the container.
- File names are generated server-side; the client's filename is kept only as
  `original_filename` (display). The DB stores the relative `storage_key`
  (`documents/<hex>.pdf`), never an absolute path.
- `pTracker/common/confidential_storage.py` builds every path from a parsed UUID
  plus a key matching a strict regex, refuses symlinked directories/files, checks the
  resolved path stays inside the company directory, writes to a temp file and
  hard-links it into place (no overwrite, no half-written files). Dirs 0750, files 0640.
- `pTracker/common/upload_validation.py` decides the type from file content
  (PNG/JPEG/WEBP verified with Pillow, PDF, DOCX/XLSX zip structure, UTF-8 TXT/CSV);
  the client Content-Type is ignored and the extension must match. SVG/HTML are not accepted.
- Limits: `COMPANY_DOCUMENT_MAX_UPLOAD_BYTES` (20 MB), `COMPANY_LOGO_MAX_UPLOAD_BYTES` (5 MB).

## Database (platform_access migrations 0016-0020)

| Migration | What |
|---|---|
| 0016 | `platform_company.uuid` added, nullable |
| 0017 | backfill a distinct uuid4 per existing company (ids/relations untouched) |
| 0018 | `uuid` NOT NULL + UNIQUE, default uuid4 for new companies, not editable |
| 0019 | `platform_company_document` (UUID pk, company FK, category, classification, storage_key UNIQUE, original_filename, content_type, size, sha256, description, uploaded_by FK, timestamps; index company+category+created_at) |
| 0020 | capabilities `company.view_documents`, `company.manage_documents` |

Apply with `python manage.py migrate platform_access` (never plain `migrate` on this DB).
Dev DB `ptracker_demo`: applied 2026-10-09. Roll back: `migrate platform_access 0015`.

## Authorization

Every request: JWT -> active company from the caller's verified membership
(`X-Company-Id` when they have several; `pTracker.api.company_documents` is a
context-only package in `module_registry.py`). The company UUID in the URL must equal
the active company's UUID or the answer is 404 (same as an unknown company).

| Action | Rule |
|---|---|
| Read `internal` documents, view logo | any active member |
| Read `confidential` documents (default) | `company.view_documents` (or manage) |
| Read `restricted` documents | `company.manage_documents` |
| Upload, delete documents; replace/delete logo | `company.manage_documents` |

Documents outside the caller's company or readable classifications are 404, not 403.
**Neither capability is granted to any role yet** - grant per company via
`PUT /api/platform/roles/<role_id>/capabilities/` (replaces the role's whole list:
send the existing codes plus the new one).

## Endpoints (`/api/companies/`)

| Method | Path | Body / result |
|---|---|---|
| GET | `<company_uuid>/documents/?category=documents` | `{"documents": [...]}` (readable ones only) |
| POST | `<company_uuid>/documents/` | multipart `file`, `category` (documents/other), `classification`, `description` -> 201 `{"document": {...}}` |
| GET | `<company_uuid>/documents/<document_id>/` | metadata |
| DELETE | `<company_uuid>/documents/<document_id>/` | removes row, file removed after commit |
| GET | `<company_uuid>/documents/<document_id>/content/` | file stream, always `attachment` |
| GET | `<company_uuid>/logo/` | image stream, `inline` |
| PUT | `<company_uuid>/logo/` | multipart `file` (png/jpg/webp) -> `{"logo": {...}}`, old logo file removed after commit |
| DELETE | `<company_uuid>/logo/` | |

The client gets the company UUID from `/api/auth/me/access/` (`company.uuid`), the
login payload (`companies[].uuid`, `active_company.uuid`) or the platform company API.

Example:

```
curl -H "Authorization: JWT <token>" -H "X-Company-Id: 4" \
     -F file=@agreement.pdf -F classification=confidential -F description="MSA 2026" \
     http://localhost:8009/api/companies/fbe2099f-aa5e-4616-89ac-5bc2049a3911/documents/

201 {"document": {"id": "8c6f...", "company_uuid": "fbe2099f-...", "category": "documents",
     "classification": "confidential", "original_filename": "agreement.pdf",
     "content_type": "application/pdf", "size": 48213, "sha256": "...", "description": "MSA 2026",
     "uploaded_by_id": 7, "created_at": "...", "updated_at": "...",
     "content_url": "/api/companies/fbe2099f-.../documents/8c6f.../content/"}}
```

File responses carry `X-Content-Type-Options: nosniff`, `Cache-Control: private, no-store`,
`Content-Security-Policy: default-src 'none'; sandbox` and an RFC 6266 `Content-Disposition`.

## AI / trusted processing

`CompanyDocumentBL().read_document_for_processing(user_id, company_uuid, document_id)` and
`extract_document_text(..., max_chars=20000)` (PDF/TXT/CSV; others return None) apply exactly
the download checks and raise `DocumentAccessDenied` otherwise. They must run inside a request
(or with `set_active_company` for that user). Not exposed over HTTP; there is no LLM integration
in this backend yet, so selecting only relevant passages, OCR and Office text extraction are
for that workflow to add. Never log the returned content.

## Docker / host

```yaml
services:
  xdeskbackend:
    volumes:
      - .:/x_desk_backend
      - /home/subish/Documents/pTracker/confidential_docs:/x_desk_backend/dm-desk-docs/confidential_docs
```

- The second line was mis-indented (folded into the first item), so the mount did not exist;
  fixed. Recreate the container to apply: `docker compose up -d --force-recreate xdeskbackend`.
- `dm-desk-docs/` is in `.gitignore` and `.dockerignore`. It is not under `STATICFILES_DIRS`
  or `MEDIA_ROOT`; never add it to Nginx.
- The image currently runs as **root** (no `USER` in the Dockerfile) - unchanged here.
  Files are created 0640, so on the host they are root-owned and unreadable by other users.
  To run unprivileged later: add a user with the host owner's uid (e.g. 1001), `chown` the
  host directory to it, `chmod 750` it, and set `user:` in compose.
- The celery service does not mount the directory; add the same volume if a task ever reads documents.

## Maintenance

`python manage.py cleanup_company_documents [--delete-orphans] [--partial-age 3600]` removes
stale partial uploads and reports files without rows / rows without files, per company.

## Tests

```
docker exec -e DJANGO_SETTINGS_MODULE=pTracker.settings.test x-desk-backend \
    python manage.py test pTracker.tests
```

`pTracker/settings/test.py` uses in-memory SQLite + the managed apps' migrations (the MySQL
user cannot create a test DB). 39 tests: storage/validation units and API tests through JWT +
company middleware (cross-company, URL tampering, guessed ids, classifications, traversal,
invalid/oversized uploads, missing files, delete/replace permissions, logo, AI accessor).
