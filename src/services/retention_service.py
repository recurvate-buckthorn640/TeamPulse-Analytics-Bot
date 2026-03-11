from __future__ import annotations

from datetime import datetime, timedelta

from sqlalchemy import delete
from sqlalchemy.orm import Session

from src.db.models import Message, MessageEdit, Mention, OwnerSettings


class RetentionService:
    def __init__(self, db: Session) -> None:
        self.db = db

    def run_for_owner(self, owner_settings: OwnerSettings) -> None:
        """
        Apply retention policy for a single owner.
        """
        now = datetime.utcnow()
        cutoff_raw = now - timedelta(days=owner_settings.retention_raw_messages_days)

        # delete message edits and mentions older than cutoff
        self.db.execute(
            delete(MessageEdit).where(MessageEdit.edited_at < cutoff_raw)
        )
        self.db.execute(
            delete(Mention).where(Mention.id.in_(
                self.db.query(Mention.id)
                .join(Message, Mention.message_id == Message.id)
                .filter(Message.sent_at < cutoff_raw)
            ))
        )
        # optionally delete or anonymize messages; for MVP we delete
        self.db.execute(delete(Message).where(Message.sent_at < cutoff_raw))

