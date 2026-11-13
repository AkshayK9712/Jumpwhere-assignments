import json
import re
from datetime import datetime
from typing import Any

from pydantic import BaseModel, ConfigDict, EmailStr, Field, field_validator, model_validator

from app.core.sanitize import clean_text
from app.core.security import password_problems
from app.models.enums import UserRole
from app.schemas.common import Page, reject_explicit_nulls


class UserRegister(BaseModel):
    email: EmailStr
    # bcrypt only uses the first 72 bytes, so we cap the length there
    password: str = Field(min_length=8, max_length=72)
    name: str = Field(min_length=1, max_length=120)

    @field_validator("password")
    @classmethod
    def strong_password(cls, v: str) -> str:
        problems = password_problems(v)
        if problems:
            raise ValueError("Password needs " + ", ".join(problems))
        return v

    @field_validator("name")
    @classmethod
    def clean_name(cls, v: str) -> str:
        v = clean_text(v)
        if not v:
            raise ValueError("Name must not be blank")
        return v


class EmailOnly(BaseModel):
    email: EmailStr


class UserOut(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: int
    email: EmailStr
    name: str
    role: UserRole
    is_active: bool
    email_verified: bool
    created_at: datetime
    updated_at: datetime | None = None
    last_login: datetime | None = None


class UserPage(Page[UserOut]):
    pass


class UserUpdate(BaseModel):
    name: str | None = Field(None, min_length=1, max_length=120)

    @field_validator("name")
    @classmethod
    def clean_name(cls, v: str | None) -> str | None:
        if v is None:
            return v
        v = clean_text(v)
        if not v:
            raise ValueError("Name must not be blank")
        return v

    @model_validator(mode="after")
    def no_nulls(self):
        reject_explicit_nulls(self)
        return self


class AdminUserUpdate(UserUpdate):
    role: UserRole | None = None
    is_active: bool | None = None


class UserProfileUpdate(BaseModel):
    avatar_url: str | None = Field(None, max_length=500)
    bio: str | None = Field(None, max_length=500)
    phone: str | None = Field(None, max_length=30)
    preferences: dict[str, Any] = Field(default_factory=dict)
    timezone: str = Field("UTC", max_length=64)
    language: str = Field("en", max_length=10)

    @field_validator("avatar_url")
    @classmethod
    def http_url_only(cls, v: str | None) -> str | None:
        if v is not None and not re.match(r"^https?://", v, re.IGNORECASE):
            raise ValueError("avatar_url must start with http:// or https://")
        return v

    @field_validator("bio")
    @classmethod
    def clean_bio(cls, v: str | None) -> str | None:
        return clean_text(v, multiline=True) if v is not None else None

    @field_validator("phone")
    @classmethod
    def valid_phone(cls, v: str | None) -> str | None:
        if v is not None and not re.match(r"^[0-9+()\-\s]{5,30}$", v):
            raise ValueError("Phone may contain only digits, spaces, + - ( )")
        return v

    @field_validator("timezone")
    @classmethod
    def valid_timezone(cls, v: str) -> str:
        if not re.match(r"^[A-Za-z0-9_+\-/]{1,64}$", v):
            raise ValueError("Invalid timezone name")
        return v

    @field_validator("language")
    @classmethod
    def valid_language(cls, v: str) -> str:
        if not re.match(r"^[a-z]{2,3}(-[A-Za-z]{2,4})?$", v):
            raise ValueError("Use a language code like 'en' or 'en-US'")
        return v

    @field_validator("preferences")
    @classmethod
    def small_preferences(cls, v: dict) -> dict:
        if len(json.dumps(v)) > 5000:
            raise ValueError("preferences is too large (max 5000 characters)")
        return v


class UserProfileOut(UserProfileUpdate):
    model_config = ConfigDict(from_attributes=True)

    id: int
    user_id: int
