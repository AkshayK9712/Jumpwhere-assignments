from datetime import datetime, timedelta

from pydantic import BaseModel, ConfigDict, Field, field_validator

from app.core.timeutil import as_utc, utcnow


class ReadingCreate(BaseModel):
    value: float = Field(allow_inf_nan=False)
    recorded_at: datetime | None = None  # defaults to server time

    @field_validator("recorded_at")
    @classmethod
    def not_in_future(cls, v: datetime | None) -> datetime | None:
        if v is None:
            return v
        v = as_utc(v)
        if v > utcnow() + timedelta(minutes=5):
            raise ValueError("recorded_at cannot be in the future")
        return v


class ReadingBulkCreate(BaseModel):
    items: list[ReadingCreate] = Field(min_length=1, max_length=1000)


class ReadingOut(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: int
    sensor_id: int
    value: float
    recorded_at: datetime
