from datetime import datetime

from fastapi import HTTPException, Request, status
from sqlalchemy import case, or_, select
from sqlalchemy.orm import Session

from app.core.sanitize import escape_like
from app.core.timeutil import as_utc
from app.models import Priority, Sensor, SensorCategory, SensorStatus, User, UserRole
from app.schemas.common import BulkError, BulkResult, PageParams, paginate
from app.schemas.sensor import BulkIds, BulkSensorCreate, SensorCreate, SensorUpdate
from app.services.activity import log_activity

_PRIORITY_RANK = case(
    {"low": 1, "medium": 2, "high": 3, "critical": 4},  # plain strings = the stored enum values
    value=Sensor.priority,
    else_=0,
)
SORT_COLUMNS = {"title": Sensor.title, "created_at": Sensor.created_at, "priority": _PRIORITY_RANK}


# ---------- visibility rules ----------
# admin: all sensors | user: own sensors only | guest: all sensors (read-only)
def _visible(user: User):
    stmt = select(Sensor)
    if user.role == UserRole.user:
        stmt = stmt.where(Sensor.user_id == user.id)
    return stmt


def get_visible_sensor(db: Session, user: User, sensor_id: int) -> Sensor:
    sensor = db.get(Sensor, sensor_id)
    # 404 (not 403) so users cannot discover other people's sensor ids
    if sensor is None or (user.role == UserRole.user and sensor.user_id != user.id):
        raise HTTPException(status.HTTP_404_NOT_FOUND, "Sensor not found")
    return sensor


# ---------- read ----------
def list_sensors(
    db: Session, user: User, params: PageParams, status_: SensorStatus | None, category: SensorCategory | None,
    priority: Priority | None, q: str | None, sort: str,
) -> dict:
    stmt = _visible(user)
    if status_ is not None:
        stmt = stmt.where(Sensor.status == status_)
    if category is not None:
        stmt = stmt.where(Sensor.category == category)
    if priority is not None:
        stmt = stmt.where(Sensor.priority == priority)
    if q and q.strip():
        pattern = f"%{escape_like(q.strip())}%"
        stmt = stmt.where(or_(Sensor.title.ilike(pattern, escape="\\"), Sensor.description.ilike(pattern, escape="\\")))

    descending = sort.startswith("-")
    column = SORT_COLUMNS[sort.lstrip("-")]
    stmt = stmt.order_by(column.desc() if descending else column.asc(), Sensor.id.desc() if descending else Sensor.id.asc())
    return paginate(db, stmt, params)


# ---------- write ----------
def _check_unmodified_since(sensor: Sensor, since: datetime | None) -> None:
    """Optimistic concurrency: refuse the write if someone changed the sensor after `since`."""
    if since is not None and as_utc(sensor.updated_at) > as_utc(since):
        raise HTTPException(status.HTTP_409_CONFLICT, "Sensor was modified after the If-Unmodified-Since time; reload and retry")


def _new_sensor(user: User, data: SensorCreate) -> Sensor:
    return Sensor(
        user_id=user.id,
        title=data.title,
        description=data.description,
        status=data.status,
        priority=data.priority,
        category=data.category,
        meta=data.metadata.model_dump(exclude_none=True, mode="json"),
    )


def create_sensor(db: Session, user: User, data: SensorCreate, request: Request | None = None) -> Sensor:
    sensor = _new_sensor(user, data)
    db.add(sensor)
    db.commit()
    db.refresh(sensor)
    log_activity(db, "sensor.create", user_id=user.id, entity_type="sensor", entity_id=sensor.id,
                 details={"title": sensor.title}, request=request)
    return sensor


def replace_sensor(db: Session, user: User, sensor_id: int, data: SensorCreate,
                   since: datetime | None, request: Request | None = None) -> Sensor:
    sensor = get_visible_sensor(db, user, sensor_id)
    _check_unmodified_since(sensor, since)
    sensor.title, sensor.description = data.title, data.description
    sensor.status, sensor.priority, sensor.category = data.status, data.priority, data.category
    sensor.meta = data.metadata.model_dump(exclude_none=True, mode="json")
    db.commit()
    db.refresh(sensor)
    log_activity(db, "sensor.replace", user_id=user.id, entity_type="sensor", entity_id=sensor.id, request=request)
    return sensor


def update_sensor(db: Session, user: User, sensor_id: int, data: SensorUpdate,
                  since: datetime | None, request: Request | None = None) -> Sensor:
    sensor = get_visible_sensor(db, user, sensor_id)
    _check_unmodified_since(sensor, since)
    changes = data.model_dump(exclude_unset=True, exclude={"metadata"})
    for field, value in changes.items():
        setattr(sensor, field, value)
    if "metadata" in data.model_fields_set and data.metadata is not None:
        sensor.meta = data.metadata.model_dump(exclude_none=True, mode="json")
        changes["metadata"] = True
    db.commit()
    db.refresh(sensor)
    log_activity(db, "sensor.update", user_id=user.id, entity_type="sensor", entity_id=sensor.id,
                 details={"fields": sorted(changes)}, request=request)
    return sensor


def delete_sensor(db: Session, user: User, sensor_id: int, request: Request | None = None) -> None:
    sensor = get_visible_sensor(db, user, sensor_id)
    title = sensor.title
    db.delete(sensor)  # readings are removed by the cascade
    db.commit()
    log_activity(db, "sensor.delete", user_id=user.id, entity_type="sensor", entity_id=sensor_id,
                 details={"title": title}, request=request)


# ---------- bulk ----------
def bulk_create(db: Session, user: User, data: BulkSensorCreate, request: Request | None = None) -> BulkResult:
    """All-or-nothing: if any item is invalid the request fails with 422 before reaching here."""
    sensors = [_new_sensor(user, item) for item in data.items]
    db.add_all(sensors)
    db.commit()
    ids = [s.id for s in sensors]
    log_activity(db, "sensor.bulk_create", user_id=user.id, entity_type="sensor",
                 details={"count": len(ids), "ids": ids}, request=request)
    return BulkResult(processed=len(ids), failed=0, ids=ids)


def bulk_delete(db: Session, user: User, data: BulkIds, request: Request | None = None) -> BulkResult:
    """Partial: sensors that are missing or not yours are reported in `errors`."""
    deleted: list[int] = []
    errors: list[BulkError] = []
    for index, sensor_id in enumerate(dict.fromkeys(data.ids)):  # de-duplicate, keep order
        try:
            sensor = get_visible_sensor(db, user, sensor_id)
        except HTTPException:
            errors.append(BulkError(index=index, detail=f"Sensor {sensor_id} not found"))
            continue
        db.delete(sensor)
        deleted.append(sensor_id)
    db.commit()
    if deleted:
        log_activity(db, "sensor.bulk_delete", user_id=user.id, entity_type="sensor",
                     details={"count": len(deleted), "ids": deleted}, request=request)
    return BulkResult(processed=len(deleted), failed=len(errors), ids=deleted, errors=errors)
