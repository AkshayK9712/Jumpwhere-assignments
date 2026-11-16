from datetime import datetime, timedelta
from typing import Any, Literal

from pydantic import BaseModel, ConfigDict, Field, field_validator, model_validator

from app.core.sanitize import clean_text
from app.core.timeutil import as_utc
from app.models.enums import ReportFormat, ReportStatus, SensorCategory
from app.schemas.common import Page


class ReportQuery(BaseModel):
    """What goes into a report. Stored as JSON on the report row."""

    model_config = ConfigDict(populate_by_name=True)

    sensor_ids: list[int] | None = Field(None, max_length=100)
    category: SensorCategory | None = None
    from_: datetime | None = Field(None, alias="from")
    to: datetime | None = None
    window_hours: int | None = Field(None, ge=1, le=24 * 366, description="Relative period ending now (used by scheduled reports)")
    template: Literal["summary", "detailed", "alerts"] = "summary"

    @field_validator("from_", "to")
    @classmethod
    def to_utc(cls, v: datetime | None) -> datetime | None:
        return as_utc(v) if v is not None else None

    @model_validator(mode="after")
    def check_range(self):
        if self.from_ and self.to:
            if self.from_ >= self.to:
                raise ValueError("'from' must be before 'to'")
            if self.to - self.from_ > timedelta(days=366):
                raise ValueError("The period cannot be longer than 366 days")
        return self


class ReportSchedule(BaseModel):
    frequency: Literal["daily", "weekly", "monthly"]
    email: bool = True  # notify the owner when each run is ready


class ReportCreate(BaseModel):
    name: str = Field(min_length=1, max_length=150)
    format: ReportFormat
    query_params: ReportQuery = Field(default_factory=ReportQuery)
    scheduled: bool = False
    schedule: ReportSchedule | None = None

    @field_validator("name")
    @classmethod
    def clean_name(cls, v: str) -> str:
        v = clean_text(v)
        if not v:
            raise ValueError("Name must not be blank")
        return v

    @model_validator(mode="after")
    def check_schedule(self):
        if self.scheduled:
            if self.schedule is None:
                raise ValueError("schedule is required when scheduled is true")
            if self.query_params.from_ or self.query_params.to:
                raise ValueError("Scheduled reports use a relative period; omit 'from' and 'to'")
        elif self.schedule is not None:
            raise ValueError("schedule can only be used with scheduled=true")
        return self


class ReportOut(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: int
    user_id: int
    name: str
    format: ReportFormat
    status: ReportStatus
    query_params: dict[str, Any] = Field(default_factory=dict)
    scheduled: bool
    created_at: datetime
    expires_at: datetime | None = None
    next_run_at: datetime | None = None
    last_run_at: datetime | None = None
    source_id: int | None = None


class ReportPage(Page[ReportOut]):
    pass
