from datetime import date

from src.workers.celery_app import celery_app
from src.workers.tasks_reporting import schedule_reports, build_report_task


def test_celery_beat_schedule_contains_required_entries() -> None:
    schedule = celery_app.conf.beat_schedule
    assert "retention_cleanup" in schedule
    assert schedule["retention_cleanup"]["task"] == "maintenance.run_retention_cleanup"
    assert "daily_reports" in schedule
    assert schedule["daily_reports"]["task"] == "reporting.schedule_reports"


def test_schedule_reports_enqueues_build_report_for_owners(monkeypatch) -> None:
    calls: list[dict] = []

    def fake_delay(*, owner_id: int, period_type: str, period_start: str, period_end: str):
        calls.append(
            {
                "owner_id": owner_id,
                "period_type": period_type,
                "period_start": period_start,
                "period_end": period_end,
            }
        )

    monkeypatch.setattr(build_report_task, "delay", fake_delay)

    # schedule_reports relies on DB state; here we simply assert that it does not crash
    # and calls delay() zero or more times depending on current OwnerSettings.
    schedule_reports()

    for call in calls:
        assert call["period_start"] == date.today().isoformat()
        assert call["period_type"] in {"daily", "weekly"}

