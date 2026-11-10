from sqlalchemy import JSON, BigInteger, DateTime, Integer, func
from sqlalchemy.dialects.postgresql import JSONB
from sqlalchemy.orm import Mapped, mapped_column

# JSONB on PostgreSQL, plain JSON elsewhere (lets tests run on SQLite)
JSONType = JSON().with_variant(JSONB(), "postgresql")

# BigInteger primary keys that still autoincrement on SQLite
BigIntPK = BigInteger().with_variant(Integer(), "sqlite")


class TimestampMixin:
    created_at: Mapped["DateTime"] = mapped_column(
        DateTime(timezone=True), server_default=func.now(), nullable=False
    )
    updated_at: Mapped["DateTime"] = mapped_column(
        DateTime(timezone=True),
        server_default=func.now(),
        onupdate=func.now(),
        nullable=False,
    )
