# API overview

Interactive docs: http://localhost:8000/docs. Every endpoint with examples: [reference.md](reference.md). Machine-readable contract: [../api-spec.yaml](../api-spec.yaml). Postman: [../postman/](../postman/).

Base URL: `http://localhost:8000/api/v1`

## Authentication

```bash
# 1. log in (form fields, not JSON); username is the email
curl -X POST "$BASE/auth/login" -d "username=user@example.com&password=User@12345&remember_me=false"
# -> {"access_token":"...","refresh_token":"...","token_type":"bearer","expires_in":900}

# 2. call the API
curl "$BASE/sensors" -H "Authorization: Bearer $ACCESS_TOKEN"

# 3. when the access token (15 min) expires, swap the refresh token for a new pair
curl -X POST "$BASE/auth/refresh" -H "Content-Type: application/json" -d '{"refresh_token":"..."}'
```

Refresh tokens are single-use: every refresh returns a new one. Presenting an old one again revokes all of that user's sessions.

## Roles

| Role | Access |
|---|---|
| admin | everything |
| user | own sensors, readings and reports |
| guest | read-only access to all sensors, the dashboard and reports |

A request that needs a higher role returns `403`. Someone else's sensor or report returns `404`.

## Conventions

| Topic | Rule |
|---|---|
| Versioning | `/api/v1` in the path; breaking changes will ship as `/api/v2`. Every response has `X-API-Version`. |
| Pagination | `?page=1&page_size=20` (max 100). Lists return `items`, `total`, `page`, `page_size`, `pages`. |
| Errors | `{"detail": "message"}`. Validation errors (422) return `detail` as a list with `loc` and `msg`. |
| Rate limits | 100 requests/min per user (per IP when not logged in); 10/min per IP for login, register and resend-verification. `429` + `Retry-After`. Headers `X-RateLimit-Limit` / `X-RateLimit-Remaining`. |
| Tracing | Send `X-Request-ID` (or one is generated); it is returned and logged. |
| Dates | ISO 8601 in UTC, e.g. `2026-11-14T10:00:00Z`. |
| Concurrency | `PUT`/`PATCH` on sensors accept `If-Unmodified-Since`; `409` if the sensor changed later. |
| Bulk | Bulk create is all-or-nothing; bulk delete is partial and lists failures in `errors`. |

## Typical flows

**Send readings from a device**
```bash
curl -X POST "$BASE/sensors/7/readings/bulk" -H "Authorization: Bearer $TOKEN" -H "Content-Type: application/json" \
  -d '{"items":[{"value":70.1},{"value":71.5,"recorded_at":"2026-11-14T10:00:00Z"}]}'
```

**Build and download a report**
```bash
ID=$(curl -s -X POST "$BASE/reports" -H "Authorization: Bearer $TOKEN" -H "Content-Type: application/json" \
  -d '{"name":"Weekly","format":"pdf","query_params":{"template":"summary","window_hours":168}}' | python -c "import sys,json;print(json.load(sys.stdin)['id'])")
curl "$BASE/reports/$ID" -H "Authorization: Bearer $TOKEN"                      # wait until "status": "ready"
curl -o weekly.pdf "$BASE/reports/$ID/download" -H "Authorization: Bearer $TOKEN"
```

**Chart data**
```bash
curl "$BASE/dashboard/timeseries?sensor_id=7&interval=hour" -H "Authorization: Bearer $TOKEN"
```
