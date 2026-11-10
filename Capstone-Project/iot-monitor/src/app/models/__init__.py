"""Import every model so Base.metadata knows all tables (needed by Alembic)."""
from app.models.activity_log import ActivityLog
from app.models.enums import (
    Priority,
    ReportFormat,
    ReportStatus,
    SensorCategory,
    SensorStatus,
    UserRole,
)
from app.models.report import Report
from app.models.sensor import Sensor, SensorReading
from app.models.system_config import SystemConfig
from app.models.user import RefreshToken, User, UserProfile

__all__ = [
    "ActivityLog", "Priority", "RefreshToken", "Report", "ReportFormat", "ReportStatus",
    "Sensor", "SensorCategory", "SensorReading", "SensorStatus", "SystemConfig",
    "User", "UserProfile", "UserRole",
]
