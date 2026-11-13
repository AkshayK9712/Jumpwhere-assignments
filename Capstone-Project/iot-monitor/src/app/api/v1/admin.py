import re
from datetime import datetime

from fastapi import APIRouter, Depends, HTTPException, Path, Query, Request, status
from sqlalchemy import select
from sqlalchemy.orm import Session

from app.api.deps import require_admin
from app.core.timeutil import as_utc
from app.db.session import get_db
from app.models import ActivityLog, SystemConfig, User
from app.schemas.admin import ActivityLogPage, SystemConfigOut, SystemConfigUpdate
from app.schemas.common import PageParams, paginate
from app.services.activity import log_activity

router = APIRouter(dependencies=[Depends(require_admin)])  # every route here is admin-only


def ConfigKey():  # a fresh Path(...) per parameter
    return Path(..., pattern=r"^[a-z0-9_.\-]{1,100}$", description="Lowercase letters, digits, . _ -")


@router.get("/activity-logs", response_model=ActivityLogPage, operation_id="list_activity_logs",
            summary="Query the audit trail")
def list_activity_logs(
    params: PageParams = Depends(),
    user_id: int | None = Query(None),
    action: str | None = Query(None, max_length=50),
    entity_type: str | None = Query(None, max_length=50),
    from_: datetime | None = Query(None, alias="from"),
    to: datetime | None = Query(None),
    db: Session = Depends(get_db),
):
    stmt = select(ActivityLog)
    if user_id is not None:
        stmt = stmt.where(ActivityLog.user_id == user_id)
    if action:
        stmt = stmt.where(ActivityLog.action == action)
    if entity_type:
        stmt = stmt.where(ActivityLog.entity_type == entity_type)
    if from_ is not None:
        stmt = stmt.where(ActivityLog.created_at >= as_utc(from_))
    if to is not None:
        stmt = stmt.where(ActivityLog.created_at <= as_utc(to))
    return paginate(db, stmt.order_by(ActivityLog.id.desc()), params)


@router.get("/config", response_model=list[SystemConfigOut], operation_id="list_config",
            summary="List system configuration")
def list_config(db: Session = Depends(get_db)):
    return list(db.scalars(select(SystemConfig).order_by(SystemConfig.key)))


@router.get("/config/{key}", response_model=SystemConfigOut, operation_id="get_config", summary="Get one config entry")
def get_config(key: str = ConfigKey(), db: Session = Depends(get_db)):
    row = db.scalar(select(SystemConfig).where(SystemConfig.key == key))
    if row is None:
        raise HTTPException(status.HTTP_404_NOT_FOUND, "Config key not found")
    return row


@router.put("/config/{key}", response_model=SystemConfigOut, operation_id="put_config",
            summary="Create or update a config entry")
def put_config(payload: SystemConfigUpdate, request: Request, key: str = ConfigKey(),
               admin: User = Depends(require_admin), db: Session = Depends(get_db)):
    row = db.scalar(select(SystemConfig).where(SystemConfig.key == key))
    if row is None:
        row = SystemConfig(key=key)
        db.add(row)
    row.value = payload.value
    row.description = payload.description
    row.is_active = payload.is_active
    row.updated_by = admin.id
    db.commit()
    db.refresh(row)
    log_activity(db, "config.put", user_id=admin.id, entity_type="config", entity_id=row.id,
                 details={"key": key}, request=request)
    return row
