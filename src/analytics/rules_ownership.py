from typing import Iterable, List

from src.db.models import Thread


def find_missing_owner_threads(threads: Iterable[Thread]) -> List[Thread]:
    """
    Detect task-like threads without a clear owner.

    Heuristic:
    - thread.is_task_like is True
    - owner_user_id is None
    """

    result: list[Thread] = []
    for t in threads:
        if t.is_task_like and t.owner_user_id is None:
            result.append(t)
    return result

