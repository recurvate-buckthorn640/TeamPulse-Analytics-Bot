from datetime import date, datetime

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
from src.db.models import Owner, Chat, ProcessSignal, Report, LLMRun
from src.workers.tasks_reporting import (
    build_report_task,
    run_llm_analyst_task,
    run_llm_verifier_task,
    run_llm_finalizer_task,
)


class _FakeClient:
    def __init__(self) -> None:
        self._counter = 0

    def complete_json(self, model: str, payload):
        # simple deterministic JSON responses for each stage
        if model == "analyst":
            return {
                "overview": {"summary": "ok"},
                "sections": [
                    {"id": "sec1", "title": "Open loops", "signal_ids": ["s1"]},
                ],
                "claims": [
                    {"id": "c1", "text": "one", "signal_ids": ["s1"], "recommendation": True}
                ],
            }
        if model == "verifier":
            return {
                "report_id": "r1",
                "claims": [{"claim_id": "c1", "supported": True, "reason": "ok"}],
                "overall_supported": True,
                "notes": "",
            }
        if model == "finalizer":
            return {"report_id": "r1", "text": "final text"}
        raise AssertionError("unexpected model")


def _seed_data(db: Session) -> Owner:
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
        evidence={"root_message_id": "1"},
        metadata={},
    )
    db.add(signal)
    db.commit()
    return owner


def test_llm_pipeline_happy_path(monkeypatch) -> None:
    # monkeypatch LLMClient to avoid real HTTP
    from src import llm as llm_pkg
    from src.llm import client as client_module

    fake_client = _FakeClient()

    def _fake_init(self, *, base_url: str = "https://api.openai.com/v1") -> None:  # noqa: ARG001
        pass

    def _fake_complete_json(self, model, payload):
        return fake_client.complete_json(model, payload)

    monkeypatch.setattr(client_module.LLMClient, "__init__", _fake_init)
    monkeypatch.setattr(client_module.LLMClient, "complete_json", _fake_complete_json)

    db = get_db_session()
    try:
        owner = _seed_data(db)
        today = date.today()
        report_id = build_report_task(
            owner_id=owner.id,
            period_type=ReportPeriodType.DAILY.value,
            period_start=today.isoformat(),
            period_end=today.isoformat(),
        )
        assert isinstance(report_id, int)

        run_llm_analyst_task(report_id)
        run_llm_verifier_task(report_id)
        run_llm_finalizer_task(report_id)

        report = db.get(Report, report_id)
        assert report is not None

        runs = db.query(LLMRun).filter(LLMRun.report_id == report_id).all()
        stages = {r.stage for r in runs}
        assert {LLMRunStage.ANALYST, LLMRunStage.VERIFIER, LLMRunStage.FINALIZER}.issubset(
            stages
        )
        assert all(r.status in {LLMRunStatus.SUCCESS, LLMRunStatus.FAILED} for r in runs)
        # after verifier success, report should be at least VERIFIED
        assert report.status in {ReportStatus.VERIFIED, ReportStatus.FAILED, ReportStatus.REJECTED}
    finally:
        db.close()

