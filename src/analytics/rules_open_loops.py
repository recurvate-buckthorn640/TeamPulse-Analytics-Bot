from datetime import datetime, timedelta, timezone
from typing import Iterable, List

from src.analytics.threading import ThreadSummary


class OpenLoopCandidate(ThreadSummary):
    """
    Thread summary extended with flag whether it should be treated as open loop.
    """

    is_open_loop: bool  # type: ignore[assignment]


def find_open_loops(
    threads: Iterable[ThreadSummary],
    *,
    now: datetime | None = None,
    threshold_hours: int = 24,
) -> List[ThreadSummary]:
    """
    Return threads that qualify as open loops.

    For this first implementation, a thread is considered an open loop when:
    - It has at least one message (message_count > 0), and
    - The time since last_activity_at is greater than or equal to threshold_hours.
    """

    if now is None:
        now = datetime.now(tz=timezone.utc)

    threshold = timedelta(hours=threshold_hours)
    open_loops: list[ThreadSummary] = []

    for t in threads:
        if t.message_count == 0:
            continue
        idle_for = now - t.last_activity_at
        if idle_for >= threshold:
            open_loops.append(t)

    return open_loops

