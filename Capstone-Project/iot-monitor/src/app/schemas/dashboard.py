from datetime import datetime

from pydantic import BaseModel

from app.schemas.sensor import Thresholds


class DashboardSummary(BaseModel):
    total_sensors: int
    active_sensors: int
    inactive_sensors: int
    faulty_sensors: int
    readings_in_range: int
    sensors_by_category: dict[str, int]
    range_from: datetime
    range_to: datetime
    generated_at: datetime


class TimeSeriesPoint(BaseModel):
    bucket: datetime
    avg: float
    min: float
    max: float
    count: int


class TimeSeries(BaseModel):
    sensor_id: int
    title: str
    unit: str | None = None
    thresholds: Thresholds | None = None
    interval: str
    range_from: datetime
    range_to: datetime
    points: list[TimeSeriesPoint]
