from datetime import datetime, timedelta

from fastapi import HTTPException, status
from sqlalchemy import func, select
from sqlalchemy.orm import Session

from app.core.timeutil import as_utc, utcnow
from app.models import Sensor, SensorCategory, SensorReading, User, UserRole
from app.services.analytics import bucket_count, bucketize
from app.services.sensor_service import get_visible_sensor

MAX_POINTS = 2000
MAX_ROWS = 100_000
MAX_RANGE = timedelta(days=366)


def resolve_range(from_: datetime | None, to: datetime | None, default_hours: int = 24) -> tuple[datetime, datetime]:
    end = as_utc(to) if to else utcnow()
    start = as_utc(from_) if from_ else end - timedelta(hours=default_hours)
    if start >= end:
        raise HTTPException(status.HTTP_422_UNPROCESSABLE_ENTITY, "'from' must be before 'to'")
    if end - start > MAX_RANGE:
        raise HTTPException(status.HTTP_422_UNPROCESSABLE_ENTITY, "The period cannot be longer than 366 days")
    return start, end


def _conditions(user: User, category: SensorCategory | None) -> list:
    conds = []
    if user.role == UserRole.user:  # users see their own sensors; admins and guests see all
        conds.append(Sensor.user_id == user.id)
    if category is not None:
        conds.append(Sensor.category == category)
    return conds


def summary(db: Session, user: User, category: SensorCategory | None, from_: datetime | None, to: datetime | None) -> dict:
    start, end = resolve_range(from_, to)
    conds = _conditions(user, category)

    by_status = {s.value: n for s, n in db.execute(select(Sensor.status, func.count(Sensor.id)).where(*conds).group_by(Sensor.status))}
    by_category = {c.value: n for c, n in db.execute(select(Sensor.category, func.count(Sensor.id)).where(*conds).group_by(Sensor.category))}
    readings = db.scalar(
        select(func.count(SensorReading.id))
        .join(Sensor, Sensor.id == SensorReading.sensor_id)
        .where(*conds, SensorReading.recorded_at >= start, SensorReading.recorded_at <= end)
    ) or 0

    return {
        "total_sensors": sum(by_status.values()),
        "active_sensors": by_status.get("active", 0),
        "inactive_sensors": by_status.get("inactive", 0),
        "faulty_sensors": by_status.get("faulty", 0),
        "readings_in_range": readings,
        "sensors_by_category": by_category,
        "range_from": start,
        "range_to": end,
        "generated_at": utcnow(),
    }


def timeseries(db: Session, user: User, sensor_id: int, from_: datetime | None, to: datetime | None, interval: str) -> dict:
    sensor = get_visible_sensor(db, user, sensor_id)  # 404 if the user may not see it
    start, end = resolve_range(from_, to)
    if bucket_count(start, end, interval) > MAX_POINTS:
        raise HTTPException(status.HTTP_422_UNPROCESSABLE_ENTITY,
                            f"Too many data points for this period; use a larger interval or a shorter period (max {MAX_POINTS})")

    rows = db.execute(
        select(SensorReading.recorded_at, SensorReading.value)
        .where(SensorReading.sensor_id == sensor.id, SensorReading.recorded_at >= start, SensorReading.recorded_at <= end)
        .order_by(SensorReading.recorded_at)
        .limit(MAX_ROWS + 1)
    ).all()
    if len(rows) > MAX_ROWS:
        raise HTTPException(status.HTTP_422_UNPROCESSABLE_ENTITY, "Too many readings in this period; choose a shorter period")

    meta = sensor.meta or {}
    return {
        "sensor_id": sensor.id,
        "title": sensor.title,
        "unit": meta.get("unit"),
        "thresholds": meta.get("thresholds"),
        "interval": interval,
        "range_from": start,
        "range_to": end,
        "points": bucketize(((as_utc(ts), value) for ts, value in rows), interval),
    }
