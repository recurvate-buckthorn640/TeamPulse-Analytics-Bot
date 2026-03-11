from celery import Celery

from src.app.config import settings


celery_app = Celery(
    "team_communication_analytics",
    broker=str(settings.redis_url),
    backend=str(settings.redis_url),
)

celery_app.conf.update(
    task_default_queue="default",
    task_acks_late=True,
    beat_schedule={
        "daily_reports": {
            "task": "reporting.schedule_reports",
            "schedule": 60 * 60 * 24,
            "args": (),
        },
        "retention_cleanup": {
            "task": "maintenance.run_retention_cleanup",
            "schedule": 60 * 60 * 24,
        },
    },
)

