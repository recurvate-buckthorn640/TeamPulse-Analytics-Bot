from datetime import datetime, timedelta, timezone

from src.analytics.rules_mentions import MentionEvent, find_slow_mentions


def _ts(seconds: int) -> datetime:
    return datetime(2024, 1, 1, tzinfo=timezone.utc) + timedelta(seconds=seconds)


def test_fast_reply_not_flagged() -> None:
    ev = MentionEvent(
        chat_id=1,
        mentioned_user_id=10,
        mention_at=_ts(0),
        reply_at=_ts(60 * 60),  # 1 hour
    )

    result = find_slow_mentions([ev], threshold_hours=4, now=_ts(0))

    assert result == []


def test_slow_reply_flagged() -> None:
    ev = MentionEvent(
        chat_id=1,
        mentioned_user_id=10,
        mention_at=_ts(0),
        reply_at=_ts(5 * 60 * 60),  # 5 hours
    )

    result = find_slow_mentions([ev], threshold_hours=4, now=_ts(0))

    assert len(result) == 1
    assert result[0].mentioned_user_id == 10


def test_unanswered_old_mention_flagged() -> None:
    ev = MentionEvent(
        chat_id=1,
        mentioned_user_id=10,
        mention_at=_ts(0),
        reply_at=None,
    )

    result = find_slow_mentions([ev], threshold_hours=4, now=_ts(5 * 60 * 60))

    assert len(result) == 1
    assert result[0].reply_at is None

