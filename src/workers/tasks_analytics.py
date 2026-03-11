from celery import shared_task
from sqlalchemy.orm import Session

from src.app.container import get_db_session
from src.services.analytics_service import AnalyticsService
from src.services.thread_service import ThreadService


@shared_task(name="analytics.update_threads_for_chat", autoretry_for=(Exception,), retry_backoff=True, retry_kwargs={"max_retries": 3})
def update_threads_for_chat(chat_id: int) -> None:
    db: Session = get_db_session()
    try:
        service = ThreadService(db)
        service.build_threads_for_chat(chat_id)
        db.commit()
    except Exception:
        db.rollback()
        raise
    finally:
        db.close()


@shared_task(name="analytics.run_for_chat", autoretry_for=(Exception,), retry_backoff=True, retry_kwargs={"max_retries": 3})
def run_analytics_for_chat(chat_id: int) -> None:
    db: Session = get_db_session()
    try:
        service = AnalyticsService(db)
        service.run_for_chat(chat_id)
        db.commit()
    except Exception:
        db.rollback()
        raise
    finally:
        db.close()

