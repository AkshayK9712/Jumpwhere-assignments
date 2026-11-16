# Final QA checklist ("before you submit")

Tick each box after checking it yourself. Commands assume the project root.

| # | Requirement | How to verify | Done |
|---|---|---|---|
| 1 | All functional requirements implemented | `pytest -v` passes; every ID in `docs/srs.json` has code and tests under `implementation` | ☐ |
| 2 | Authentication and authorization end to end | In the web app: sign up, verify, log in as user, guest and admin; guest sees no edit buttons; `/ui/#/admin/users` as a user shows "Not allowed" | ☐ |
| 3 | Dashboard with real-time data | Run `python scripts/simulate.py`; open the dashboard on "Last hour"; the status line and chart update every 5 s | ☐ |
| 4 | Complete CRUD for all entities | Create, edit, delete a sensor in the UI; users via admin page; reports; config via `PUT /admin/config/{key}` (Swagger) | ☐ |
| 5 | API documentation with examples | Open `docs/api/reference.md`; `/docs` loads; Postman collection imports and "Log in" works | ☐ |
| 6 | Containerized and deployment-ready | `docker compose up --build`; `docker compose ps` shows `api` as healthy; follow `docs/deployment.md` for production | ☐ |
| 7 | Code documented with comments | Skim `src/app/services`, `src/frontend/js`: modules start with a purpose comment; non-obvious rules are explained | ☐ |
| 8 | Migrations and seed data | `alembic upgrade head` then `python scripts/seed.py` on an empty database; `pytest tests/test_migrations.py` | ☐ |
| 9 | Error handling and logging | Stop the database: API answers 503 on `/api/v1/health/db`; every response has `X-Request-ID`; check `activity_logs` in the audit page | ☐ |
| 10 | Bridge (frontend to API) integration | `npm run test:frontend`; in the browser, wait 15 minutes (or edit `ACCESS_TOKEN_EXPIRE_MINUTES=1`) and see requests keep working through refresh | ☐ |
| 11 | Mobile-responsive design verified | Browser dev tools, device toolbar: iPhone SE (375 px) and iPad (768 px). Menu collapses, tables become cards, charts shrink, no sideways scrolling | ☐ |

## Mobile spot-check (item 11)

For each page at 375 px wide: Login, Sign up, Dashboard, Sensors, Sensor form, Sensor page, Reports, Profile, Users, Audit log.
Look for: horizontal scrolling, overlapping text, buttons smaller than a fingertip, unreadable charts, dialogs wider than the screen.

## Deliverables

| Deliverable | Location |
|---|---|
| SRS | `docs/srs.json` |
| OpenAPI specification | `docs/api-spec.yaml` |
| Database schema and migrations | `db/migrations/` (+ `docs/er-diagram.md`) |
| Source code | `src/` |
| Docker configuration | `docker-compose.yml`, `Dockerfile` |
| Test suite | `tests/` |
| API documentation | `docs/api/` |
| User manual and README | `docs/user-manual.md`, `docs/README.md` |
| Deployment guide | `docs/deployment.md` |
| Demo video and screenshots | `demo/` (record following `demo/DEMO_SCRIPT.md`) |
| Postman collection | `docs/postman/` |
| Performance test results | `tests/performance/results/latest.md` (run `load_test.py`) |
