from datetime import datetime
from typing import Any

from pydantic import BaseModel, ConfigDict, Field, field_validator

from app.core.sanitize import clean_text
from app.schemas.common import Page


class ActivityLogOut(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: int
    user_id: int | None = None
    action: str
    entity_type: str | None = None
    entity_id: int | None = None
    details: dict = Field(default_factory=dict)
    ip_address: str | None = None
    user_agent: str | None = None
    created_at: datetime


class ActivityLogPage(Page[ActivityLogOut]):
    pass


class SystemConfigUpdate(BaseModel):
    value: Any
    description: str | None = Field(None, max_length=255)
    is_active: bool = True

    @field_validator("description")
    @classmethod
    def clean_description(cls, v: str | None) -> str | None:
        return clean_text(v) if v is not None else None


class SystemConfigOut(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: int
    key: str
    value: Any = None
    description: str | None = None
    is_active: bool
    updated_by: int | None = None
    updated_at: datetime
