from __future__ import annotations

from celery import shared_task
from sqlalchemy import select
from sqlalchemy.orm import Session

from src.app.container import get_db_session
from src.db.models import OwnerSettings
from src.reporting.audit import write_audit_log
from src.services.retention_service import RetentionService


@shared_task(name="maintenance.run_retention_cleanup", autoretry_for=(Exception,), retry_backoff=True, retry_kwargs={"max_retries": 3})
def run_retention_cleanup() -> None:
    db: Session = get_db_session()
    try:
        settings_list = list(db.execute(select(OwnerSettings)).scalars())
        service = RetentionService(db)
        for owner_settings in settings_list:
            service.run_for_owner(owner_settings)
        write_audit_log(
            db,
            event_type="retention_cleanup",
            actor_type="system",
            actor_id=None,
            context={},
            message="Retention cleanup completed for all owners",
        )
        db.commit()
    except Exception:
        db.rollback()
        raise
    finally:
        db.close()

