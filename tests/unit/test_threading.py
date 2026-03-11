from datetime import datetime, timedelta, timezone

from src.analytics.threading import ThreadMessage, build_threads


def _ts(seconds: int) -> datetime:
    return datetime(2024, 1, 1, tzinfo=timezone.utc) + timedelta(seconds=seconds)


def test_single_message_forms_single_thread() -> None:
    msg = ThreadMessage(
        message_id=1,
        chat_id=100,
        sent_at=_ts(0),
        reply_to_message_id=None,
    )

    threads = build_threads([msg])

    assert len(threads) == 1
    t = threads[0]
    assert t.root_message_id == 1
    assert t.chat_id == 100
    assert t.message_count == 1
    assert t.started_at == _ts(0)
    assert t.last_activity_at == _ts(0)


def test_reply_chain_belongs_to_root_thread() -> None:
    root = ThreadMessage(
        message_id=1,
        chat_id=100,
        sent_at=_ts(0),
        reply_to_message_id=None,
    )
    reply1 = ThreadMessage(
        message_id=2,
        chat_id=100,
        sent_at=_ts(10),
        reply_to_message_id=1,
    )
    reply2 = ThreadMessage(
        message_id=3,
        chat_id=100,
        sent_at=_ts(20),
        reply_to_message_id=2,
    )

    threads = build_threads([root, reply1, reply2])

    assert len(threads) == 1
    t = threads[0]
    assert t.root_message_id == 1
    assert t.message_count == 3
    assert t.started_at == _ts(0)
    assert t.last_activity_at == _ts(20)


def test_multiple_roots_create_multiple_threads() -> None:
    root1 = ThreadMessage(
        message_id=1,
        chat_id=100,
        sent_at=_ts(0),
        reply_to_message_id=None,
    )
    root2 = ThreadMessage(
        message_id=10,
        chat_id=100,
        sent_at=_ts(5),
        reply_to_message_id=None,
    )
    reply = ThreadMessage(
        message_id=11,
        chat_id=100,
        sent_at=_ts(6),
        reply_to_message_id=10,
    )

    threads = sorted(build_threads([root1, root2, reply]), key=lambda t: t.root_message_id)

    assert len(threads) == 2

    t1, t2 = threads
    assert t1.root_message_id == 1
    assert t1.message_count == 1

    assert t2.root_message_id == 10
    assert t2.message_count == 2

