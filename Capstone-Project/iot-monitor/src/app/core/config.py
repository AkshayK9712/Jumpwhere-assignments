from functools import lru_cache
from pathlib import Path

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
    EMAIL_FROM: str = "no-reply@iot-monitor.local"

    # Rate limiting (in-memory, per process)
    RATE_LIMIT_ENABLED: bool = True
    RATE_LIMIT_DEFAULT_PER_MINUTE: int = 100   # per user (or per IP when not logged in)
    RATE_LIMIT_AUTH_PER_MINUTE: int = 10       # per IP on login / register / resend-verification

    # Seed data (python scripts/seed.py)
    ADMIN_EMAIL: str = "admin@example.com"
    ADMIN_PASSWORD: str = "Admin@12345"
    SEED_DEMO_DATA: bool = True

    model_config = SettingsConfigDict(env_file=ROOT_DIR / ".env", extra="ignore")

    @property
    def cors_origins_list(self) -> list[str]:
        return [o.strip() for o in self.CORS_ORIGINS.split(",") if o.strip()]


@lru_cache
def get_settings() -> Settings:
    return Settings()


settings = get_settings()
