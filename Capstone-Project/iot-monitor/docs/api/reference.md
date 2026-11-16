# IoT Monitor API: API reference

_Generated from `docs/api-spec.yaml` by `scripts/build_api_docs.py`. Do not edit by hand._

Examples assume:

```bash
BASE=http://localhost:8000/api/v1
TOKEN=$(curl -s -X POST "$BASE/auth/login" -d "username=user@example.com&password=User@12345" | python -c "import sys,json;print(json.load(sys.stdin)['access_token'])")
```

## Contents

- **health**: `GET /health`, `GET /health/db`
- **auth**: `POST /auth/register`, `GET /auth/verify-email`, `POST /auth/resend-verification`, `POST /auth/login`, `POST /auth/refresh`, `POST /auth/logout`
- **users**: `GET /users/me`, `PATCH /users/me`, `GET /users/me/profile`, `PUT /users/me/profile`, `GET /users`, `GET /users/{user_id}`, `PATCH /users/{user_id}`, `DELETE /users/{user_id}`
- **sensors**: `GET /sensors`, `POST /sensors`, `POST /sensors/bulk`, `DELETE /sensors/bulk`, `GET /sensors/{sensor_id}`, `PUT /sensors/{sensor_id}`, `PATCH /sensors/{sensor_id}`, `DELETE /sensors/{sensor_id}`
- **readings**: `GET /sensors/{sensor_id}/readings`, `POST /sensors/{sensor_id}/readings`, `POST /sensors/{sensor_id}/readings/bulk`
- **dashboard**: `GET /dashboard/summary`, `GET /dashboard/timeseries`
- **reports**: `GET /reports`, `POST /reports`, `GET /reports/{report_id}`, `DELETE /reports/{report_id}`, `GET /reports/{report_id}/download`
- **admin**: `GET /admin/activity-logs`, `GET /admin/config`, `GET /admin/config/{key}`, `PUT /admin/config/{key}`

## Health

### `GET /health`

**Liveness check** (operationId: `health`)

Authentication: none (public).

Example:

```bash
curl -X GET "$BASE/health"
```

Responses:

- `200`: Service is up
- `429`: Rate limit exceeded

### `GET /health/db`

**Database connectivity check** (operationId: `health_db`)

Authentication: none (public).

Example:

```bash
curl -X GET "$BASE/health/db"
```

Responses:

- `200`: DB reachable
- `503`: Database unavailable
- `429`: Rate limit exceeded

## Auth

### `POST /auth/register`

**Register a new account** (operationId: `register`)

Creates an inactive account with role `user` and sends an email verification link. Password must be at least 8 characters with upper, lower, digit and symbol.

Authentication: none (public).

Request body (`application/json`):

```json
{
  "email": "ann@example.com",
  "password": "Str0ng!Pass",
  "name": "Ann Lee"
}
```

Example:

```bash
curl -X POST "$BASE/auth/register" \
  -H "Content-Type: application/json" \
  -d '{"email": "ann@example.com", "password": "Str0ng!Pass", "name": "Ann Lee"}'
```

Responses:

- `201`: Account created; verification email sent
- `409`: Email already registered
- `422`: Validation error
- `429`: Rate limit exceeded

### `GET /auth/verify-email`

**Verify email address** (operationId: `verify_email`)

Authentication: none (public).

| Parameter | In | Required | Type | Notes |
|---|---|---|---|---|
| `token` | query | yes | string | Signed verification token |

Example:

```bash
curl -X GET "$BASE/auth/verify-email"
```

Responses:

- `200`: Account activated
- `400`: Invalid or expired token
- `422`: Validation error
- `429`: Rate limit exceeded

### `POST /auth/resend-verification`

**Resend verification email** (operationId: `resend_verification`)

Authentication: none (public).

Request body (`application/json`):

```json
{
  "email": "ann@example.com"
}
```

Example:

```bash
curl -X POST "$BASE/auth/resend-verification" \
  -H "Content-Type: application/json" \
  -d '{"email": "ann@example.com"}'
```

Responses:

- `200`: Email sent if the account exists and is unverified
- `422`: Validation error
- `429`: Rate limit exceeded

