from datetime import datetime

from fastapi import APIRouter, Depends, HTTPException, Query, Request, status
from sqlalchemy.orm import Session

from app.api.deps import get_current_user, require_writer
from app.core.timeutil import as_utc
from app.db.session import get_db
from app.models import User
from app.schemas.common import BulkResult
from app.schemas.reading import ReadingBulkCreate, ReadingCreate, ReadingOut
from app.services import reading_service, sensor_service

router = APIRouter()


@router.get("/sensors/{sensor_id}/readings", response_model=list[ReadingOut], operation_id="list_readings",
            summary="List readings of a sensor")
def list_readings(
    sensor_id: int,
    from_: datetime | None = Query(None, alias="from"),
    to: datetime | None = Query(None),
    limit: int = Query(500, ge=1, le=5000),
    user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    if from_ is not None and to is not None and as_utc(from_) > as_utc(to):
        raise HTTPException(status.HTTP_422_UNPROCESSABLE_ENTITY, "'from' must not be after 'to'")
    sensor = sensor_service.get_visible_sensor(db, user, sensor_id)
    return reading_service.list_readings(db, sensor, from_, to, limit)


@router.post("/sensors/{sensor_id}/readings", response_model=ReadingOut, status_code=status.HTTP_201_CREATED,
             operation_id="create_reading", summary="Add a reading")
def create_reading(sensor_id: int, payload: ReadingCreate, user: User = Depends(require_writer),
                   db: Session = Depends(get_db)):
    sensor = sensor_service.get_visible_sensor(db, user, sensor_id)
    return reading_service.create_reading(db, sensor, payload)


@router.post("/sensors/{sensor_id}/readings/bulk", response_model=BulkResult, status_code=status.HTTP_201_CREATED,
             operation_id="bulk_create_readings", summary="Ingest many readings")
def bulk_create_readings(sensor_id: int, payload: ReadingBulkCreate, request: Request,
                         user: User = Depends(require_writer), db: Session = Depends(get_db)):
    sensor = sensor_service.get_visible_sensor(db, user, sensor_id)
    return reading_service.bulk_create_readings(db, user, sensor, payload, request)
