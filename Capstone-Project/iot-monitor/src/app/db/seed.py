"""Seed the database: admin account, demo users, demo sensors with readings, default config.

Run from the project root:   python scripts/seed.py
Safe to run many times: existing rows are left alone.
"""
import logging
import math
import random
from datetime import datetime, timedelta, timezone

from sqlalchemy import select
from sqlalchemy.orm import Session

from app.core.config import settings
from app.core.logging import setup_logging
from app.core.security import hash_password
from app.db.session import SessionLocal
from app.models import (
    Priority, Sensor, SensorCategory, SensorReading, SensorStatus,
    SystemConfig, User, UserProfile, UserRole,
)

logger = logging.getLogger(__name__)

DEMO_USER = ("user@example.com", "Demo User", "User@12345")
DEMO_GUEST = ("guest@example.com", "Demo Guest", "Guest@12345")

PLANT = "Hyderabad Plant"
DEMO_SENSORS = [
    dict(title="Boiler Temperature", category=SensorCategory.temperature, priority=Priority.high,
         status=SensorStatus.active, base=75, amp=5,
         meta={"factory": PLANT, "location": "Boiler Room", "unit": "°C", "thresholds": {"min": 60, "max": 90}}),
    dict(title="Cooling Line Pressure", category=SensorCategory.pressure, priority=Priority.medium,
         status=SensorStatus.active, base=4.2, amp=0.4,
         meta={"factory": PLANT, "location": "Cooling Loop A", "unit": "bar", "thresholds": {"min": 3, "max": 6}}),
    dict(title="Warehouse Humidity", category=SensorCategory.humidity, priority=Priority.low,
         status=SensorStatus.active, base=55, amp=8,
         meta={"factory": "Pune Plant", "location": "Warehouse 2", "unit": "%", "thresholds": {"min": 30, "max": 70}}),
    dict(title="Press Vibration", category=SensorCategory.vibration, priority=Priority.critical,
         status=SensorStatus.active, base=2.1, amp=0.6,
         meta={"factory": "Pune Plant", "location": "Press Line 1", "unit": "mm/s", "thresholds": {"max": 4.5}}),
    dict(title="Coolant Flow", category=SensorCategory.flow, priority=Priority.medium,
         status=SensorStatus.active, base=120, amp=10,
         meta={"factory": PLANT, "location": "Cooling Loop B", "unit": "L/min", "thresholds": {"min": 90}}),
    dict(title="Old Chiller Temperature", category=SensorCategory.temperature, priority=Priority.low,
         status=SensorStatus.faulty, base=8, amp=1, fraction=0.5,
         meta={"factory": PLANT, "location": "Chiller Yard", "unit": "°C", "thresholds": {"max": 12}}),
]

DEFAULT_CONFIG = [
    ("dashboard.poll_interval_seconds", 5, "How often the dashboard refreshes"),
    ("auth.registration_open", True, "Allow self-registration"),
    ("reports.retention_days", 30, "Days before generated reports expire"),
    ("rate_limit.default_per_minute", 100, "Default API requests per minute per user"),
]


def _get_or_create_user(db: Session, email: str, name: str, role: UserRole, password: str) -> tuple[User, bool]:
    user = db.scalar(select(User).where(User.email == email))
    if user:
        return user, False
    user = User(email=email, password_hash=hash_password(password), name=name, role=role,
                is_active=True, email_verified=True)
    user.profile = UserProfile()
    db.add(user)
    db.flush()
    return user, True


def _readings(rng: random.Random, base: float, amp: float, hours: int = 24,
              step_minutes: int = 15, fraction: float = 1.0) -> list[tuple[datetime, float]]:
    now = datetime.now(timezone.utc).replace(second=0, microsecond=0)
    start = now - timedelta(hours=hours)
    total = hours * 60 // step_minutes
    out = []
    for i in range(int(total * fraction) + 1):
        value = base + amp * math.sin(i / 12) + rng.uniform(-amp * 0.2, amp * 0.2)
        out.append((start + timedelta(minutes=i * step_minutes), round(value, 2)))
    return out


def seed_database(db: Session, include_demo: bool = True) -> dict:
    summary = {"users": 0, "sensors": 0, "readings": 0, "config": 0}

    admin, created = _get_or_create_user(db, settings.ADMIN_EMAIL.lower(), "Administrator",
                                         UserRole.admin, settings.ADMIN_PASSWORD)
    summary["users"] += created

    for key, value, description in DEFAULT_CONFIG:
        if not db.scalar(select(SystemConfig).where(SystemConfig.key == key)):
            db.add(SystemConfig(key=key, value=value, description=description, updated_by=admin.id))
            summary["config"] += 1

    if include_demo:
        demo, created = _get_or_create_user(db, DEMO_USER[0], DEMO_USER[1], UserRole.user, DEMO_USER[2])
        summary["users"] += created
        _, created = _get_or_create_user(db, DEMO_GUEST[0], DEMO_GUEST[1], UserRole.guest, DEMO_GUEST[2])
        summary["users"] += created

        has_sensors = db.scalar(select(Sensor.id).where(Sensor.user_id == demo.id).limit(1))
        if not has_sensors:
            rng = random.Random(42)  # same fake data every time
            for spec in DEMO_SENSORS:
                sensor = Sensor(
                    user_id=demo.id, title=spec["title"], category=spec["category"],
                    priority=spec["priority"], status=spec["status"], meta=spec["meta"],
                    description=f"Demo sensor at {spec['meta']['location']}",
                )
                for ts, value in _readings(rng, spec["base"], spec["amp"], fraction=spec.get("fraction", 1.0)):
                    sensor.readings.append(SensorReading(value=value, recorded_at=ts))
                    summary["readings"] += 1
                db.add(sensor)
                summary["sensors"] += 1

    db.commit()
    return summary


def main() -> None:
    setup_logging()
    with SessionLocal() as db:
        summary = seed_database(db, include_demo=settings.SEED_DEMO_DATA)
    logger.info("Seed complete: %s", summary)
    logger.info("Admin login: %s / %s", settings.ADMIN_EMAIL, settings.ADMIN_PASSWORD)


if __name__ == "__main__":
    main()
