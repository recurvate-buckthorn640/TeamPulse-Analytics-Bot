from src.workers.tasks_analytics import run_analytics_for_chat


class _FailingService(Exception):
    pass


def test_celery_task_retry_configuration_present() -> None:
    # we can't easily observe Celery retries without a broker here, but we can
    # assert that the task has retry-related attributes configured.
    task = run_analytics_for_chat
    assert getattr(task, "autoretry_for", None) is not None
    assert getattr(task, "retry_backoff", None) is not None
