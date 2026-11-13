import math
from typing import Generic, TypeVar

from fastapi import Query
from pydantic import BaseModel
from sqlalchemy import func, select
from sqlalchemy.orm import Session

T = TypeVar("T")


class Page(BaseModel, Generic[T]):
    items: list[T]
    total: int
    page: int
    page_size: int
    pages: int


class PageParams:
    """Dependency: ?page=1&page_size=20"""

    def __init__(
        self,
        page: int = Query(1, ge=1),
        page_size: int = Query(20, ge=1, le=100),
    ):
        self.page = page
        self.page_size = page_size

    @property
    def offset(self) -> int:
        return (self.page - 1) * self.page_size


def paginate(db: Session, stmt, params: PageParams) -> dict:
    """Run `stmt` with LIMIT/OFFSET and return a dict matching the Page schema."""
    total = db.scalar(select(func.count()).select_from(stmt.order_by(None).subquery())) or 0
    items = db.scalars(stmt.offset(params.offset).limit(params.page_size)).all()
    return {
        "items": items,
        "total": total,
        "page": params.page,
        "page_size": params.page_size,
        "pages": math.ceil(total / params.page_size) if total else 0,
    }


class BulkError(BaseModel):
    index: int
    detail: str


class BulkResult(BaseModel):
    processed: int
    failed: int = 0
    ids: list[int] | None = None
    errors: list[BulkError] = []


def reject_explicit_nulls(model: BaseModel, nullable: tuple[str, ...] = ()) -> None:
    """PATCH bodies may omit a field, but must not send null for a required column."""
    for field in model.model_fields_set:
        if getattr(model, field) is None and field not in nullable:
            raise ValueError(f"{field} cannot be null")
