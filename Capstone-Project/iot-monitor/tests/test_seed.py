from sqlalchemy import func, select

from app.core.security import verify_password
from app.db.seed import seed_database
from app.models import Sensor, SensorReading, SystemConfig, User, UserRole


def test_seed_creates_admin_and_demo_data(db_session):
    summary = seed_database(db_session)
    assert summary["users"] == 3
    assert summary["sensors"] == 6
    assert summary["readings"] > 300
    assert summary["config"] == 4

    admin = db_session.scalar(select(User).where(User.role == UserRole.admin))
    assert admin.is_active and admin.email_verified
    assert verify_password("Admin@12345", admin.password_hash)


def test_seed_is_idempotent(db_session):
    seed_database(db_session)
    counts = lambda: (
        db_session.scalar(select(func.count(User.id))),
        db_session.scalar(select(func.count(Sensor.id))),
        db_session.scalar(select(func.count(SensorReading.id))),
        db_session.scalar(select(func.count(SystemConfig.id))),
    )
    first = counts()
    again = seed_database(db_session)
    assert counts() == first
    assert again == {"users": 0, "sensors": 0, "readings": 0, "config": 0}


def test_seed_without_demo_data(db_session):
    summary = seed_database(db_session, include_demo=False)
    assert summary["users"] == 1 and summary["sensors"] == 0
