from datetime import datetime
from typing import Any, Mapping

from sqlalchemy.orm import Session

from src.db.models import AuditLog


def write_audit_log(
    db: Session,
    *,
    event_type: str,
    actor_type: str,
    actor_id: int | None,
    context: Mapping[str, Any] | None,
    message: str,
) -> None:
    now = datetime.utcnow()
    log = AuditLog(
        event_type=event_type,
        actor_type=actor_type,
        actor_id=actor_id,
        context=dict(context) if context is not None else None,
        message=message,
        created_at=now,
    )
    db.add(log)

