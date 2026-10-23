# AssureX Claim Engine — REST API (Django Ninja)

This document describes the REST API that lives alongside the original FastAPI
application. Both applications share the same domain code (`src/`), the same
SQLite database (`database/assurex.db`), the same `uploads/` directory, the same
warranty policies and the same ML models.

- **Framework:** Django 5.2 + django-ninja 1.7
- **OpenAPI / Swagger UI:** `http://127.0.0.1:8011/api/docs`
- **OpenAPI schema:** `http://127.0.0.1:8011/api/openapi.json`
- **Base URL:** `http://127.0.0.1:8011/api/v1`
- **Authentication:** expiring signed bearer tokens (8 h default)

The legacy FastAPI application is untouched and remains runnable; the migration
is additive. See [Migration map](#migration-map) for the route-by-route mapping.

---

## 1. Architecture

```
backend/
  manage.py                  Django entry point
  assurex_api/               project settings, URLs, WSGI/ASGI
  restapi/
    api.py                   NinjaAPI instance + router registration
    deps.py                  bearer/session auth, RBAC, DB access
    schemas.py               Pydantic request models
    serializers.py           ORM -> JSON
    middleware.py            one SQLAlchemy session per request, DB bootstrap
    services/
      tokens.py              signed token issue/verify (itsdangerous)
      models.py              background model registry (XGBoost + GTM + fusion)
      claim_flow.py          claim intake / adjudication / CSV import
      storage.py             upload persistence
    routers/                 auth, products, warranties, documents,
                             repairs, claims, review, admin, system
tests_api/                   REST API test suite (isolated temp DB)
```

The Django ORM is deliberately **not** used. `restapi.middleware` opens one
SQLAlchemy session per request (`request.db`) against the legacy schema, so the
API reads and writes exactly the same rows as the FastAPI app. On the first
request the process runs the legacy `init_db()` (schema creation/migration +
seed users) — the same code the FastAPI lifespan hook runs.

---

## 2. Running

```powershell
# from the repository root
uv sync

# Django management server (recommended for local use)
uv run python backend/manage.py runserver 8011

# or any ASGI server
uv run uvicorn assurex_api.asgi:application --app-dir backend --port 8011
```

`run_api.bat` wraps the first command. `ASSUREX_API_PRELOAD_MODELS=0` disables
eager model loading (endpoints that need models return `503` until the models
are loaded).

On Windows the first TensorFlow/Keras import can take 60–120 s. The tabular
model becomes available first; `/api/v1/health` reports progress:

```json
{"status": "loading", "models_ready": false, "python_model_ready": true, "gtm_model_ready": false}
```

### Environment variables

| Variable | Default | Purpose |
| --- | --- | --- |
| `SECRET_KEY` | dev key | Token/session signing (set in production) |
| `ASSUREX_DEBUG` | `1` | Django debug |
| `ASSUREX_ALLOWED_HOSTS` | `*` | Comma-separated hosts |
| `ASSUREX_DB_PATH` | `database/assurex.db` | SQLite file |
| `ASSUREX_UPLOADS_DIR` | `uploads/` | Evidence + summary cards |
| `ASSUREX_API_TOKEN_TTL_SECONDS` | `28800` | Bearer token lifetime |
| `ASSUREX_MODEL_TIMEOUT_SECONDS` | `300` | Max wait for model load |
| `ASSUREX_API_PRELOAD_MODELS` | `1` | Load models on startup |

---

## 3. Authentication & RBAC

```powershell
$login = Invoke-RestMethod -Method Post http://127.0.0.1:8011/api/v1/auth/login `
  -ContentType 'application/json' `
  -Body '{"email":"customer@assurex.com","password":"customer123"}'

$headers = @{ Authorization = "Bearer $($login.access_token)" }
```

Every protected endpoint accepts `Authorization: Bearer <token>`. The login
also sets a Django signed-cookie session, which lets you use the Swagger UI
(`/api/docs` → **Authorize** is not required; just call login first). Tokens
are stateless and expire after the configured TTL; call
`POST /api/v1/auth/logout` to clear the browser session.

Roles (seeded): `customer`, `service_center`, `reviewer`, `admin`.
`admin` bypasses role checks. Self-registration only creates `customer` or
`service_center` accounts.

| Role | Capabilities |
| --- | --- |
| `customer` | Own products, documents, repairs, claims, reports |
| `service_center` | Same as customer (shared ownership model) |
| `reviewer` | All claims, reviewer queue, overrides, audit logs, monitoring |
| `admin` | Everything, policy editing, analytics, CSV export, settings |

---

## 4. Endpoint reference

### System (public)

| Method | Path | Description |
| --- | --- | --- |
| GET | `/api/` | Service metadata |
| GET | `/api/v1/health` | Liveness + model readiness |
| GET | `/api/v1/system/models` | Model readiness details (auth) |
| GET | `/api/v1/system/info` | Runtime info and counts (auth) |

### Auth

| Method | Path | Description |
| --- | --- | --- |
| POST | `/api/v1/auth/register` | Register (`customer`/`service_center`) → token |
| POST | `/api/v1/auth/login` | Email + password → token |
| POST | `/api/v1/auth/logout` | Clear session |
| GET | `/api/v1/auth/me` | Current user + counts |
| PATCH | `/api/v1/auth/me` | Update name/email/phone/address |
| POST | `/api/v1/auth/change-password` | Current + new password |

### Products & warranties

| Method | Path | Description |
| --- | --- | --- |
| GET | `/api/v1/products` | List (filters: `category`, `serial`, `warranty_status`, `page`, `per_page`) |
| POST | `/api/v1/products` | Register product |
| GET | `/api/v1/products/{product_id}` | Product + warranty + documents/repairs/claims |
| GET | `/api/v1/warranties` | Warranty cards (paginated) |
| GET | `/api/v1/warranties/{product_id}` | Warranty detail |
| GET | `/api/v1/alerts` | Warranty alerts (`tab=expiring\|grace\|expired\|all`) |
| POST | `/api/v1/alerts/{product_id}/dismiss` | Dismiss an alert |

### Evidence / documents

| Method | Path | Description |
| --- | --- | --- |
| GET | `/api/v1/documents` | Vault (filters: `file_type`, `product_id`, `claim_id`) |
| POST | `/api/v1/documents` | Multipart upload (`upload`, `file_type`, `product_id`) |
| GET | `/api/v1/documents/{doc_id}` | Metadata + OCR fields + duplicate matches |
| GET | `/api/v1/documents/{doc_id}/download` | Download stored file |
| GET | `/api/v1/documents/{doc_id}/file` | Alias of download |
| POST | `/api/v1/documents/{doc_id}/verify` | Save corrected OCR fields |
| POST | `/api/v1/documents/{doc_id}/replace` | Replace file and re-run OCR |
| DELETE | `/api/v1/documents/{doc_id}` | Delete file + row |

### Repairs

| Method | Path | Description |
| --- | --- | --- |
| GET | `/api/v1/repairs` | List (filter `product_id`) |
| POST | `/api/v1/repairs` | Log a repair |

### Claims

| Method | Path | Description |
| --- | --- | --- |
| GET | `/api/v1/claims` | List (filters: `claim_id`, `product_id`, `serial`, `category`, `status`, `date_from`, `date_to`) |
| POST | `/api/v1/claims/precheck` | Policy/document/contradiction readiness (no ML) |
| POST | `/api/v1/claims` | Multipart submission; `action_type=draft` or `submit` |
| POST | `/api/v1/claims/import-csv` | Bulk import (`upload` CSV) |
| GET | `/api/v1/claims/{claim_id}` | Claim + dossier + narrative + documents |
| GET | `/api/v1/claims/{claim_id}/dossier` | Alias of claim detail |
| GET | `/api/v1/claims/{claim_id}/summary-card` | Rendered 600×600 card (PNG) |
| POST | `/api/v1/claims/{claim_id}/documents/{doc_id}` | Attach existing vault document |
| GET | `/api/v1/claims/{claim_id}/report.pdf` | Adjudication PDF |
| GET | `/api/v1/claims/{claim_id}/report.md` | Markdown report |

`POST /api/v1/claims` accepts `multipart/form-data`:

```
product_id, product_name, product_category, brand, model_number, serial_number,
purchase_date, purchase_price, retailer, warranty_months, has_extended_warranty,
extended_warranty_provider, extended_warranty_contract_number,
extended_warranty_duration_months, fault_category, damage_type,
fault_occurrence_date, claim_submission_date, description,
previous_repairs_count, has_unauthorized_repairs, attach_doc_ids,
action_type (submit|draft), draft_id,
receipt_file, warranty_card_file, product_photo_file, serial_photo_file, damage_photo_file
```

Response (abridged):

```json
{
  "claim_id": "CLM-2026-0042",
  "status": "Manual Review",
  "final_decision": "Manual Review Required",
  "python_predicted_class": "Manual Review",
  "python_top_confidence": 0.96,
  "vision_predicted_class": "Manual Review",
  "vision_top_confidence": 1.0,
  "confidence_difference": 0.04,
  "consistency_status": "Strong Match",
  "dossier": {"comparison": {"...": "..."}, "final_decision": "..."},
  "summary_card_url": "/api/v1/claims/CLM-2026-0042/summary-card",
  "report_url": "/api/v1/claims/CLM-2026-0042/report.pdf"
}
```

### Reviewer

| Method | Path | Description |
| --- | --- | --- |
| GET | `/api/v1/review/queue` | Manual Review / Request More Info queue |
| GET | `/api/v1/review/stats` | Queue counters |
| POST | `/api/v1/review/{claim_id}/decision` | `{action, comments}` override |

### Administration

| Method | Path | Description |
| --- | --- | --- |
| GET | `/api/v1/admin/policies` | All category policies |
| GET | `/api/v1/admin/policies/{category}` | One policy |
| PUT | `/api/v1/admin/policies/{category}` | Replace policy JSON |
| GET | `/api/v1/admin/analytics` | Aggregates + monitoring flags |
| GET | `/api/v1/admin/monitoring` | Drift/duplicate/review-rate flags |
| GET | `/api/v1/admin/audit-logs` | Audit trail (filters `action`, `user_id`, `claim_id`) |
| GET | `/api/v1/admin/export/claims.csv` | CSV export |
| GET | `/api/v1/admin/settings` | Runtime settings |
| PUT | `/api/v1/admin/settings` | Update whitelisted settings |

Errors use Ninja's JSON shape: `{"detail": "..."}` with `400`, `401`, `403`,
`404`, `503` (models loading) or `500`.

---

## 5. Migration map (FastAPI → REST)

| Legacy FastAPI route | REST endpoint |
| --- | --- |
| `POST /login` | `POST /api/v1/auth/login` |
| `POST /register` | `POST /api/v1/auth/register` |
| `GET /logout` | `POST /api/v1/auth/logout` |
| `GET /profile` / `POST /profile/update` | `GET` / `PATCH /api/v1/auth/me` |
| `POST /profile/change-password` | `POST /api/v1/auth/change-password` |
| `GET /` (dashboard) | `GET /api/v1/claims` + `GET /api/v1/products` |
| `GET /products` | `GET /api/v1/products` |
| `POST /products/new` | `POST /api/v1/products` |
| `GET /warranties`, `GET /warranties/{id}` | `GET /api/v1/warranties[/{id}]` |
| `GET /alerts`, `POST /alerts/dismiss/{id}` | `GET /api/v1/alerts`, `POST /api/v1/alerts/{id}/dismiss` |
| `GET /documents` | `GET /api/v1/documents` |
| `POST /documents/upload` | `POST /api/v1/documents` |
| `GET /documents/{id}/verify` | `GET /api/v1/documents/{id}` |
| `POST /documents/{id}/verify` | `POST /api/v1/documents/{id}/verify` |
| `POST /documents/{id}/delete` | `DELETE /api/v1/documents/{id}` |
| `POST /documents/{id}/replace` | `POST /api/v1/documents/{id}/replace` |
| `GET /repairs`, `POST /repairs/new` | `GET` / `POST /api/v1/repairs` |
| `POST /claims/pre-check` | `POST /api/v1/claims/precheck` |
| `POST /claims/submit` | `POST /api/v1/claims` |
| `POST /claims/import-csv` | `POST /api/v1/claims/import-csv` |
| `GET /claims/view/{id}` | `GET /api/v1/claims/{id}` |
| `GET /claims/{id}/report/pdf` | `GET /api/v1/claims/{id}/report.pdf` |
| `GET /claims/{id}/report/download?format=md` | `GET /api/v1/claims/{id}/report.md` |
| `GET /claims/{id}/report/print` | Not migrated (HTML print view) |
| `GET /reviewer/queue` | `GET /api/v1/review/queue` |
| `POST /reviewer/override/{id}` | `POST /api/v1/review/{id}/decision` |
| `GET /audit-logs` | `GET /api/v1/admin/audit-logs` |
| `GET /admin/policies` / `POST /admin/policies/edit` | `GET` / `PUT /api/v1/admin/policies/{category}` |
| `GET /admin/export-csv` | `GET /api/v1/admin/export/claims.csv` |
| `GET /admin/analytics` | `GET /api/v1/admin/analytics` |
| `GET /health` | `GET /api/v1/health` |
| `GET /uploads/{filename}` | `GET /api/v1/documents/{id}/download`, `GET /api/v1/claims/{id}/summary-card` |

Behaviour preserved: the same `compute_derived_claim_features` → tabular
prediction → `render_claim_card` → GTM prediction → `DecisionFusionEngine`
pipeline; the same audit-log actions; the same SHA-256 duplicate detection;
the same policy validation; the same upload limits (10 MB, PDF/JPG/PNG).

Deliberately **not** migrated: HTML pages (`templates/`), the printable HTML
report, flash messages and the legacy static assets. They remain in the
FastAPI application on `master` and on this branch.

---

## 6. Tests

```powershell
uv run pytest tests_api -q     # REST API (isolated temp DB + uploads)
uv run pytest tests -q         # legacy FastAPI suite, unchanged
```

The API suite covers health/OpenAPI, login/registration/profile, product
creation, warranties/alerts, document upload + duplicate detection + download +
delete, claim submission through both ML models, drafting, pre-check, summary
card, PDF/Markdown reports, CSV import, reviewer override and admin/RBAC.

---

## 7. Production notes

- Run behind HTTPS: `SESSION_COOKIE_SECURE = True` and `ASSUREX_DEBUG=0`.
- Set a strong `SECRET_KEY`; tokens and sessions are signed with it.
- Use one worker per model instance (the registry loads models per process).
- Keep `database/assurex.db` and `uploads/` on a persistent volume, or point
  `ASSUREX_DB_PATH` / `ASSUREX_UPLOADS_DIR` elsewhere.
- CSRF: Ninja views are CSRF-exempt by design; the cookie session fallback is
  `SameSite=Lax`, so cross-site POSTs do not carry it. Bearer tokens are the
  recommended production mechanism.