### `POST /auth/login`

**Log in and get tokens** (operationId: `login`)

OAuth2 password flow. `username` is the email. With `remember_me=true` the refresh token lasts 30 days instead of 7.

Authentication: none (public).

Request body (`application/x-www-form-urlencoded`):

```
username=user@example.com&password=User@12345&remember_me=false
```

Example:

```bash
curl -X POST "$BASE/auth/login" \
  -d "username=user@example.com&password=User@12345&remember_me=false"
```

Responses:

- `200`: Token pair
- `401`: Invalid credentials
- `403`: Email not verified or account disabled
- `422`: Validation error
- `429`: Rate limit exceeded

### `POST /auth/refresh`

**Exchange refresh token for a new token pair** (operationId: `refresh_token`)

Authentication: none (public).

Request body (`application/json`):

```json
{
  "refresh_token": "<refresh_token>"
}
```

Example:

```bash
curl -X POST "$BASE/auth/refresh" \
  -H "Content-Type: application/json" \
  -d '{"refresh_token": "<refresh_token>"}'
```

Responses:

- `200`: New token pair (old refresh token is rotated)
- `422`: Validation error
- `429`: Rate limit exceeded

### `POST /auth/logout`

**Log out (revoke refresh token)** (operationId: `logout`)

Allowed roles: admin, user, guest.

Authentication: Bearer token required.

Request body (`application/json`):

```json
{
  "refresh_token": "<refresh_token>"
}
```

Example:

```bash
curl -X POST "$BASE/auth/logout" \
  -H "Authorization: Bearer $TOKEN" \
  -H "Content-Type: application/json" \
  -d '{"refresh_token": "<refresh_token>"}'
```

Responses:

- `200`: Session closed
- `401`: Missing, invalid or expired token
- `422`: Validation error
- `429`: Rate limit exceeded

## Users

### `GET /users/me`

**Get my account** (operationId: `get_me`)

Allowed roles: admin, user, guest.

Authentication: Bearer token required.

Example:

```bash
curl -X GET "$BASE/users/me" \
  -H "Authorization: Bearer $TOKEN"
```

Responses:

- `200`: Current user
- `401`: Missing, invalid or expired token
- `429`: Rate limit exceeded

### `PATCH /users/me`

**Update my account** (operationId: `update_me`)

Allowed roles: admin, user.

Authentication: Bearer token required.

Request body (`application/json`):

```json
{
  "name": "Ann Lee"
}
```

Example:

```bash
curl -X PATCH "$BASE/users/me" \
  -H "Authorization: Bearer $TOKEN" \
  -H "Content-Type: application/json" \
  -d '{"name": "Ann Lee"}'
```

Responses:

- `200`: Updated user
- `401`: Missing, invalid or expired token
- `403`: Role not allowed to perform this action
- `422`: Validation error
- `429`: Rate limit exceeded

### `GET /users/me/profile`

**Get my profile** (operationId: `get_my_profile`)

Allowed roles: admin, user, guest.

Authentication: Bearer token required.

Example:

```bash
curl -X GET "$BASE/users/me/profile" \
  -H "Authorization: Bearer $TOKEN"
```

Responses:

- `200`: Profile
- `401`: Missing, invalid or expired token
- `429`: Rate limit exceeded

### `PUT /users/me/profile`

**Create or replace my profile** (operationId: `put_my_profile`)

Allowed roles: admin, user.

Authentication: Bearer token required.

Request body (`application/json`):

```json
{
  "bio": "Maintenance lead",
  "phone": "+91 98765 43210",
  "timezone": "Asia/Kolkata",
  "language": "en-IN",
  "preferences": {
    "theme": "dark"
  }
}
```

Example:

```bash
curl -X PUT "$BASE/users/me/profile" \
  -H "Authorization: Bearer $TOKEN" \
  -H "Content-Type: application/json" \
  -d '{"bio": "Maintenance lead", "phone": "+91 98765 43210", "timezone": "Asia/Kolkata", "language": "en-IN", "preferences": {"theme": "dark"}}'
```

Responses:

