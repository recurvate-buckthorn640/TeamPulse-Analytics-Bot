from datetime import datetime, timedelta, timezone

from src.analytics.rules_unresolved import find_unresolved_threads
from src.analytics.threading import ThreadSummary


def _ts(seconds: int) -> datetime:
    return datetime(2024, 1, 1, tzinfo=timezone.utc) + timedelta(seconds=seconds)


def test_short_thread_not_marked_unresolved() -> None:
    thread = ThreadSummary(
        root_message_id=1,
        chat_id=100,
        started_at=_ts(0),
        last_activity_at=_ts(60),
        message_count=3,
    )

    result = find_unresolved_threads([thread], min_length=5, min_duration_minutes=30)

    assert result == []


def test_long_enough_and_long_duration_marked_unresolved() -> None:
    thread = ThreadSummary(
        root_message_id=1,
        chat_id=100,
        started_at=_ts(0),
        last_activity_at=_ts(60 * 60),  # 60 minutes
        message_count=10,
    )

    result = find_unresolved_threads([thread], min_length=5, min_duration_minutes=30)

    assert len(result) == 1
    assert result[0].root_message_id == 1


def test_multiple_threads_filter_by_length_and_duration() -> None:
    t1 = ThreadSummary(
        root_message_id=1,
        chat_id=100,
        started_at=_ts(0),
        last_activity_at=_ts(60 * 60),
        message_count=10,
    )
    t2 = ThreadSummary(
        root_message_id=2,
        chat_id=100,
        started_at=_ts(0),
        last_activity_at=_ts(10 * 60),
        message_count=10,
    )
    t3 = ThreadSummary(
        root_message_id=3,
        chat_id=100,
        started_at=_ts(0),
        last_activity_at=_ts(60 * 60),
        message_count=3,
    )

    result = find_unresolved_threads([t1, t2, t3], min_length=5, min_duration_minutes=30)

    ids = {t.root_message_id for t in result}
    assert ids == {1}

