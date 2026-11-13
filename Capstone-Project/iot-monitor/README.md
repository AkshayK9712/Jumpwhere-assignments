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
| http://localhost:8000/ui/ | Frontend |
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

## Tests

```bash
pytest -v
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
- [ ] Day 6: frontend shell, API client

## Design docs

| File | What |
|---|---|
| `docs/srs.json` | Requirements, permission matrix, traceability |
| `docs/er-diagram.md` | ER diagram (Mermaid) |
| `docs/schema.dbml` | Same schema for dbdiagram.io |
| `docs/api-spec.yaml` | OpenAPI 3 contract |
