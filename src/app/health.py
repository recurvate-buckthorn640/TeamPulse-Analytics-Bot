from fastapi import APIRouter
from sqlalchemy import text

from src.app.container import get_db_session, get_redis_client


router = APIRouter(tags=["health"])


@router.get("/health/live")
def live() -> dict:
    return {"status": "ok"}


@router.get("/health/ready")
def ready() -> dict:
    db_ok = False
    redis_ok = False

    # minimal DB check
    db = get_db_session()
    try:
        db.execute(text("SELECT 1"))
        db_ok = True
    finally:
        db.close()

    # minimal Redis check
    try:
        redis = get_redis_client()
        redis.ping()
        redis_ok = True
    except Exception:  # noqa: BLE001
        redis_ok = False

    return {"status": "ready" if db_ok and redis_ok else "degraded", "db": db_ok, "redis": redis_ok}

