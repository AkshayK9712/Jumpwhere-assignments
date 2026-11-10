"""Create every table on in-memory SQLite and exercise relationships."""
from datetime import datetime, timezone

import pytest
from sqlalchemy import create_engine, event, inspect
from sqlalchemy.orm import Session

from app.db.session import Base
from app import models  # noqa: F401  (registers all tables)
from app.models import (
    ActivityLog, Priority, Report, ReportFormat, Sensor, SensorCategory,
    SensorReading, SystemConfig, User, UserProfile, UserRole,
)


@pytest.fixture()
def db():
    engine = create_engine("sqlite:///:memory:")

    @event.listens_for(engine, "connect")
    def _fk_on(dbapi_conn, _):
        dbapi_conn.execute("PRAGMA foreign_keys=ON")

    Base.metadata.create_all(engine)
    with Session(engine) as session:
        yield session


def test_all_tables_exist(db):
    tables = set(inspect(db.get_bind()).get_table_names())
    assert tables == {
        "users", "user_profiles", "sensors", "sensor_readings",
        "activity_logs", "reports", "system_config", "refresh_tokens",
    }


def test_sensor_readings_composite_index(db):
    idx = inspect(db.get_bind()).get_indexes("sensor_readings")
    assert any(i["column_names"] == ["sensor_id", "recorded_at"] for i in idx)


def test_user_sensor_reading_chain(db):
    user = User(email="a@b.com", password_hash="x", name="Ann", role=UserRole.admin)
    user.profile = UserProfile(timezone="Asia/Kolkata")
    sensor = Sensor(
        title="Boiler temp", category=SensorCategory.temperature,
        meta={"factory": "Hyderabad", "unit": "C", "thresholds": {"max": 90}},
    )
    sensor.readings.append(SensorReading(value=71.5, recorded_at=datetime.now(timezone.utc)))
    user.sensors.append(sensor)
    db.add(user)
    db.commit()

    saved = db.query(Sensor).one()
    assert saved.priority == Priority.medium           # default
    assert saved.meta["factory"] == "Hyderabad"
    assert saved.owner.email == "a@b.com"
    assert saved.readings[0].value == 71.5
    assert user.profile.language == "en"
    assert user.is_active is False                     # must verify email first


def test_deleting_user_cascades_but_keeps_audit_log(db):
    user = User(email="c@d.com", password_hash="x", name="Cy")
    user.sensors.append(Sensor(title="S", category=SensorCategory.pressure))
    user.reports.append(Report(name="R", format=ReportFormat.csv))
    db.add(user)
    db.flush()
    db.add(ActivityLog(user_id=user.id, action="user.login"))
    db.add(SystemConfig(key="feature.x", value=True, updated_by=user.id))
    db.commit()

    db.delete(user)
    db.commit()

    assert db.query(Sensor).count() == 0
    assert db.query(Report).count() == 0
    assert db.query(ActivityLog).one().user_id is None
    assert db.query(SystemConfig).one().updated_by is None
