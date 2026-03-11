from datetime import datetime, timedelta, timezone
from typing import Iterable, List, Mapping


class MentionEvent(Mapping[str, object]):
    """
    Simple structure representing a mention and the first reply from the mentioned user.
    """

    def __init__(
        self,
        *,
        chat_id: int,
        mentioned_user_id: int,
        mention_at: datetime,
        reply_at: datetime | None,
    ) -> None:
        self.chat_id = chat_id
        self.mentioned_user_id = mentioned_user_id
        self.mention_at = mention_at
        self.reply_at = reply_at

    def __getitem__(self, key: str) -> object:
        return getattr(self, key)

    def __iter__(self):
        return iter(("chat_id", "mentioned_user_id", "mention_at", "reply_at"))

    def __len__(self) -> int:
        return 4


def find_slow_mentions(
    events: Iterable[MentionEvent],
    *,
    threshold_hours: int = 4,
    now: datetime | None = None,
) -> List[MentionEvent]:
    """
    Detect slow mention responses.

    We treat a mention as slow when:
    - reply_at is not None and (reply_at - mention_at) >= threshold_hours, OR
    - reply_at is None and (now - mention_at) >= threshold_hours (still unanswered).
    """

    if now is None:
        now = datetime.now(tz=timezone.utc)

    threshold = timedelta(hours=threshold_hours)
    result: list[MentionEvent] = []

    for ev in events:
        if ev.reply_at is not None:
            delay = ev.reply_at - ev.mention_at
        else:
            delay = now - ev.mention_at

        if delay >= threshold:
            result.append(ev)

    return result

