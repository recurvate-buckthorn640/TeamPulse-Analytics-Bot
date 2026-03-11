from datetime import date

from sqlalchemy.orm import Session

from src.app.container import get_db_session
from src.db.enums import (
    LLMRunStage,
    LLMRunStatus,
    ProcessSignalSeverity,
    ProcessSignalStatus,
    ProcessSignalType,
    ReportPeriodType,
    ReportStatus,
)
from src.db.models import Chat, LLMRun, Owner, ProcessSignal, Report
from src.workers.tasks_reporting import build_report_task, run_llm_analyst_task


def _seed_owner_chat_and_signal(db: Session) -> Owner:
    owner = Owner(
        telegram_user_id=2222,
        display_name="Owner",
        is_active=True,
        created_at=date.today(),
        updated_at=date.today(),
    )
    db.add(owner)
    db.flush()

    chat = Chat(
        telegram_chat_id=-200,
        title="Team",
        type="supergroup",
        owner_id=owner.id,
        is_active=True,
        created_at=date.today(),
        updated_at=date.today(),
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
        first_detected_at=date.today(),
        last_detected_at=date.today(),
        evidence={},
        metadata={},
    )
    db.add(signal)
    db.commit()
    return owner


def test_report_marked_failed_when_llm_unavailable(monkeypatch) -> None:
    from src.llm import client as client_module

    def _failing_complete_json(self, model, payload):  # noqa: ARG001
        raise RuntimeError("LLM provider unavailable")

    monkeypatch.setattr(client_module.LLMClient, "complete_json", _failing_complete_json)

    db: Session = get_db_session()
    try:
        owner = _seed_owner_chat_and_signal(db)
        today = date.today()
        report_id = build_report_task(
            owner_id=owner.id,
            period_type=ReportPeriodType.DAILY.value,
            period_start=today.isoformat(),
            period_end=today.isoformat(),
        )

        run_llm_analyst_task(report_id)

        report = db.get(Report, report_id)
        assert report is not None
        # when LLM is unavailable, pipeline should mark report as failed
        assert report.status == ReportStatus.FAILED

        runs = db.query(LLMRun).filter(
            LLMRun.report_id == report_id, LLMRun.stage == LLMRunStage.ANALYST
        ).all()
        assert any(r.status == LLMRunStatus.FAILED for r in runs)
    finally:
        db.close()

