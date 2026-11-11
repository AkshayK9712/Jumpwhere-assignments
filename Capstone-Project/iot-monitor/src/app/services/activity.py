from fastapi import Request
from sqlalchemy.orm import Session

from app.models import ActivityLog


def log_activity(
    db: Session,
    action: str,
    user_id: int | None = None,
    entity_type: str | None = None,
    entity_id: int | None = None,
    details: dict | None = None,
    request: Request | None = None,
) -> None:
    """Write one row to the audit trail (activity_logs)."""
    ip = request.client.host if request is not None and request.client else None
    agent = request.headers.get("user-agent", "")[:255] if request is not None else None
    db.add(
        ActivityLog(
            user_id=user_id,
            action=action,
            entity_type=entity_type,
            entity_id=entity_id,
            details=details or {},
            ip_address=ip,
            user_agent=agent,
        )
    )
    db.commit()
