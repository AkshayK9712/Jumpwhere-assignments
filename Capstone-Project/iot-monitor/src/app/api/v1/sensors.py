from datetime import datetime
from typing import Literal

from fastapi import APIRouter, Depends, Header, Query, Request, Response, status
from sqlalchemy.orm import Session

from app.api.deps import get_current_user, require_writer
from app.db.session import get_db
from app.models import Priority, SensorCategory, SensorStatus, User
from app.schemas.common import BulkResult, PageParams
from app.schemas.sensor import BulkIds, BulkSensorCreate, SensorCreate, SensorOut, SensorPage, SensorUpdate
from app.services import sensor_service

router = APIRouter()

SortKey = Literal["title", "-title", "created_at", "-created_at", "priority", "-priority"]


def IfUnmodifiedSince():  # a fresh Header(...) per parameter
    return Header(None, alias="If-Unmodified-Since",
                  description="ISO date-time. Reject with 409 if the sensor changed after this time.")


@router.get("", response_model=SensorPage, operation_id="list_sensors", summary="List sensors")
def list_sensors(
    params: PageParams = Depends(),
    status_: SensorStatus | None = Query(None, alias="status"),
    category: SensorCategory | None = Query(None),
    priority: Priority | None = Query(None),
    q: str | None = Query(None, max_length=100, description="Search title/description"),
    sort: SortKey = Query("-created_at"),
    user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    return sensor_service.list_sensors(db, user, params, status_, category, priority, q, sort)


@router.post("", response_model=SensorOut, status_code=status.HTTP_201_CREATED, operation_id="create_sensor",
             summary="Create a sensor")
def create_sensor(payload: SensorCreate, request: Request, user: User = Depends(require_writer),
                  db: Session = Depends(get_db)):
    return sensor_service.create_sensor(db, user, payload, request)


# NOTE: /bulk routes must come before /{sensor_id}
@router.post("/bulk", response_model=BulkResult, status_code=status.HTTP_201_CREATED,
             operation_id="bulk_create_sensors", summary="Bulk create sensors")
def bulk_create_sensors(payload: BulkSensorCreate, request: Request, user: User = Depends(require_writer),
                        db: Session = Depends(get_db)):
    return sensor_service.bulk_create(db, user, payload, request)


@router.delete("/bulk", response_model=BulkResult, operation_id="bulk_delete_sensors", summary="Bulk delete sensors")
def bulk_delete_sensors(payload: BulkIds, request: Request, user: User = Depends(require_writer),
                        db: Session = Depends(get_db)):
    return sensor_service.bulk_delete(db, user, payload, request)


@router.get("/{sensor_id}", response_model=SensorOut, operation_id="get_sensor", summary="Get a sensor")
def get_sensor(sensor_id: int, user: User = Depends(get_current_user), db: Session = Depends(get_db)):
    return sensor_service.get_visible_sensor(db, user, sensor_id)


@router.put("/{sensor_id}", response_model=SensorOut, operation_id="replace_sensor", summary="Replace a sensor")
def replace_sensor(sensor_id: int, payload: SensorCreate, request: Request,
                   if_unmodified_since: datetime | None = IfUnmodifiedSince(),
                   user: User = Depends(require_writer), db: Session = Depends(get_db)):
    return sensor_service.replace_sensor(db, user, sensor_id, payload, if_unmodified_since, request)


@router.patch("/{sensor_id}", response_model=SensorOut, operation_id="update_sensor",
              summary="Partially update a sensor")
def update_sensor(sensor_id: int, payload: SensorUpdate, request: Request,
                  if_unmodified_since: datetime | None = IfUnmodifiedSince(),
                  user: User = Depends(require_writer), db: Session = Depends(get_db)):
    return sensor_service.update_sensor(db, user, sensor_id, payload, if_unmodified_since, request)


@router.delete("/{sensor_id}", status_code=status.HTTP_204_NO_CONTENT, operation_id="delete_sensor",
               summary="Delete a sensor", response_class=Response)
def delete_sensor(sensor_id: int, request: Request, user: User = Depends(require_writer),
                  db: Session = Depends(get_db)):
    sensor_service.delete_sensor(db, user, sensor_id, request)
    return Response(status_code=status.HTTP_204_NO_CONTENT)
