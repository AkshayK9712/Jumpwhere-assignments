# IoT Monitor API

Centralized API to monitor, control, and analyze data from IoT sensors across factory locations.

**Stack:** FastAPI, PostgreSQL, Alembic, JWT auth, HTML/CSS/JS + D3.js, Docker.

## Quick start

```bash
cp .env.example .env
docker compose up --build
```

| URL | What |
|---|---|
| http://localhost:8000/docs | Swagger UI |
| http://localhost:8000/health | Liveness |
| http://localhost:8000/api/v1/health/db | DB check |
| http://localhost:8000/ui/ | Frontend |
| http://localhost:8025 | MailHog (test emails) |

## Run tests

```bash
pip install -r requirements.txt
pytest
```

## Branching

`main` (stable) <- `dev` <- `feature/*`

## Status

- [x] Day 1: skeleton, Docker, SRS draft
- [ ] Day 2: ER diagram, OpenAPI spec
