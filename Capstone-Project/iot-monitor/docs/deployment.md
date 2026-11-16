# Deployment guide

## 1. Environments

| | Development | Staging | Production |
|---|---|---|---|
| Config file | `.env.example` | `.env.staging.example` | `.env.production.example` |
| Command | `docker compose up --build` | `docker compose -f docker-compose.yml up -d --build` | same as staging |
| Database | PostgreSQL in Docker (port 5432 open) | PostgreSQL in Docker (private) | PostgreSQL in Docker (private) or a managed service |
| Email | MailHog (http://localhost:8025) | real SMTP | real SMTP |
| Demo data | yes | optional | **no** |
| Hot reload | yes | no | no |

Plain `docker compose up` also loads `docker-compose.override.yml` (development extras). Naming the file with `-f docker-compose.yml` skips it.

## 2. Requirements

- A Linux server (or any machine) with Docker Engine 24+ and the Compose plugin
- 1 vCPU and 1 GB RAM minimum; 2 GB recommended
- A domain name and TLS certificate for production (Caddy below gets one automatically)

## 3. Deploy to a server

```bash
git clone <your-repo> iot-monitor && cd iot-monitor
cp .env.production.example .env
nano .env                         # replace every CHANGE value (see the table in section 6)
```

Generate secrets:
```bash
python3 -c "import secrets; print(secrets.token_urlsafe(48))"      # JWT_SECRET
python3 -c "import secrets; print(secrets.token_urlsafe(24))"      # database and admin passwords
```
Use the same database password in `POSTGRES_PASSWORD` and inside `DATABASE_URL`.

Create the first admin (once): in `.env` set `SEED_ON_START=true`, a strong `ADMIN_PASSWORD`, keep `SEED_DEMO_DATA=false`, then:

```bash
docker compose -f docker-compose.yml up -d --build
docker compose -f docker-compose.yml logs -f api        # wait for "Application startup complete"
```
Then set `SEED_ON_START=false` in `.env` and run `docker compose -f docker-compose.yml up -d` again, and change the admin password if you want a different one.

The container runs `alembic upgrade head` on every start, so upgrades apply migrations automatically.

Check it:
```bash
docker compose -f docker-compose.yml ps                  # api should say "healthy"
curl http://127.0.0.1:8000/health                        # {"status":"ok"}
curl http://127.0.0.1:8000/api/v1/health/db              # {"status":"ok","database":"connected"}
```

## 4. HTTPS with a reverse proxy

The API listens only on `127.0.0.1:8000`. Put a proxy in front. Example with [Caddy](https://caddyserver.com) (automatic certificates):

```
iot.example.com {
    reverse_proxy 127.0.0.1:8000
}
```
Set `API_BASE_URL` and `CORS_ORIGINS` in `.env` to `https://iot.example.com` (email links use `API_BASE_URL`).
If you use nginx, forward `Host`, `X-Forwarded-For` and `X-Forwarded-Proto` and allow request bodies up to 2 MB.

## 5. Operations

**Logs:** `docker compose -f docker-compose.yml logs -f api` (each line has a request id; users can quote the `X-Request-ID` header when reporting a problem).

**Backup (daily is sensible):**
```bash
docker compose -f docker-compose.yml exec -T db pg_dump -U iot iotdb | gzip > backup-$(date +%F).sql.gz
docker run --rm -v iot-monitor_reports:/data -v "$PWD":/backup alpine tar czf /backup/reports-$(date +%F).tgz -C /data .
```
(The volume name is `<folder name>_reports`; check with `docker volume ls`.) Reports can be regenerated, so the database backup matters most.

**Restore:**
```bash
gunzip -c backup-2026-11-14.sql.gz | docker compose -f docker-compose.yml exec -T db psql -U iot iotdb
```

**Update to a new version:**
```bash
git pull
docker compose -f docker-compose.yml up -d --build      # migrations run on start
```
Back up first. To undo a migration: `docker compose -f docker-compose.yml exec api alembic downgrade -1`.

**Rotate `JWT_SECRET`:** change it in `.env` and restart; everyone is signed out.

**Scheduler:** scheduled reports and cleanup of expired reports run inside the API process every `SCHEDULER_INTERVAL_SECONDS`. With `WEB_CONCURRENCY` above 1, each worker runs the loop, but schedules are claimed atomically, so no report is generated twice.

## 6. Settings reference

| Variable | Meaning | Default |
|---|---|---|
| `ENVIRONMENT` | `development`, `staging` or `production` (production refuses weak secrets) | development |
| `DATABASE_URL` | SQLAlchemy URL | local PostgreSQL |
| `JWT_SECRET` | Signing key, 32+ random characters in production | dev value |
| `ACCESS_TOKEN_EXPIRE_MINUTES` / `REFRESH_TOKEN_EXPIRE_DAYS` / `REFRESH_TOKEN_REMEMBER_DAYS` | Session lengths | 15 / 7 / 30 |
| `API_BASE_URL` | Public address, used in email links | http://localhost:8000 |
| `CORS_ORIGINS` | Comma-separated allowed browser origins (the bundled web app is same-origin and needs none) | empty |
| `REQUIRE_EMAIL_VERIFICATION` | Accounts start inactive until the email link is used | true |
| `EMAIL_BACKEND` | `console`, `smtp` or `memory` (tests) | console |
| `SMTP_HOST` `SMTP_PORT` `SMTP_USER` `SMTP_PASSWORD` `SMTP_USE_TLS` `EMAIL_FROM` | Mail server | localhost:1025 |
| `RATE_LIMIT_ENABLED` / `RATE_LIMIT_DEFAULT_PER_MINUTE` / `RATE_LIMIT_AUTH_PER_MINUTE` | Request limits | true / 100 / 10 |
| `REPORTS_DIR` / `REPORTS_RETENTION_DAYS` | Where report files go and how long they live | reports_output / 30 |
| `MAX_REPORT_READINGS` / `MAX_REPORT_SENSORS` | Safety caps per report | 200000 / 200 |
| `SCHEDULER_ENABLED` / `SCHEDULER_INTERVAL_SECONDS` | Background jobs | true / 60 |
| `ADMIN_EMAIL` / `ADMIN_PASSWORD` / `SEED_DEMO_DATA` / `SEED_ON_START` | First admin and demo data | see file |
| `WEB_CONCURRENCY` | Number of server worker processes | 1 |
| `POSTGRES_USER` `POSTGRES_PASSWORD` `POSTGRES_DB` | Database container credentials | iot / iot / iotdb |

## 7. Security checklist before going live

- [ ] `ENVIRONMENT=production`, random `JWT_SECRET`, random database and admin passwords
- [ ] `SEED_DEMO_DATA=false`; no `@example.com` demo accounts exist (check *Users* as admin)
- [ ] HTTPS in front; `API_BASE_URL` and `CORS_ORIGINS` use `https://`
- [ ] Port 5432 not exposed to the internet (it is not published by `docker-compose.yml`)
- [ ] Real SMTP configured and a test sign-up email arrives
- [ ] Firewall allows only 80/443 (and SSH)
- [ ] Backups scheduled and a restore tested
- [ ] `.env` is not in version control

## 8. Troubleshooting

| Symptom | Cause and fix |
|---|---|
| API exits immediately with "Unsafe production configuration" | `JWT_SECRET` is short or still a placeholder |
| `api` keeps restarting, logs show a database connection error | Password in `DATABASE_URL` differs from `POSTGRES_PASSWORD`; if the database volume already exists with an old password, run `docker compose down -v` (this deletes data) or change the password inside PostgreSQL |
| Verification emails never arrive | Check `EMAIL_BACKEND=smtp` and SMTP settings; look for "Could not send email" in the API log |
| Everyone gets `429` | Users behind one proxy share an IP for login limits; make sure the proxy forwards the client address, or raise `RATE_LIMIT_AUTH_PER_MINUTE` |
| Charts empty, banner says the chart library failed | The browser cannot reach cdnjs: download `d3.min.js` (v7) into `src/frontend/vendor/` and rebuild |
| Reports stay `pending` | Look for "Report N failed" in the logs; usually a too-large period (see `MAX_REPORT_READINGS`) |
| `port is already allocated` | Another program uses 8000 or 5432; change the left side of the port mapping |
