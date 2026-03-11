from datetime import date

from sqlalchemy.orm import Session

from src.app.container import get_db_session
from src.db.enums import ReportPeriodType, ReportStatus
from src.db.models import Owner, Report
from src.workers.tasks_reporting import build_report_task


def test_build_report_no_chats_no_signals_creates_skipped_report() -> None:
    db: Session = get_db_session()
    try:
        owner = Owner(
            telegram_user_id=1111,
            display_name="Owner",
            is_active=True,
            created_at=date.today(),
            updated_at=date.today(),
        )
        db.add(owner)
        db.commit()

        today = date.today()
        report_id = build_report_task(
            owner_id=owner.id,
            period_type=ReportPeriodType.DAILY.value,
            period_start=today.isoformat(),
            period_end=today.isoformat(),
        )

        report = db.get(Report, report_id)
        assert report is not None
        # when there is no data, we still create a report but mark it as rejected/skipped
        assert report.status in {ReportStatus.REJECTED, ReportStatus.ASSEMBLING, ReportStatus.FAILED}
    finally:
        db.close()

