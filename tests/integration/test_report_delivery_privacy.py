from datetime import date, datetime

from sqlalchemy.orm import Session

from src.app.container import get_db_session
from src.db.enums import (
    ProcessSignalSeverity,
    ProcessSignalStatus,
    ProcessSignalType,
    ReportPeriodType,
    ReportStatus,
)
from src.db.models import Owner, Chat, ProcessSignal, Report, LLMRun
from src.llm.schemas import FinalizerOutput
from src.workers.tasks_reporting import deliver_report_task


def _seed_report_ready_for_delivery(db: Session) -> Report:
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
    db.flush()

    today = date.today()
    report = Report(
        owner_id=owner.id,
        period_type=ReportPeriodType.DAILY,
        period_start=today,
        period_end=today,
        status=ReportStatus.VERIFIED,
        created_at=datetime.utcnow(),
        updated_at=datetime.utcnow(),
        delivered_at=None,
        rejection_reason=None,
    )
    db.add(report)
    db.flush()

    # create finalizer LLM run with text
    run = LLMRun(
        report_id=report.id,
        stage=None,  # type: ignore[arg-type]
        status=None,  # type: ignore[arg-type]
        request_payload={},
        response_payload=FinalizerOutput(report_id=str(report.id), text="hi").model_dump(),
        error_message=None,
        created_at=datetime.utcnow(),
        updated_at=datetime.utcnow(),
        correlation_id="corr",
    )
    db.add(run)
    db.commit()
    return report


def test_report_delivery_only_for_verified_reports(monkeypatch) -> None:
    sent_messages: list[tuple[int, str]] = []

    async def _fake_send_telegram_message(telegram_user_id: int, text: str) -> None:
        sent_messages.append((telegram_user_id, text))

    from src.reporting import delivery as delivery_module

    monkeypatch.setattr(
        delivery_module, "_send_telegram_message", _fake_send_telegram_message
    )

    db = get_db_session()
    try:
        report = _seed_report_ready_for_delivery(db)
        deliver_report_task(report.id)
        # after delivery, we expect exactly one DM sent
        assert len(sent_messages) == 1
    finally:
        db.close()

