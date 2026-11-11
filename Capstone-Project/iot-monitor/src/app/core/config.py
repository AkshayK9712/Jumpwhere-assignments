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
    # Day 3: False = new accounts are active immediately.
    # Day 4 switches this to True (account must be activated via email link).
    REQUIRE_EMAIL_VERIFICATION: bool = False

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