- `200`: Profile
- `401`: Missing, invalid or expired token
- `403`: Role not allowed to perform this action
- `422`: Validation error
- `429`: Rate limit exceeded

### `GET /users`

**List users** (operationId: `list_users`)

Allowed roles: admin.

Authentication: Bearer token required.

| Parameter | In | Required | Type | Notes |
|---|---|---|---|---|
| `page` | query | no | integer |  |
| `page_size` | query | no | integer |  |
| `role` | query | no | string (admin, user, guest) |  |
| `is_active` | query | no | boolean |  |
| `q` | query | no | string | Search name or email |

Example:

```bash
curl -X GET "$BASE/users" \
  -H "Authorization: Bearer $TOKEN"
```

Responses:

- `200`: Page of users
- `401`: Missing, invalid or expired token
- `403`: Role not allowed to perform this action
- `422`: Validation error
- `429`: Rate limit exceeded

### `GET /users/{user_id}`

**Get a user** (operationId: `get_user`)

Allowed roles: admin.

Authentication: Bearer token required.

| Parameter | In | Required | Type | Notes |
|---|---|---|---|---|
| `user_id` | path | yes | integer |  |

Example:

```bash
curl -X GET "$BASE/users/2" \
  -H "Authorization: Bearer $TOKEN"
```

Responses:

- `200`: User
- `404`: Resource not found
- `401`: Missing, invalid or expired token
- `403`: Role not allowed to perform this action
- `422`: Validation error
- `429`: Rate limit exceeded

### `PATCH /users/{user_id}`

**Update role / active state** (operationId: `admin_update_user`)

Allowed roles: admin.

Authentication: Bearer token required.

| Parameter | In | Required | Type | Notes |
|---|---|---|---|---|
| `user_id` | path | yes | integer |  |

Request body (`application/json`):

```json
{
  "role": "user",
  "is_active": true
}
```

Example:

```bash
curl -X PATCH "$BASE/users/2" \
  -H "Authorization: Bearer $TOKEN" \
  -H "Content-Type: application/json" \
  -d '{"role": "user", "is_active": true}'
```

Responses:

- `200`: Updated user
- `400`: Not allowed on your own account (role change, deactivation, deletion)
- `404`: Resource not found
- `401`: Missing, invalid or expired token
- `403`: Role not allowed to perform this action
- `422`: Validation error
- `429`: Rate limit exceeded

### `DELETE /users/{user_id}`

**Delete a user** (operationId: `delete_user`)

Allowed roles: admin.

Authentication: Bearer token required.

| Parameter | In | Required | Type | Notes |
|---|---|---|---|---|
| `user_id` | path | yes | integer |  |

Example:

```bash
curl -X DELETE "$BASE/users/2" \
  -H "Authorization: Bearer $TOKEN"
```

Responses:

- `204`: Deleted
- `400`: Not allowed on your own account (role change, deactivation, deletion)
- `404`: Resource not found
- `401`: Missing, invalid or expired token
- `403`: Role not allowed to perform this action
- `422`: Validation error
- `429`: Rate limit exceeded

## Sensors

### `GET /sensors`

**List sensors** (operationId: `list_sensors`)

Users see their own sensors; admins and guests see all. Allowed roles: admin, user, guest.

Authentication: Bearer token required.

| Parameter | In | Required | Type | Notes |
|---|---|---|---|---|
| `page` | query | no | integer |  |
| `page_size` | query | no | integer |  |
| `status` | query | no | string (active, inactive, faulty) |  |
| `category` | query | no | string (temperature, pressure, humidity, vibration, flow, other) |  |
| `priority` | query | no | string (low, medium, high, critical) |  |
| `q` | query | no | string | Search title/description |
| `sort` | query | no | string (title, -title, created_at, -created_at, priority, -priority) |  |

Example:

```bash
curl -X GET "$BASE/sensors" \
  -H "Authorization: Bearer $TOKEN"
```

Responses:

- `200`: Page of sensors
- `401`: Missing, invalid or expired token
- `422`: Validation error
- `429`: Rate limit exceeded

### `POST /sensors`

**Create a sensor** (operationId: `create_sensor`)

Allowed roles: admin, user.

