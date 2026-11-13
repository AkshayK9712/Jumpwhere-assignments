import json
from datetime import datetime

from pydantic import BaseModel, ConfigDict, Field, field_validator, model_validator

from app.core.sanitize import clean_text
from app.models.enums import Priority, SensorCategory, SensorStatus
from app.schemas.common import Page, reject_explicit_nulls


class Thresholds(BaseModel):
    min: float | None = None
    max: float | None = None

    @model_validator(mode="after")
    def ordered(self):
        if self.min is not None and self.max is not None and self.min > self.max:
            raise ValueError("thresholds.min must be less than or equal to thresholds.max")
        return self


class SensorMetadata(BaseModel):
    """Free-form details; the common keys are validated, extra keys are allowed."""

    model_config = ConfigDict(extra="allow")

    factory: str | None = Field(None, max_length=100)
    location: str | None = Field(None, max_length=100)
    unit: str | None = Field(None, max_length=20)
    thresholds: Thresholds | None = None

    @field_validator("factory", "location", "unit")
    @classmethod
    def clean(cls, v: str | None) -> str | None:
        return clean_text(v) if v is not None else None

    @model_validator(mode="after")
    def clean_extras_and_limit_size(self):
        extra = self.model_extra or {}
        for key, value in list(extra.items()):
            if isinstance(value, str):
                extra[key] = clean_text(value)
        if len(json.dumps(self.model_dump(mode="json"))) > 4000:
            raise ValueError("metadata is too large (max 4000 characters)")
        return self


class SensorCreate(BaseModel):
    title: str = Field(min_length=1, max_length=150)
    description: str | None = Field(None, max_length=1000)
    status: SensorStatus = SensorStatus.active
    priority: Priority = Priority.medium
    category: SensorCategory
    metadata: SensorMetadata = Field(default_factory=SensorMetadata)

    @field_validator("title")
    @classmethod
    def clean_title(cls, v: str) -> str:
        v = clean_text(v)
        if not v:
            raise ValueError("Title must not be blank")
        return v

    @field_validator("description")
    @classmethod
    def clean_description(cls, v: str | None) -> str | None:
        return clean_text(v, multiline=True) if v is not None else None


class SensorUpdate(BaseModel):
    """PATCH body: send only the fields to change. `metadata` is replaced as a whole."""

    title: str | None = Field(None, min_length=1, max_length=150)
    description: str | None = Field(None, max_length=1000)
    status: SensorStatus | None = None
    priority: Priority | None = None
    category: SensorCategory | None = None
    metadata: SensorMetadata | None = None

    @field_validator("title")
    @classmethod
    def clean_title(cls, v: str | None) -> str | None:
        if v is None:
            return v
        v = clean_text(v)
        if not v:
            raise ValueError("Title must not be blank")
        return v

    @field_validator("description")
    @classmethod
    def clean_description(cls, v: str | None) -> str | None:
        return clean_text(v, multiline=True) if v is not None else None

    @model_validator(mode="after")
    def no_nulls(self):
        reject_explicit_nulls(self, nullable=("description",))
        return self


class SensorOut(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: int
    user_id: int
    title: str
    description: str | None = None
    status: SensorStatus
    priority: Priority
    category: SensorCategory
    # The ORM attribute is `meta`; the JSON field is called `metadata`.
    meta: dict = Field(default_factory=dict, serialization_alias="metadata")
    created_at: datetime
    updated_at: datetime


class SensorPage(Page[SensorOut]):
    pass


class BulkSensorCreate(BaseModel):
    items: list[SensorCreate] = Field(min_length=1, max_length=100)


class BulkIds(BaseModel):
    ids: list[int] = Field(min_length=1, max_length=100)
