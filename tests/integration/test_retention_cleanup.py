from datetime import datetime, timedelta

from sqlalchemy.orm import Session

from src.app.container import get_db_session
from src.db.models import Owner, OwnerSettings, Chat, Message
from src.workers.tasks_maintenance import run_retention_cleanup


def test_retention_cleanup_deletes_old_messages() -> None:
    db: Session = get_db_session()
    try:
        owner = Owner(
            telegram_user_id=111,
            display_name="Owner",
            is_active=True,
            created_at=datetime.utcnow(),
            updated_at=datetime.utcnow(),
        )
        db.add(owner)
        db.flush()

        settings = OwnerSettings(
            owner_id=owner.id,
            open_loop_threshold_hours=24,
            slow_response_threshold_hours=4,
            min_thread_length_for_unresolved=1,
            min_thread_duration_minutes_for_unresolved=0,
            retention_raw_messages_days=1,
            retention_metrics_days=10,
            time_zone="UTC",
            created_at=datetime.utcnow(),
            updated_at=datetime.utcnow(),
        )
        db.add(settings)
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

        old_ts = datetime.utcnow() - timedelta(days=10)
        msg = Message(
            telegram_message_id=1,
            chat_id=chat.id,
            sender_id=None,  # type: ignore[arg-type]
            sent_at=old_ts,
            edited_at=None,
            text="old",
            reply_to_message_id=None,
            is_deleted=False,
            idempotency_key="k1",
            raw_payload={},
            created_at=old_ts,
            updated_at=old_ts,
        )
        db.add(msg)
        db.commit()

        run_retention_cleanup()

        remaining = db.query(Message).all()
        assert remaining == []
    finally:
        db.close()

