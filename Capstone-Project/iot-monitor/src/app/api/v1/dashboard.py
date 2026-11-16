from datetime import datetime
from typing import Literal

from fastapi import APIRouter, Depends, Query
from sqlalchemy.orm import Session

from app.api.deps import get_current_user
from app.db.session import get_db
from app.models import SensorCategory, User
from app.schemas.dashboard import DashboardSummary, TimeSeries
from app.services import dashboard_service

router = APIRouter()


@router.get("/summary", response_model=DashboardSummary, operation_id="dashboard_summary", summary="Key metrics")
def dashboard_summary(
    category: SensorCategory | None = Query(None),
    from_: datetime | None = Query(None, alias="from", description="Start of the period (default: 24 hours ago)"),
    to: datetime | None = Query(None, description="End of the period (default: now)"),
    user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    """Designed to be polled every few seconds by the dashboard."""
    return dashboard_service.summary(db, user, category, from_, to)


@router.get("/timeseries", response_model=TimeSeries, operation_id="dashboard_timeseries",
            summary="Aggregated readings for charts")
def dashboard_timeseries(
    sensor_id: int = Query(...),
    from_: datetime | None = Query(None, alias="from"),
    to: datetime | None = Query(None),
    interval: Literal["minute", "hour", "day"] = Query("hour"),
    user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    return dashboard_service.timeseries(db, user, sensor_id, from_, to, interval)
