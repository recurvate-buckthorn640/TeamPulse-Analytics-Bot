from datetime import datetime
from typing import Iterable, List

from sqlalchemy import select
from sqlalchemy.orm import Session

from src.analytics.threading import ThreadMessage, ThreadSummary, build_threads
from src.db.models import Message, Thread
from src.db.enums import ThreadStatus


class ThreadService:
    def __init__(self, db: Session) -> None:
        self.db = db

    def build_threads_for_chat(self, chat_id: int) -> List[Thread]:
        """
        Rebuild threads for a given chat from messages.

        This is a simple implementation suitable for analytics runs over
        a limited dataset; production backfills can refine this further.
        """

        stmt = (
            select(Message)
            .where(Message.chat_id == chat_id, Message.is_deleted.is_(False))
            .order_by(Message.sent_at)
        )
        messages: list[Message] = list(self.db.execute(stmt).scalars())

        thread_messages: list[ThreadMessage] = [
            ThreadMessage(
                message_id=m.id,
                chat_id=m.chat_id,
                sent_at=m.sent_at,
                reply_to_message_id=m.reply_to_message_id,
            )
            for m in messages
        ]

        summaries: list[ThreadSummary] = build_threads(thread_messages)

        # naive: delete existing threads for chat and rebuild
        self.db.query(Thread).filter(Thread.chat_id == chat_id).delete()

        now = datetime.utcnow()
        created_threads: list[Thread] = []
        for s in summaries:
            t = Thread(
                chat_id=s.chat_id,
                root_message_id=s.root_message_id,
                topic=None,
                started_at=s.started_at,
                last_activity_at=s.last_activity_at,
                message_count=s.message_count,
                status=ThreadStatus.ACTIVE,
                is_task_like=False,
                has_resolution_marker=False,
                owner_user_id=None,
                deadline_at=None,
            )
            created_threads.append(t)
            self.db.add(t)

        self.db.flush()
        return created_threads

