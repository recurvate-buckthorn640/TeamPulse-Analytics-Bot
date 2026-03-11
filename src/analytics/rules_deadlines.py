from datetime import datetime
from typing import Iterable, List

from src.db.models import Thread


def find_missing_deadline_threads(threads: Iterable[Thread], *, now: datetime | None = None) -> List[Thread]:
    """
    Detect task-like threads with an owner but no deadline.

    Heuristic:
    - thread.is_task_like is True
    - owner_user_id is not None
    - deadline_at is None
    """

    _ = now  # reserved for future refinements (e.g., only active threads)

    result: list[Thread] = []
    for t in threads:
        if t.is_task_like and t.owner_user_id is not None and t.deadline_at is None:
            result.append(t)
    return result

