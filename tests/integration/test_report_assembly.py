from datetime import date, datetime

from sqlalchemy.orm import Session

from src.app.container import get_db_session
from src.db.enums import (
    ProcessSignalSeverity,
    ProcessSignalStatus,
    ProcessSignalType,
    ReportPeriodType,
)
from src.db.models import Owner, Chat, ProcessSignal
from src.services.report_service import ReportService


def _seed_owner_chat_and_signal(db: Session) -> Owner:
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
        telegram_chat_id=-100123,
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


def test_report_assembly_creates_report_and_items() -> None:
    db = get_db_session()
    try:
        owner = _seed_owner_chat_and_signal(db)
        service = ReportService(db)
        today = date.today()
        report = service.build_report(
            owner_id=owner.id,
            period_type=ReportPeriodType.DAILY,
            period_start=today,
            period_end=today,
        )
        db.commit()

        assert report.id is not None
        # lazy import to avoid circulars
        from src.db.models import ReportItem

        items = db.query(ReportItem).filter(ReportItem.report_id == report.id).all()
        assert items
    finally:
        db.close()

