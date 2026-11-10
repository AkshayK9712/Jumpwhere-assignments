import enum


class UserRole(str, enum.Enum):
    admin = "admin"
    user = "user"
    guest = "guest"


class SensorStatus(str, enum.Enum):
    active = "active"
    inactive = "inactive"
    faulty = "faulty"


class SensorCategory(str, enum.Enum):
    temperature = "temperature"
    pressure = "pressure"
    humidity = "humidity"
    vibration = "vibration"
    flow = "flow"
    other = "other"


class Priority(str, enum.Enum):
    low = "low"
    medium = "medium"
    high = "high"
    critical = "critical"


class ReportFormat(str, enum.Enum):
    pdf = "pdf"
    csv = "csv"


class ReportStatus(str, enum.Enum):
    pending = "pending"
    ready = "ready"
    failed = "failed"
