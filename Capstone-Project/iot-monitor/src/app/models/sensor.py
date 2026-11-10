from datetime import datetime

from sqlalchemy import DateTime, Enum, Float, ForeignKey, Index, Integer, String, Text
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.db.session import Base
from app.models.base import BigIntPK, JSONType, TimestampMixin
from app.models.enums import Priority, SensorCategory, SensorStatus


class Sensor(TimestampMixin, Base):
    """MainEntity of the application: one physical IoT sensor/device."""

    __tablename__ = "sensors"

    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    user_id: Mapped[int] = mapped_column(
        ForeignKey("users.id", ondelete="CASCADE"), index=True, nullable=False
    )
    title: Mapped[str] = mapped_column(String(150), nullable=False)
    description: Mapped[str | None] = mapped_column(Text)
    status: Mapped[SensorStatus] = mapped_column(
        Enum(SensorStatus, native_enum=False, length=20),
        default=SensorStatus.active,
        index=True,
        nullable=False,
    )
    priority: Mapped[Priority] = mapped_column(
        Enum(Priority, native_enum=False, length=20),
        default=Priority.medium,
        nullable=False,
    )
    category: Mapped[SensorCategory] = mapped_column(
        Enum(SensorCategory, native_enum=False, length=20),
        index=True,
        nullable=False,
    )
    # Python attribute is `meta` because `metadata` is reserved by SQLAlchemy.
    # Stores factory, location, unit, thresholds, etc.
    meta: Mapped[dict] = mapped_column("metadata", JSONType, default=dict, nullable=False)

    owner: Mapped["User"] = relationship(back_populates="sensors")
    readings: Mapped[list["SensorReading"]] = relationship(
        back_populates="sensor", cascade="all, delete-orphan", passive_deletes=True
    )


class SensorReading(Base):
    """One time-series data point from a sensor."""

    __tablename__ = "sensor_readings"
    __table_args__ = (Index("ix_readings_sensor_time", "sensor_id", "recorded_at"),)

    id: Mapped[int] = mapped_column(BigIntPK, primary_key=True)
    sensor_id: Mapped[int] = mapped_column(
        ForeignKey("sensors.id", ondelete="CASCADE"), nullable=False
    )
    value: Mapped[float] = mapped_column(Float, nullable=False)
    recorded_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False)

    sensor: Mapped["Sensor"] = relationship(back_populates="readings")
