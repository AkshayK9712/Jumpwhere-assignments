# IoT Monitor API

Centralized API to monitor, control, and analyze data from IoT sensors across factory locations.

**Stack:** FastAPI, PostgreSQL (SQLite for quick local dev), Alembic, JWT auth, HTML/CSS/JS + D3.js, Docker.

## Quick start with Docker

```bash
cp .env.example .env
docker compose up --build
```
The API container runs migrations and seeds data automatically.

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

| URL | What |
|---|---|
| http://localhost:8000/docs | Swagger UI (use the Authorize button) |
| http://localhost:8000/api/v1/health/db | DB check |
| http://localhost:8000/ui/ | Frontend |
| http://localhost:8025 | MailHog (test emails, Docker only) |

## Seeded accounts

| Role | Email | Password |
|---|---|---|
| admin | admin@example.com | Admin@12345 |
| user | user@example.com | User@12345 |
| guest | guest@example.com | Guest@12345 |

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
- [ ] Day 4: email verification, RBAC, admin user management

## Design docs

| File | What |
|---|---|
| `docs/srs.json` | Requirements, permission matrix, traceability |
| `docs/er-diagram.md` | ER diagram (Mermaid) |
| `docs/schema.dbml` | Same schema for dbdiagram.io |
| `docs/api-spec.yaml` | OpenAPI 3 contract |
