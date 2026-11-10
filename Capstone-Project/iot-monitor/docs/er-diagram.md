# ER Diagram

Render this file on GitHub / VS Code (Mermaid) or paste `schema.dbml` into https://dbdiagram.io.

```mermaid
erDiagram
    USERS ||--o| USER_PROFILES : "has (0..1)"
    USERS ||--o{ SENSORS : owns
    USERS ||--o{ ACTIVITY_LOGS : performs
    USERS ||--o{ REPORTS : generates
    USERS ||--o{ REFRESH_TOKENS : "has sessions"
    USERS ||--o{ SYSTEM_CONFIG : "updated_by"
    SENSORS ||--o{ SENSOR_READINGS : records

    USERS {
        int id PK
        string email UK
        string password_hash
        string name
        string role "admin|user|guest"
        bool is_active
        bool email_verified
        timestamptz created_at
        timestamptz updated_at
        timestamptz last_login
    }
    USER_PROFILES {
        int id PK
        int user_id FK,UK
        string avatar_url
        string bio
        string phone
        jsonb preferences
        string timezone
        string language
    }
    SENSORS {
        int id PK
        int user_id FK
        string title
        text description
        string status "active|inactive|faulty"
        string priority "low|medium|high|critical"
        string category "temperature|pressure|humidity|vibration|flow|other"
        jsonb metadata "factory, location, unit, thresholds"
        timestamptz created_at
        timestamptz updated_at
    }
    SENSOR_READINGS {
        bigint id PK
        int sensor_id FK
        float value
        timestamptz recorded_at "indexed with sensor_id"
    }
    ACTIVITY_LOGS {
        bigint id PK
        int user_id FK
        string action
        string entity_type
        int entity_id
        jsonb details
        string ip_address
        string user_agent
        timestamptz created_at
    }
    REPORTS {
        int id PK
        int user_id FK
        string name
        jsonb query_params
        string format "pdf|csv"
        string status "pending|ready|failed"
        bool scheduled
        string file_path
        timestamptz created_at
        timestamptz expires_at
    }
    SYSTEM_CONFIG {
        int id PK
        string key UK
        jsonb value
        string description
        bool is_active
        int updated_by FK
        timestamptz updated_at
    }
    REFRESH_TOKENS {
        int id PK
        int user_id FK
        string token_hash UK
        timestamptz expires_at
        bool revoked
        timestamptz created_at
    }
```

## Design notes

- `SENSORS` is the brief's **MainEntity**. `SENSOR_READINGS` and `REFRESH_TOKENS` are additions that the brief's 6 entities don't list, but the dashboard (time-series data) and logout (session revocation) need them.
- Deleting a user cascades to their profile, sensors (and readings), reports and refresh tokens. Activity logs and `system_config.updated_by` are set to NULL instead, so the audit trail survives.
- The composite index `(sensor_id, recorded_at)` serves the dashboard's "readings for sensor X between dates" queries.
