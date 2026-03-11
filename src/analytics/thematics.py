from collections import defaultdict
from typing import Dict, Iterable, List, Mapping

from src.db.models import Thread


def tag_threads_by_keywords(
    threads: Iterable[Thread],
    *,
    keyword_patterns: Mapping[str, Iterable[str]],
) -> Dict[int, List[str]]:
    """
    Basic thematic tagging for threads based on simple keyword patterns.

    Returns mapping: thread_id -> list of theme names.
    """

    tags: dict[int, list[str]] = defaultdict(list)

    for t in threads:
        text = (t.topic or "").lower()
        for theme, patterns in keyword_patterns.items():
            for p in patterns:
                if p.lower() in text:
                    tags[t.id].append(theme)
                    break

    return dict(tags)

