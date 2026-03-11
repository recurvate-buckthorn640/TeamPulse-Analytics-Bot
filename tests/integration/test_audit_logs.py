from datetime import date, datetime

from sqlalchemy.orm import Session

from src.app.container import get_db_session
from src.db.enums import (
    ProcessSignalSeverity,
    ProcessSignalStatus,
    ProcessSignalType,
    ReportPeriodType,
)
from src.db.models import Owner, Chat, ProcessSignal, AuditLog
from src.services.report_service import ReportService
from src.workers.tasks_maintenance import run_retention_cleanup


def _seed_owner_and_signal(db: Session) -> Owner:
    owner = Owner(
        telegram_user_id=9999,
        display_name="Owner",
        is_active=True,
        created_at=datetime.utcnow(),
        updated_at=datetime.utcnow(),
    )
    db.add(owner)
    db.flush()

    chat = Chat(
        telegram_chat_id=-100,
        title="Team",
        type="supergroup",
        owner_id=owner.id,
        is_active=True,
        created_at=datetime.utcnow(),
        updated_at=datetime.utcnow(),
    )
    db.add(chat)
    db.flush()

    signal = ProcessSignal(
        thread_id=1,
        chat_id=chat.id,
        owner_id=owner.id,
        type=ProcessSignalType.OPEN_LOOP,
        severity=ProcessSignalSeverity.MEDIUM,
        status=ProcessSignalStatus.ACTIVE,
        first_detected_at=datetime.utcnow(),
        last_detected_at=datetime.utcnow(),
        evidence={},
        metadata={},
    )
    db.add(signal)
    db.commit()
    return owner


def test_audit_log_for_report_creation_and_retention() -> None:
    db = get_db_session()
    try:
        owner = _seed_owner_and_signal(db)
        today = date.today()
        service = ReportService(db)
        service.build_report(
            owner_id=owner.id,
            period_type=ReportPeriodType.DAILY,
            period_start=today,
            period_end=today,
        )
        db.commit()

        run_retention_cleanup()

        logs = db.query(AuditLog).all()
        types = {l.event_type for l in logs}
        assert "report_created" in types
        assert "retention_cleanup" in types
    finally:
        db.close()

