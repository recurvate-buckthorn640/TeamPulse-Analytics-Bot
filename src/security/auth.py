from typing import Iterable

from fastapi import HTTPException, status

from src.app.config import settings


def ensure_owner_allowed(telegram_user_id: int) -> None:
    allowed_ids: Iterable[int] = settings.owner_telegram_user_ids
    if telegram_user_id not in allowed_ids:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Not allowed to access reports",
        )

