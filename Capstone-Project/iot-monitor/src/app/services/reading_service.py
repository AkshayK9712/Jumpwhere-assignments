from datetime import datetime

from fastapi import Request
from sqlalchemy import insert, select
from sqlalchemy.orm import Session

from app.core.timeutil import as_utc, utcnow
from app.models import Sensor, SensorReading, User
from app.schemas.common import BulkResult
from app.schemas.reading import ReadingBulkCreate, ReadingCreate
from app.services.activity import log_activity


def list_readings(db: Session, sensor: Sensor, from_: datetime | None, to: datetime | None, limit: int) -> list[SensorReading]:
    stmt = select(SensorReading).where(SensorReading.sensor_id == sensor.id)
    if from_ is not None:
        stmt = stmt.where(SensorReading.recorded_at >= as_utc(from_))
    if to is not None:
        stmt = stmt.where(SensorReading.recorded_at <= as_utc(to))
    stmt = stmt.order_by(SensorReading.recorded_at.desc(), SensorReading.id.desc()).limit(limit)
    return list(db.scalars(stmt))


def create_reading(db: Session, sensor: Sensor, data: ReadingCreate) -> SensorReading:
    # Single readings are not written to the audit log: devices can send thousands per day.
    reading = SensorReading(sensor_id=sensor.id, value=data.value, recorded_at=data.recorded_at or utcnow())
    db.add(reading)
    db.commit()
    db.refresh(reading)
    return reading


def bulk_create_readings(db: Session, user: User, sensor: Sensor, data: ReadingBulkCreate,
                         request: Request | None = None) -> BulkResult:
    now = utcnow()
    rows = [{"sensor_id": sensor.id, "value": i.value, "recorded_at": i.recorded_at or now} for i in data.items]
    db.execute(insert(SensorReading), rows)
    db.commit()
    log_activity(db, "reading.bulk_create", user_id=user.id, entity_type="sensor", entity_id=sensor.id,
                 details={"count": len(rows)}, request=request)
    return BulkResult(processed=len(rows), failed=0)
