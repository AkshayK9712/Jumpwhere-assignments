# IoT Monitor

A centralized system to monitor, control and analyze data from IoT sensors across factory locations:
a FastAPI REST API, a PostgreSQL database and a web app (plain HTML, CSS and JavaScript with D3 charts).

| | |
|---|---|
| **Backend** | FastAPI, SQLAlchemy 2, Alembic, JWT auth (OAuth2 password flow) |
| **Database** | PostgreSQL 16 (SQLite for quick local use) |
| **Web app** | ES modules, D3.js charts, no build step, served at `/ui/` |
| **Reports** | PDF (ReportLab) and CSV, one-off or scheduled |
| **Deployment** | Docker Compose |

## Quick start

### Option A: Docker (recommended)

```bash
cp .env.example .env
docker compose up --build                # API + PostgreSQL + MailHog (dev)
docker compose --profile demo up         # also sends fake live readings
```

### Option B: no Docker (SQLite)

```powershell
python -m venv .venv
.venv\Scripts\Activate.ps1                # Mac/Linux: source .venv/bin/activate
pip install -r requirements.txt
$env:DATABASE_URL="sqlite:///./dev.db"    # Mac/Linux: export DATABASE_URL=sqlite:///./dev.db
alembic upgrade head
python scripts/seed.py
uvicorn app.main:app --app-dir src --reload
python scripts/simulate.py                # optional, in a second terminal: live data for the dashboard
```
Without Docker, emails (such as the verification link) are printed in the terminal running uvicorn.

### Open it

| URL | What |
|---|---|
| http://localhost:8000/ui/ | **Web app** |
| http://localhost:8000/docs | Swagger UI (interactive API) |
| http://localhost:8000/health | Liveness check |
| http://localhost:8025 | MailHog inbox (Docker dev only) |

| Seeded account | Email | Password |
|---|---|---|
| Admin | admin@example.com | Admin@12345 |
| User | user@example.com | User@12345 |
| Guest (read-only) | guest@example.com | Guest@12345 |

## What it does

| Area | Features |
|---|---|
| **Accounts** | Sign-up with email verification, login with "remember me", token refresh and rotation, logout, profile |
| **Roles** | `admin` (everything), `user` (own sensors and reports), `guest` (read-only). Enforced by the API; the UI also hides what you cannot use |
| **Sensors** | CRUD with search, filters, sorting, pagination, bulk create/delete, overwrite protection (`If-Unmodified-Since`) |
| **Readings** | Single and bulk ingest, range queries |
| **Dashboard** | Counts, donut by category, line chart with min/max band and threshold lines, period presets and custom range, live polling every 5 s, CSV export |
| **Reports** | PDF/CSV, three templates (summary, detailed, alerts), scheduled daily/weekly/monthly with email notice, download, auto-expiry |
| **Admin** | User management, audit log, system config |
| **Platform** | OpenAPI contract, `/api/v1` versioning, rate limiting, request IDs, audit trail, security headers |

## Project layout

```
iot-monitor/
├── src/app/              API: api/v1 (routes), services (logic), models, schemas, core (config, security, middleware)
├── src/frontend/         web app: index.html, css/, js/ (api client, router, views, charts), vendor/ (optional offline D3)
├── db/migrations/        Alembic migrations
├── scripts/              seed.py, simulate.py, build_api_docs.py, build_postman.py
├── tests/                pytest suites, frontend/ (Node tests), performance/ (load test)
├── docs/                 srs.json, api-spec.yaml, er-diagram.md, schema.dbml, api/, postman/, guides
├── demo/                 demo script and screenshot list
├── Dockerfile, docker-compose.yml, docker-compose.override.yml
└── .env.example, .env.staging.example, .env.production.example
```

## Tests

```bash
pytest -v                       # API, services, migrations, reports, static checks of the web app
npm run test:frontend           # JavaScript unit tests (Node 20+, optional)
python tests/performance/load_test.py --users 10 --duration 20     # see tests/performance/README.md
```

## Documentation

| Document | For |
|---|---|
| [User manual](user-manual.md) | People using the web app |
| [Deployment guide](deployment.md) | Running it in Docker, staging and production |
| [API reference](api/reference.md) and [overview](api/README.md) | Developers integrating with the API |
| [Postman collection](postman/) | Trying every endpoint |
| [Architecture](architecture.md) | How the pieces fit |
| [QA checklist](qa-checklist.md) | Final verification before submitting |
| [SRS](srs.json), [OpenAPI spec](api-spec.yaml), [ER diagram](er-diagram.md) | Design documents |

## Development notes

- **Migrations:** `alembic revision --autogenerate -m "describe"` after changing a model; `test_migration_matches_models` fails if you forget.
- **Regenerate docs** after changing `docs/api-spec.yaml`: `python scripts/build_api_docs.py && python scripts/build_postman.py`.
- **Branching:** `main` (stable) <- `dev` <- `feature/*`.
- **Offline charts:** download `d3.min.js` (v7) to `src/frontend/vendor/d3.min.js`; the app tries that file before the CDN.