Authentication: Bearer token required.

Request body (`application/json`):

```json
{
  "title": "Boiler Temperature",
  "description": "Main boiler outlet",
  "category": "temperature",
  "status": "active",
  "priority": "high",
  "metadata": {
    "factory": "Hyderabad Plant",
    "location": "Boiler Room",
    "unit": "°C",
    "thresholds": {
      "min": 60,
      "max": 90
    }
  }
}
```

Example:

```bash
curl -X POST "$BASE/sensors" \
  -H "Authorization: Bearer $TOKEN" \
  -H "Content-Type: application/json" \
  -d '{"title": "Boiler Temperature", "description": "Main boiler outlet", "category": "temperature", "status": "active", "priority": "high", "metadata": {"factory": "Hyderabad Plant", "location": "Boiler Room", "unit": "°C", "thresholds": {"min": 60, "max": 90}}}'
```

Responses:

- `201`: Created
- `401`: Missing, invalid or expired token
- `403`: Role not allowed to perform this action
- `422`: Validation error
- `429`: Rate limit exceeded

### `POST /sensors/bulk`

**Bulk create sensors** (operationId: `bulk_create_sensors`)

All-or-nothing: if any item is invalid the whole request fails with 422 and nothing is created. Allowed roles: admin, user.

Authentication: Bearer token required.

Request body (`application/json`):

```json
{
  "items": [
    {
      "title": "Pump A",
      "category": "pressure"
    },
    {
      "title": "Pump B",
      "category": "pressure"
    }
  ]
}
```

Example:

```bash
curl -X POST "$BASE/sensors/bulk" \
  -H "Authorization: Bearer $TOKEN" \
  -H "Content-Type: application/json" \
  -d '{"items": [{"title": "Pump A", "category": "pressure"}, {"title": "Pump B", "category": "pressure"}]}'
```

Responses:

- `201`: Result
- `401`: Missing, invalid or expired token
- `403`: Role not allowed to perform this action
- `422`: Validation error
- `429`: Rate limit exceeded

### `DELETE /sensors/bulk`

**Bulk delete sensors** (operationId: `bulk_delete_sensors`)

Partial: sensors that do not exist or are not yours are listed in `errors`; the rest are deleted. Allowed roles: admin, user.

Authentication: Bearer token required.

Request body (`application/json`):

```json
{
  "ids": [
    7,
    8
  ]
}
```

Example:

```bash
curl -X DELETE "$BASE/sensors/bulk" \
  -H "Authorization: Bearer $TOKEN" \
  -H "Content-Type: application/json" \
  -d '{"ids": [7, 8]}'
```

Responses:

- `200`: Result
- `401`: Missing, invalid or expired token
- `403`: Role not allowed to perform this action
- `422`: Validation error
- `429`: Rate limit exceeded

### `GET /sensors/{sensor_id}`

**Get a sensor** (operationId: `get_sensor`)

Allowed roles: admin, user, guest.

Authentication: Bearer token required.

| Parameter | In | Required | Type | Notes |
|---|---|---|---|---|
| `sensor_id` | path | yes | integer | Sensor ID |

Example:

```bash
curl -X GET "$BASE/sensors/1" \
  -H "Authorization: Bearer $TOKEN"
```

Responses:

- `200`: Sensor
- `404`: Resource not found
- `401`: Missing, invalid or expired token
- `422`: Validation error
- `429`: Rate limit exceeded

### `PUT /sensors/{sensor_id}`

**Replace a sensor** (operationId: `replace_sensor`)

Allowed roles: admin, user.

Authentication: Bearer token required.

| Parameter | In | Required | Type | Notes |
|---|---|---|---|---|
| `sensor_id` | path | yes | integer | Sensor ID |
| `If-Unmodified-Since` | header | no | string | Optimistic concurrency: reject with 409 if the sensor changed after this time. |

Request body (`application/json`):

```json
{
  "title": "Boiler Temperature",
  "category": "temperature",
  "status": "active",
  "priority": "high",
  "metadata": {
    "unit": "°C"
  }
}
```

Example:

