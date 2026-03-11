from datetime import datetime
from typing import Any, Dict, Optional

from sqlalchemy import select
from sqlalchemy.orm import Session

from src.db.models import Chat, User, Message, MessageEdit, Mention


class ChatRepository:
    def __init__(self, db: Session) -> None:
        self.db = db

    def get_or_create(self, telegram_chat_id: int, title: Optional[str], chat_type: str) -> Chat:
        stmt = select(Chat).where(Chat.telegram_chat_id == telegram_chat_id)
        chat = self.db.execute(stmt).scalar_one_or_none()
        now = datetime.utcnow()
        if chat is None:
            chat = Chat(
                telegram_chat_id=telegram_chat_id,
                title=title,
                type=chat_type,
                is_active=True,
                created_at=now,
                updated_at=now,
            )
            self.db.add(chat)
            self.db.flush()
        return chat


class UserRepository:
    def __init__(self, db: Session) -> None:
        self.db = db

    def get_or_create(
        self,
        telegram_user_id: int,
        username: Optional[str],
        display_name: Optional[str],
    ) -> User:
        stmt = select(User).where(User.telegram_user_id == telegram_user_id)
        user = self.db.execute(stmt).scalar_one_or_none()
        now = datetime.utcnow()
        if user is None:
            user = User(
                telegram_user_id=telegram_user_id,
                username=username,
                display_name=display_name,
                created_at=now,
                updated_at=now,
            )
            self.db.add(user)
            self.db.flush()
        return user


class MessageRepository:
    def __init__(self, db: Session) -> None:
        self.db = db

    def upsert_message(
        self,
        chat: Chat,
        sender: User,
        telegram_message_id: int,
        sent_at: datetime,
        text: Optional[str],
        reply_to_message_id: Optional[int],
        idempotency_key: str,
        raw_payload: Dict[str, Any],
    ) -> Message:
        stmt = select(Message).where(Message.idempotency_key == idempotency_key)
        message = self.db.execute(stmt).scalar_one_or_none()
        now = datetime.utcnow()
        if message is None:
            message = Message(
                telegram_message_id=telegram_message_id,
                chat_id=chat.id,
                sender_id=sender.id,
                sent_at=sent_at,
                edited_at=None,
                text=text,
                reply_to_message_id=reply_to_message_id,
                is_deleted=False,
                idempotency_key=idempotency_key,
                raw_payload=raw_payload,
                created_at=now,
                updated_at=now,
            )
            self.db.add(message)
        else:
            message.text = text
            message.edited_at = sent_at
            message.raw_payload = raw_payload
            message.updated_at = now
        self.db.flush()
        return message


class MessageEditRepository:
    def __init__(self, db: Session) -> None:
        self.db = db

    def add_edit(self, message: Message, edited_at: datetime, text: Optional[str], raw_payload: Dict[str, Any]) -> MessageEdit:
        edit = MessageEdit(
            message_id=message.id,
            edited_at=edited_at,
            text=text,
            raw_payload=raw_payload,
        )
        self.db.add(edit)
        self.db.flush()
        return edit


class MentionRepository:
    def __init__(self, db: Session) -> None:
        self.db = db

    def add_mention(self, message: Message, mentioned_user: User, offset: Optional[int], length: Optional[int]) -> Mention:
        mention = Mention(
            message_id=message.id,
            mentioned_user_id=mentioned_user.id,
            offset=offset,
            length=length,
        )
        self.db.add(mention)
        self.db.flush()
        return mention

