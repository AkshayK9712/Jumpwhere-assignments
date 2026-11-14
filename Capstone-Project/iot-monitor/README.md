# IoT Monitor API

Centralized API to monitor, control, and analyze data from IoT sensors across factory locations.

**Stack:** FastAPI, PostgreSQL (SQLite for quick local dev), Alembic, JWT auth, HTML/CSS/JS + D3.js, Docker.

## Quick start with Docker

```bash
cp .env.example .env
docker compose up --build
```
The API container runs migrations and seeds data automatically. Verification emails appear in MailHog (http://localhost:8025).

## Quick start without Docker (SQLite)

```powershell
python -m venv .venv
.venv\Scripts\Activate.ps1
pip install -r requirements.txt
$env:DATABASE_URL="sqlite:///./dev.db"
alembic upgrade head
python scripts/seed.py
uvicorn app.main:app --app-dir src --reload
```
Without Docker, verification emails are **printed in the terminal** where uvicorn runs (look for `EMAIL (console backend)`).

| URL | What |
|---|---|
| http://localhost:8000/docs | Swagger UI (use the Authorize button) |
| http://localhost:8000/api/v1/health/db | DB check |
| http://localhost:8000/ui/ | Web app (log in, sensors, admin) |
| http://localhost:8025 | MailHog (Docker only) |

## Seeded accounts

| Role | Email | Password |
|---|---|---|
| admin | admin@example.com | Admin@12345 |
| user | user@example.com | User@12345 |
| guest | guest@example.com | Guest@12345 |

## What each role can do

| | admin | user | guest |
|---|---|---|---|
| Register / log in / verify email | yes | yes | yes |
| Edit own account and profile | yes | yes | read only |
| Sensors and readings | all | own only | all, read only |
| Manage users, audit log, system config | yes | no | no |

## API overview (all under `/api/v1`)

| Area | Endpoints |
|---|---|
| auth | `POST /auth/register`, `GET /auth/verify-email`, `POST /auth/resend-verification`, `POST /auth/login`, `POST /auth/refresh`, `POST /auth/logout` |
| users | `GET/PATCH /users/me`, `GET/PUT /users/me/profile`, `GET /users`, `GET/PATCH/DELETE /users/{id}` |
| sensors | `GET/POST /sensors`, `POST/DELETE /sensors/bulk`, `GET/PUT/PATCH/DELETE /sensors/{id}` |
| readings | `GET/POST /sensors/{id}/readings`, `POST /sensors/{id}/readings/bulk` |
| admin | `GET /admin/activity-logs`, `GET /admin/config`, `GET/PUT /admin/config/{key}` |

Lists accept `page` and `page_size` (max 100). Sensors also accept `status`, `category`, `priority`, `q` and `sort`.
Full contract: `docs/api-spec.yaml`.

## Versioning, rate limits, logging

- **Versioning:** the major version is in the path (`/api/v1`). Breaking changes will ship under `/api/v2` while v1 stays available. Every response has `X-API-Version`.
- **Rate limits:** 100 requests/min per user, 10/min per IP on login/register/resend-verification. Exceeding returns `429` + `Retry-After`.
- **Logging:** each request is logged with its `X-Request-ID`; sign-ups, logins, sensor changes and admin actions are stored in `activity_logs`.

## Web app (`/ui/`)

Plain HTML, CSS and JavaScript (ES modules): no build step. Open http://localhost:8000/ui/ after starting the server.

| Page | Who | Route |
|---|---|---|
| Log in / Sign up / Verify email | everyone | `#/login`, `#/register`, `#/verify` |
| Home (counts, recent sensors) | any logged-in user | `#/` |
| Sensor list (search, filters, sort, paging, bulk delete) | any logged-in user | `#/sensors` |
| Sensor detail + readings | any logged-in user | `#/sensors/:id` |
| Create / edit sensor | admin, user | `#/sensors/new`, `#/sensors/:id/edit` |
| My profile | any logged-in user (guests read-only) | `#/profile` |
| User management, audit log | admin | `#/admin/users`, `#/admin/logs` |

How the pieces fit (`src/frontend/js/`):

| File | Job |
|---|---|
| `api.js` | API client: adds the token, refreshes it on 401, retries temporary failures, turns errors into `ApiError` |
| `session.js` | Token storage ("remember me" = localStorage, otherwise sessionStorage) |
| `auth.js` | login, register, logout, verify, resend |
| `router.js`, `route-match.js` | `#/path` routing with login and role guards |
| `ui.js`, `components.js` | DOM helpers (no `innerHTML`), toasts, dialogs, forms, pager |
| `validators.js` | Client-side validation that mirrors the server rules |
| `views/*.js` | One file per page |

To add a page: create `views/my-page.js` exporting a function that returns an element, then add one line to the `routes` list in `main.js`.

Security notes: the UI sends a strict Content-Security-Policy (no inline scripts or styles, same-origin only), builds all DOM with text nodes, and the server re-checks every permission, so hiding a button is only a convenience.

## Tests

```bash
pytest -v                 # backend + static checks of the web app
npm run test:frontend     # JavaScript unit tests (needs Node 20 or newer; optional)
```

## Database migrations

```bash
alembic upgrade head                              # apply
alembic revision --autogenerate -m "describe"     # after changing a model
alembic downgrade -1                              # undo last
```

## Branching

`main` (stable) <- `dev` <- `feature/*`

## Status

- [x] Day 1: skeleton, Docker, SRS draft
- [x] Day 2: ER diagram, OpenAPI spec, models, SRS (M1)
- [x] Day 3: migrations, seed data, register/login/refresh/logout with JWT
- [x] Day 4: email verification, role-based access control, admin user management
- [x] Day 5: sensor and reading CRUD, validation, audit log, rate limiting (M2)
- [x] Day 6: frontend shell, login/register/verify pages, API client with token refresh and retry
- [x] Day 7: sensor list and forms, role-based routes, admin pages, responsive layout (M3)
- [ ] Day 8: dashboard with charts

## Design docs

| File | What |
|---|---|
| `docs/srs.json` | Requirements, permission matrix, traceability |
| `docs/er-diagram.md` | ER diagram (Mermaid) |
| `docs/schema.dbml` | Same schema for dbdiagram.io |
| `docs/api-spec.yaml` | OpenAPI 3 contract |