```bash
curl -X PUT "$BASE/sensors/1" \
  -H "Authorization: Bearer $TOKEN" \
  -H "Content-Type: application/json" \
  -d '{"title": "Boiler Temperature", "category": "temperature", "status": "active", "priority": "high", "metadata": {"unit": "°C"}}'
```

Responses:

- `200`: Updated
- `404`: Resource not found
- `409`: Resource was modified by someone else
- `401`: Missing, invalid or expired token
- `403`: Role not allowed to perform this action
- `422`: Validation error
- `429`: Rate limit exceeded

### `PATCH /sensors/{sensor_id}`

**Partially update a sensor** (operationId: `update_sensor`)

Allowed roles: admin, user.

Authentication: Bearer token required.

| Parameter | In | Required | Type | Notes |
|---|---|---|---|---|
| `sensor_id` | path | yes | integer | Sensor ID |

Request body (`application/json`):

```json
{
  "status": "faulty"
}
```

Example:

```bash
curl -X PATCH "$BASE/sensors/1" \
  -H "Authorization: Bearer $TOKEN" \
  -H "Content-Type: application/json" \
  -d '{"status": "faulty"}'
```

Responses:

- `200`: Updated
- `404`: Resource not found
- `409`: Resource was modified by someone else
- `401`: Missing, invalid or expired token
- `403`: Role not allowed to perform this action
- `422`: Validation error
- `429`: Rate limit exceeded

### `DELETE /sensors/{sensor_id}`

**Delete a sensor** (operationId: `delete_sensor`)

Allowed roles: admin, user.

Authentication: Bearer token required.

| Parameter | In | Required | Type | Notes |
|---|---|---|---|---|
| `sensor_id` | path | yes | integer | Sensor ID |

Example:

```bash
curl -X DELETE "$BASE/sensors/1" \
  -H "Authorization: Bearer $TOKEN"
```

Responses:

- `204`: Deleted (with its readings)
- `404`: Resource not found
- `401`: Missing, invalid or expired token
- `403`: Role not allowed to perform this action
- `422`: Validation error
- `429`: Rate limit exceeded

## Readings

### `GET /sensors/{sensor_id}/readings`

**List readings of a sensor** (operationId: `list_readings`)

Allowed roles: admin, user, guest.

Authentication: Bearer token required.

| Parameter | In | Required | Type | Notes |
|---|---|---|---|---|
| `sensor_id` | path | yes | integer | Sensor ID |
| `from` | query | no | string |  |
| `to` | query | no | string |  |
| `limit` | query | no | integer |  |

Example:

```bash
curl -X GET "$BASE/sensors/1/readings" \
  -H "Authorization: Bearer $TOKEN"
```

Responses:

- `200`: Readings, newest first
- `404`: Resource not found
- `401`: Missing, invalid or expired token
- `422`: Validation error
- `429`: Rate limit exceeded

### `POST /sensors/{sensor_id}/readings`

**Add a reading** (operationId: `create_reading`)

Allowed roles: admin, user.

Authentication: Bearer token required.

| Parameter | In | Required | Type | Notes |
|---|---|---|---|---|
| `sensor_id` | path | yes | integer | Sensor ID |

Request body (`application/json`):

```json
{
  "value": 71.5
}
```

Example:

```bash
curl -X POST "$BASE/sensors/1/readings" \
  -H "Authorization: Bearer $TOKEN" \
  -H "Content-Type: application/json" \
  -d '{"value": 71.5}'
```

Responses:

- `201`: Created
- `404`: Resource not found
- `401`: Missing, invalid or expired token
- `403`: Role not allowed to perform this action
- `422`: Validation error
- `429`: Rate limit exceeded

### `POST /sensors/{sensor_id}/readings/bulk`

**Ingest many readings** (operationId: `bulk_create_readings`)

Allowed roles: admin, user.

Authentication: Bearer token required.

| Parameter | In | Required | Type | Notes |
|---|---|---|---|---|
| `sensor_id` | path | yes | integer | Sensor ID |

Request body (`application/json`):

```json
{
  "items": [
    {
      "value": 70.1
    },
    {
      "value": 71.5,
      "recorded_at": "2026-11-14T10:00:00Z"
    }
  ]
}
```

