from datetime import datetime

from src.analytics.rules_deadlines import find_missing_deadline_threads
from src.analytics.rules_ownership import find_missing_owner_threads
from src.db.models import Thread


def _thread(
    *,
    thread_id: int,
    is_task_like: bool,
    owner_user_id: int | None,
    deadline_at: datetime | None,
) -> Thread:
    t = Thread(
        id=thread_id,
        chat_id=1,
        root_message_id=1,
        topic=None,
        started_at=datetime.utcnow(),
        last_activity_at=datetime.utcnow(),
        message_count=1,
        status=None,  # type: ignore[arg-type]
        is_task_like=is_task_like,
        has_resolution_marker=False,
        owner_user_id=owner_user_id,
        deadline_at=deadline_at,
    )
    return t


def test_missing_owner_threads_detected() -> None:
    t1 = _thread(thread_id=1, is_task_like=True, owner_user_id=None, deadline_at=None)
    t2 = _thread(thread_id=2, is_task_like=False, owner_user_id=None, deadline_at=None)
    t3 = _thread(thread_id=3, is_task_like=True, owner_user_id=10, deadline_at=None)

    result = find_missing_owner_threads([t1, t2, t3])

    ids = {t.id for t in result}
    assert ids == {1}


def test_missing_deadline_threads_detected() -> None:
    now = datetime.utcnow()
    t1 = _thread(thread_id=1, is_task_like=True, owner_user_id=10, deadline_at=None)
    t2 = _thread(thread_id=2, is_task_like=True, owner_user_id=None, deadline_at=None)
    t3 = _thread(thread_id=3, is_task_like=True, owner_user_id=10, deadline_at=now)

    result = find_missing_deadline_threads([t1, t2, t3], now=now)

    ids = {t.id for t in result}
    assert ids == {1}

