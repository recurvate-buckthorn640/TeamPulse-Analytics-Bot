from sqlalchemy.orm import Session

from src.app.container import get_db_session
from src.db.enums import ProcessSignalSeverity, ProcessSignalStatus, ProcessSignalType
from src.db.models import Owner, Chat, ProcessSignal
from src.services.analytics_service import AnalyticsService


def test_run_analytics_for_chat_idempotent() -> None:
    db: Session = get_db_session()
    try:
        owner = Owner(
            telegram_user_id=123,
            display_name="Owner",
            is_active=True,
            created_at=None,
            updated_at=None,
        )
        db.add(owner)
        db.flush()

        chat = Chat(
            telegram_chat_id=-100,
            title="Team",
            type="supergroup",
            owner_id=owner.id,
            is_active=True,
            created_at=None,
            updated_at=None,
        )
        db.add(chat)
        db.flush()

        # seed a single signal
        signal = ProcessSignal(
            thread_id=1,
            chat_id=chat.id,
            owner_id=owner.id,
            type=ProcessSignalType.OPEN_LOOP,
            severity=ProcessSignalSeverity.MEDIUM,
            status=ProcessSignalStatus.ACTIVE,
            first_detected_at=None,  # type: ignore[arg-type]
            last_detected_at=None,  # type: ignore[arg-type]
            evidence={},
            metadata={},
        )
        db.add(signal)
        db.commit()

        service = AnalyticsService(db)
        service.run_for_chat(chat.id)
        db.commit()
        service.run_for_chat(chat.id)
        db.commit()

        rows = db.query(ProcessSignal).all()
        assert len(rows) == 1
    finally:
        db.close()

