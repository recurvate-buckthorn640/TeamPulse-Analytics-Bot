from typing import Any, Dict, Optional

import logging
from datetime import datetime, timezone

from sqlalchemy.orm import Session

from src.app.container import get_db_session
from src.db.repositories import (
    ChatRepository,
    UserRepository,
    MessageRepository,
    MessageEditRepository,
    MentionRepository,
)
from src.reporting.audit import write_audit_log
from src.telegram_bot.models import TelegramUpdate, MessageEntity, TelegramMessage


logger = logging.getLogger(__name__)


class IngestionService:
    @classmethod
    def handle_update(cls, payload: Dict[str, Any]) -> None:
        correlation_id = f"update-{payload.get('update_id')}"
        extra = {"correlation_id": correlation_id}

        update = TelegramUpdate.model_validate(payload)
        logger.info("Received update", extra={**extra, "update_id": update.update_id})

        message = update.message or update.edited_message
        if message is None:
            logger.info("Ignoring update without message", extra={**extra, "update_id": update.update_id})
            return

        db = get_db_session()
        try:
            chat_repo = ChatRepository(db)
            user_repo = UserRepository(db)
            message_repo = MessageRepository(db)
            edit_repo = MessageEditRepository(db)
            mention_repo = MentionRepository(db)

            chat = chat_repo.get_or_create(
                telegram_chat_id=message.chat.id,
                title=message.chat.title,
                chat_type=message.chat.type,
            )

            if message.from_ is None:
                logger.info("Ignoring message without sender", extra=extra)
                return

            display_name_parts = [
                part
                for part in [
                    message.from_.first_name,
                    message.from_.last_name,
                ]
                if part
            ]
            display_name = " ".join(display_name_parts) if display_name_parts else message.from_.username
            sender = user_repo.get_or_create(
                telegram_user_id=message.from_.id,
                username=message.from_.username,
                display_name=display_name,
            )

            sent_at = datetime.fromtimestamp(message.date, tz=timezone.utc)
            reply_to_id: Optional[int] = None
            if message.reply_to_message is not None:
                reply_to_id = message.reply_to_message.message_id

            idempotency_key = f"{message.chat.id}:{message.message_id}:{message.date}"

            stored_message = message_repo.upsert_message(
                chat=chat,
                sender=sender,
                telegram_message_id=message.message_id,
                sent_at=sent_at,
                text=message.text,
                reply_to_message_id=reply_to_id,
                idempotency_key=idempotency_key,
                raw_payload=payload,
            )

            if update.edited_message is not None:
                edit_repo.add_edit(
                    message=stored_message,
                    edited_at=sent_at,
                    text=message.text,
                    raw_payload=payload,
                )

            cls._persist_mentions(
                db=db,
                mention_repo=mention_repo,
                user_repo=user_repo,
                stored_message=stored_message,
                message=message,
            )

            write_audit_log(
                db,
                event_type="ingestion",
                actor_type="system",
                actor_id=None,
                context={"update_id": update.update_id, "chat_id": chat.id, "message_id": stored_message.id},
                message="Telegram update ingested",
            )

            db.commit()
            logger.info(
                "Update ingested successfully",
                extra={**extra, "update_id": update.update_id, "chat_id": chat.id, "message_id": stored_message.id},
            )
        except Exception:
            db.rollback()
            logger.exception("Failed to ingest update", extra=extra)
            raise
        finally:
            db.close()

    @classmethod
    def _persist_mentions(
        cls,
        *,
        db: Session,
        mention_repo: MentionRepository,
        user_repo: UserRepository,
        stored_message,
        message: TelegramMessage,
    ) -> None:
        if not message.entities or not message.text:
            return

        text = message.text
        for entity in message.entities:
            if entity.type != "mention":
                continue
            username = text[entity.offset + 1 : entity.offset + entity.length]
            if not username:
                continue
            mentioned_user = user_repo.get_or_create(
                telegram_user_id=0,  # placeholder when only username is known
                username=username,
                display_name=username,
            )
            mention_repo.add_mention(
                message=stored_message,
                mentioned_user=mentioned_user,
                offset=entity.offset,
                length=entity.length,
            )

