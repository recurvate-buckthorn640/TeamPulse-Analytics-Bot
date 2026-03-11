from datetime import datetime, timedelta, timezone
from typing import Iterable, List

from src.analytics.threading import ThreadSummary


def find_unresolved_threads(
    threads: Iterable[ThreadSummary],
    *,
    now: datetime | None = None,
    min_length: int = 5,
    min_duration_minutes: int = 30,
) -> List[ThreadSummary]:
    """
    Identify long-running threads that appear unresolved.

    For this first implementation we use simple heuristics:
    - message_count >= min_length
    - (last_activity_at - started_at) in minutes >= min_duration_minutes
    """

    if now is None:
        now = datetime.now(tz=timezone.utc)

    _ = now  # reserved for future use (e.g., staleness)
    min_duration = timedelta(minutes=min_duration_minutes)
    result: list[ThreadSummary] = []

    for t in threads:
        if t.message_count < min_length:
            continue
        duration = t.last_activity_at - t.started_at
        if duration >= min_duration:
            result.append(t)

    return result