Example:

```bash
curl -X POST "$BASE/sensors/1/readings/bulk" \
  -H "Authorization: Bearer $TOKEN" \
  -H "Content-Type: application/json" \
  -d '{"items": [{"value": 70.1}, {"value": 71.5, "recorded_at": "2026-11-14T10:00:00Z"}]}'
```

Responses:

- `201`: Result
- `404`: Resource not found
- `401`: Missing, invalid or expired token
- `403`: Role not allowed to perform this action
- `422`: Validation error
- `429`: Rate limit exceeded

## Dashboard

### `GET /dashboard/summary`

**Key metrics** (operationId: `dashboard_summary`)

Designed for polling every 5 seconds. Allowed roles: admin, user, guest.

Authentication: Bearer token required.

| Parameter | In | Required | Type | Notes |
|---|---|---|---|---|
| `category` | query | no | string (temperature, pressure, humidity, vibration, flow, other) |  |
| `from` | query | no | string |  |
| `to` | query | no | string |  |

Example:

```bash
curl -X GET "$BASE/dashboard/summary" \
  -H "Authorization: Bearer $TOKEN"
```

Responses:

- `200`: Summary
- `401`: Missing, invalid or expired token
- `422`: Validation error
- `429`: Rate limit exceeded

### `GET /dashboard/timeseries`

**Aggregated readings for charts** (operationId: `dashboard_timeseries`)

Allowed roles: admin, user, guest.

Authentication: Bearer token required.

| Parameter | In | Required | Type | Notes |
|---|---|---|---|---|
| `sensor_id` | query | yes | integer |  |
| `from` | query | no | string |  |
| `to` | query | no | string |  |
| `interval` | query | no | string (minute, hour, day) |  |

Example:

```bash
curl -X GET "$BASE/dashboard/timeseries" \
  -H "Authorization: Bearer $TOKEN"
```

Responses:

- `200`: Series
- `404`: Resource not found
- `401`: Missing, invalid or expired token
- `422`: Validation error
- `429`: Rate limit exceeded

## Reports

### `GET /reports`

**List my reports** (operationId: `list_reports`)

Allowed roles: admin, user, guest.

Authentication: Bearer token required.

| Parameter | In | Required | Type | Notes |
|---|---|---|---|---|
| `page` | query | no | integer |  |
| `page_size` | query | no | integer |  |
| `scheduled` | query | no | boolean | true = schedule definitions, false = generated reports |

Example:

```bash
curl -X GET "$BASE/reports" \
  -H "Authorization: Bearer $TOKEN"
```

Responses:

- `200`: Page of reports
- `401`: Missing, invalid or expired token
- `422`: Validation error
- `429`: Rate limit exceeded

### `POST /reports`

**Generate or schedule a report** (operationId: `create_report`)

Allowed roles: admin, user.

Authentication: Bearer token required.

Request body (`application/json`):

```json
{
  "name": "Weekly plant report",
  "format": "pdf",
  "query_params": {
    "template": "summary",
    "category": "temperature",
    "window_hours": 168
  }
}
```

Example:

```bash
curl -X POST "$BASE/reports" \
  -H "Authorization: Bearer $TOKEN" \
  -H "Content-Type: application/json" \
  -d '{"name": "Weekly plant report", "format": "pdf", "query_params": {"template": "summary", "category": "temperature", "window_hours": 168}}'
```

Responses:

- `202`: Accepted; generation runs in background
- `401`: Missing, invalid or expired token
- `403`: Role not allowed to perform this action
- `422`: Validation error
- `429`: Rate limit exceeded

### `GET /reports/{report_id}`

**Get report metadata** (operationId: `get_report`)

Allowed roles: admin, user, guest.

Authentication: Bearer token required.

| Parameter | In | Required | Type | Notes |
|---|---|---|---|---|
| `report_id` | path | yes | integer |  |

Example:

```bash
curl -X GET "$BASE/reports/1" \
  -H "Authorization: Bearer $TOKEN"
```

Responses:

- `200`: Report
- `404`: Resource not found
- `401`: Missing, invalid or expired token
- `422`: Validation error
- `429`: Rate limit exceeded

