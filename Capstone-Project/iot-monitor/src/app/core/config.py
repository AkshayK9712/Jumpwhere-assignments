from functools import lru_cache
from pathlib import Path

from pydantic import model_validator
from pydantic_settings import BaseSettings, SettingsConfigDict

# Project root = .../iot-monitor (this file is src/app/core/config.py)
ROOT_DIR = Path(__file__).resolve().parents[3]


class Settings(BaseSettings):
    """All configuration comes from environment variables (see .env.example)."""

    DATABASE_URL: str = "postgresql+psycopg2://iot:iot@localhost:5432/iotdb"
    JWT_SECRET: str = "dev-only-secret"
    AUTH_PROVIDER_KEY: str = ""
    API_BASE_URL: str = "http://localhost:8000"
    CORS_ORIGINS: str = ""
    ENVIRONMENT: str = "development"  # development | staging | production
    LOG_LEVEL: str = "INFO"

    # Auth
    JWT_ALGORITHM: str = "HS256"
    ACCESS_TOKEN_EXPIRE_MINUTES: int = 15
    REFRESH_TOKEN_EXPIRE_DAYS: int = 7
    REFRESH_TOKEN_REMEMBER_DAYS: int = 30
    REQUIRE_EMAIL_VERIFICATION: bool = True   # Day 4: accounts start inactive until the email link is used
    VERIFY_TOKEN_EXPIRE_HOURS: int = 24

    # Email: console = print the email to the log (default, no setup needed)
    #        smtp    = send via SMTP_HOST:SMTP_PORT (MailHog in Docker)
    #        memory  = keep in a Python list (used by tests)
    EMAIL_BACKEND: str = "console"
    SMTP_HOST: str = "localhost"
    SMTP_PORT: int = 1025
    SMTP_USER: str = ""
    SMTP_PASSWORD: str = ""
    SMTP_USE_TLS: bool = False                 # STARTTLS; turn on for real mail servers
    EMAIL_FROM: str = "no-reply@iot-monitor.local"

    # Reports
    REPORTS_DIR: str = str(ROOT_DIR / "reports_output")   # generated PDF/CSV files are stored here
    REPORTS_RETENTION_DAYS: int = 30
    MAX_REPORT_READINGS: int = 200_000         # safety cap per report
    MAX_REPORT_SENSORS: int = 200

    # Background scheduler (scheduled reports, clean-up of expired reports)
    SCHEDULER_ENABLED: bool = True
    SCHEDULER_INTERVAL_SECONDS: int = 60

    # Rate limiting (in-memory, per process)
    RATE_LIMIT_ENABLED: bool = True
    RATE_LIMIT_DEFAULT_PER_MINUTE: int = 100   # per user (or per IP when not logged in)
    RATE_LIMIT_AUTH_PER_MINUTE: int = 10       # per IP on login / register / resend-verification

    # Seed data (python scripts/seed.py)
    ADMIN_EMAIL: str = "admin@example.com"
    ADMIN_PASSWORD: str = "Admin@12345"
    SEED_DEMO_DATA: bool = True

    model_config = SettingsConfigDict(env_file=ROOT_DIR / ".env", extra="ignore")

    @model_validator(mode="after")
    def _refuse_unsafe_production_settings(self):
        if self.ENVIRONMENT.lower() == "production":
            problems = []
            if len(self.JWT_SECRET) < 32 or self.JWT_SECRET in {"dev-only-secret", "change-me", "change-me-to-a-long-random-string"}:
                problems.append("JWT_SECRET must be a random string of at least 32 characters")
            if self.EMAIL_BACKEND == "memory":
                problems.append("EMAIL_BACKEND must not be 'memory'")
            if problems:
                raise ValueError("Unsafe production configuration: " + "; ".join(problems))
        return self

    @property
    def cors_origins_list(self) -> list[str]:
        return [o.strip() for o in self.CORS_ORIGINS.split(",") if o.strip()]


@lru_cache
def get_settings() -> Settings:
    return Settings()


settings = get_settings()
