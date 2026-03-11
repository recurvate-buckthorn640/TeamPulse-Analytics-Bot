from datetime import datetime, timedelta, timezone

from src.analytics.rules_open_loops import find_open_loops
from src.analytics.threading import ThreadSummary


def _ts(seconds: int) -> datetime:
    return datetime(2024, 1, 1, tzinfo=timezone.utc) + timedelta(seconds=seconds)


def test_thread_not_old_enough_is_not_open_loop() -> None:
    thread = ThreadSummary(
        root_message_id=1,
        chat_id=100,
        started_at=_ts(0),
        last_activity_at=_ts(60),
        message_count=3,
    )

    now = _ts(60 + 60 * 60)  # 1 hour later
    result = find_open_loops([thread], now=now, threshold_hours=24)

    assert result == []


def test_thread_past_threshold_is_open_loop() -> None:
    thread = ThreadSummary(
        root_message_id=1,
        chat_id=100,
        started_at=_ts(0),
        last_activity_at=_ts(0),
        message_count=2,
    )

    now = _ts(24 * 60 * 60)  # 24 hours later
    result = find_open_loops([thread], now=now, threshold_hours=24)

    assert len(result) == 1
    assert result[0].root_message_id == 1


def test_multiple_threads_filter_correctly() -> None:
    t1 = ThreadSummary(
        root_message_id=1,
        chat_id=100,
        started_at=_ts(0),
        last_activity_at=_ts(0),
        message_count=2,
    )
    t2 = ThreadSummary(
        root_message_id=2,
        chat_id=100,
        started_at=_ts(10),
        last_activity_at=_ts(10),
        message_count=5,
    )

    now = _ts(24 * 60 * 60)
    result = find_open_loops([t1, t2], now=now, threshold_hours=24)

    ids = {t.root_message_id for t in result}
    assert ids == {1, 2}