### `DELETE /reports/{report_id}`

**Delete a report** (operationId: `delete_report`)

Allowed roles: admin, user.

Authentication: Bearer token required.

| Parameter | In | Required | Type | Notes |
|---|---|---|---|---|
| `report_id` | path | yes | integer |  |

Example:

```bash
curl -X DELETE "$BASE/reports/1" \
  -H "Authorization: Bearer $TOKEN"
```

Responses:

- `204`: Deleted
- `404`: Resource not found
- `401`: Missing, invalid or expired token
- `403`: Role not allowed to perform this action
- `422`: Validation error
- `429`: Rate limit exceeded

### `GET /reports/{report_id}/download`

**Download the report file** (operationId: `download_report`)

Allowed roles: admin, user, guest.

Authentication: Bearer token required.

| Parameter | In | Required | Type | Notes |
|---|---|---|---|---|
| `report_id` | path | yes | integer |  |

Example:

```bash
curl -X GET "$BASE/reports/1/download" \
  -H "Authorization: Bearer $TOKEN"
```

Responses:

- `200`: PDF or CSV file
- `404`: Resource not found
- `409`: Report not ready yet
- `401`: Missing, invalid or expired token
- `422`: Validation error
- `429`: Rate limit exceeded

## Admin

### `GET /admin/activity-logs`

**Query the audit trail** (operationId: `list_activity_logs`)

Allowed roles: admin.

Authentication: Bearer token required.

| Parameter | In | Required | Type | Notes |
|---|---|---|---|---|
| `page` | query | no | integer |  |
| `page_size` | query | no | integer |  |
| `user_id` | query | no | integer |  |
| `action` | query | no | string |  |
| `entity_type` | query | no | string |  |
| `from` | query | no | string |  |
| `to` | query | no | string |  |

Example:

```bash
curl -X GET "$BASE/admin/activity-logs" \
  -H "Authorization: Bearer $TOKEN"
```

Responses:

- `200`: Page of logs
- `401`: Missing, invalid or expired token
- `403`: Role not allowed to perform this action
- `422`: Validation error
- `429`: Rate limit exceeded

### `GET /admin/config`

**List system configuration** (operationId: `list_config`)

Allowed roles: admin.

Authentication: Bearer token required.

Example:

```bash
curl -X GET "$BASE/admin/config" \
  -H "Authorization: Bearer $TOKEN"
```

Responses:

- `200`: All config entries
- `401`: Missing, invalid or expired token
- `403`: Role not allowed to perform this action
- `429`: Rate limit exceeded

### `GET /admin/config/{key}`

**Get one config entry** (operationId: `get_config`)

Allowed roles: admin.

Authentication: Bearer token required.

| Parameter | In | Required | Type | Notes |
|---|---|---|---|---|
| `key` | path | yes | string |  |

Example:

```bash
curl -X GET "$BASE/admin/config/dashboard.poll_interval_seconds" \
  -H "Authorization: Bearer $TOKEN"
```

Responses:

- `200`: Entry
- `404`: Resource not found
- `401`: Missing, invalid or expired token
- `403`: Role not allowed to perform this action
- `422`: Validation error
- `429`: Rate limit exceeded

### `PUT /admin/config/{key}`

**Create or update a config entry** (operationId: `put_config`)

Allowed roles: admin.

Authentication: Bearer token required.

| Parameter | In | Required | Type | Notes |
|---|---|---|---|---|
| `key` | path | yes | string |  |

Request body (`application/json`):

```json
{
  "value": 5,
  "description": "Dashboard refresh interval in seconds",
  "is_active": true
}
```

Example:

```bash
curl -X PUT "$BASE/admin/config/dashboard.poll_interval_seconds" \
  -H "Authorization: Bearer $TOKEN" \
  -H "Content-Type: application/json" \
  -d '{"value": 5, "description": "Dashboard refresh interval in seconds", "is_active": true}'
```

Responses:

- `200`: Entry
- `401`: Missing, invalid or expired token
- `403`: Role not allowed to perform this action
- `422`: Validation error
- `429`: Rate limit exceeded

