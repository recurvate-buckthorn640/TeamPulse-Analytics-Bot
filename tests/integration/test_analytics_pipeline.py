from fastapi.testclient import TestClient
from sqlalchemy import select

from src.app.main import create_app
from src.api.deps import SessionLocal
from src.db.models import Chat, Owner, OwnerSettings, ProcessSignal
from src.db.enums import ProcessSignalType
from src.services.analytics_service import AnalyticsService
from src.services.thread_service import ThreadService


app = create_app()
client = TestClient(app)


def test_analytics_pipeline_creates_signals_for_chat() -> None:
    session = SessionLocal()
    try:
        # arrange: create owner, chat, settings, and a simple message thread via webhook
        owner = Owner(
            telegram_user_id=9999,
            display_name="Owner",
            is_active=True,
            created_at=None,
            updated_at=None,
        )
        session.add(owner)
        session.flush()

        chat = Chat(
            telegram_chat_id=-10012345,
            title="Team",
            type="supergroup",
            owner_id=owner.id,
            is_active=True,
            created_at=None,
            updated_at=None,
        )
        session.add(chat)
        session.flush()

        settings = OwnerSettings(
            owner_id=owner.id,
            open_loop_threshold_hours=24,
            slow_response_threshold_hours=4,
            min_thread_length_for_unresolved=1,
            min_thread_duration_minutes_for_unresolved=0,
            retention_raw_messages_days=180,
            retention_metrics_days=365,
            time_zone="UTC",
            created_at=None,
            updated_at=None,
        )
        session.add(settings)
        session.commit()
    finally:
        session.close()

    payload = {
        "update_id": 100,
        "message": {
            "message_id": 1,
            "date": 1_700_000_000,
            "chat": {"id": -10012345, "type": "supergroup", "title": "Team"},
            "from": {"id": 1, "is_bot": False, "first_name": "User"},
            "text": "hello",
        },
    }
    resp = client.post("/webhook/telegram", json=payload)
    assert resp.status_code == 200

    # build threads and run analytics directly (without Celery)
    session = SessionLocal()
    try:
        thread_service = ThreadService(session)
        threads = thread_service.build_threads_for_chat(chat_id=chat.id)
        assert threads

        analytics = AnalyticsService(session)
        analytics.run_for_chat(chat_id=chat.id)
        session.commit()

        signals = session.execute(select(ProcessSignal)).scalars().all()
        assert signals
        types = {s.type for s in signals}
        assert ProcessSignalType.OPEN_LOOP in types or ProcessSignalType.UNRESOLVED_THREAD in types
    finally:
        session.close()

