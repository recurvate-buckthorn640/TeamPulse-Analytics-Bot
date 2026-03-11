from __future__ import annotations

from datetime import date, datetime

from sqlalchemy import select
from sqlalchemy.orm import Session

from src.db.enums import ReportPeriodType, ReportStatus
from src.db.models import Owner, ProcessSignal, Report, ReportItem
from src.reporting.assembler import build_analyst_input, create_or_get_report
from src.reporting.audit import write_audit_log
from src.services.analytics_service import prioritize_signals


class ReportService:
    def __init__(self, db: Session) -> None:
        self.db = db

    def build_report(
        self,
        *,
        owner_id: int,
        period_type: ReportPeriodType,
        period_start: date,
        period_end: date,
    ) -> Report:
        owner = self.db.get(Owner, owner_id)
        if owner is None:
            raise ValueError(f"Owner {owner_id} not found")

        report = create_or_get_report(
            self.db,
            owner_id=owner_id,
            period_type=period_type,
            period_start=period_start,
            period_end=period_end,
        )
        report.status = ReportStatus.ASSEMBLING
        now = datetime.utcnow()
        report.updated_at = now

        # basic mapping: include all active signals for this owner into report items,
        # ordered by deterministic prioritization
        signals_stmt = select(ProcessSignal).where(ProcessSignal.owner_id == owner_id)
        signals = list(self.db.execute(signals_stmt).scalars())
        ordered_signals = prioritize_signals(signals)

        # clear existing items
        self.db.query(ReportItem).filter(ReportItem.report_id == report.id).delete()

        position = 0
        for s in ordered_signals:
            position += 1
            section = _section_for_type(s.type.value)
            item = ReportItem(
                report_id=report.id,
                process_signal_id=s.id,
                chat_id=s.chat_id,
                position=position,
                section=section,
            )
            self.db.add(item)

        write_audit_log(
            self.db,
            event_type="report_created",
            actor_type="system",
            actor_id=None,
            context={"report_id": report.id, "owner_id": owner_id},
            message="Report assembled from active process signals",
        )
        return report


def _section_for_type(signal_type: str) -> str:
    mapping = {
        "open_loop": "open_loops",
        "unresolved_thread": "unresolved",
        "missing_owner": "ownership",
        "missing_deadline": "deadlines",
        "slow_mention_response": "mentions",
        "theme_pattern": "themes",
    }
    return mapping.get(signal_type, "other")

