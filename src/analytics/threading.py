from collections import defaultdict
from dataclasses import dataclass
from datetime import datetime
from typing import Iterable, List, Optional


@dataclass(frozen=True)
class ThreadMessage:
    """
    Lightweight message view used for thread construction.

    This stays independent of ORM models so it can be exercised in unit tests
    without a database.
    """

    message_id: int
    chat_id: int
    sent_at: datetime
    reply_to_message_id: Optional[int]


@dataclass
class ThreadSummary:
    """
    Minimal thread summary used by analytics rules.
    """

    root_message_id: int
    chat_id: int
    started_at: datetime
    last_activity_at: datetime
    message_count: int


def build_threads(messages: Iterable[ThreadMessage]) -> List[ThreadSummary]:
    """
    Build simple thread summaries from a set of messages.

    Rules:
    - A thread is anchored at a root message (reply_to_message_id is None).
    - Replies form a tree; for now we treat any reply chain as belonging to the
      root message's thread.
    - Messages are assumed to belong to a single chat; if multiple chats are
      present they are threaded independently.
    """

    by_id: dict[int, ThreadMessage] = {}
    children: defaultdict[int, list[ThreadMessage]] = defaultdict(list)

    root_candidates: list[ThreadMessage] = []

    for m in messages:
        by_id[m.message_id] = m
        if m.reply_to_message_id is None:
            root_candidates.append(m)
        else:
            children[m.reply_to_message_id].append(m)

    threads: list[ThreadSummary] = []

    for root in sorted(root_candidates, key=lambda x: x.sent_at):
        stack = [root]
        all_msgs: list[ThreadMessage] = []

        while stack:
            current = stack.pop()
            all_msgs.append(current)
            for child in children.get(current.message_id, []):
                stack.append(child)

        all_msgs.sort(key=lambda x: x.sent_at)

        started_at = all_msgs[0].sent_at
        last_activity_at = all_msgs[-1].sent_at

        threads.append(
            ThreadSummary(
                root_message_id=root.message_id,
                chat_id=root.chat_id,
                started_at=started_at,
                last_activity_at=last_activity_at,
                message_count=len(all_msgs),
            )
        )

    return threads

