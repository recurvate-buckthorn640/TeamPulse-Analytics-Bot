from __future__ import annotations

from datetime import datetime, date, timezone
from typing import List

from sqlalchemy import select
from sqlalchemy.orm import Session

from src.db.enums import ProcessSignalStatus, ReportPeriodType
from src.db.models import Chat, Owner, ProcessSignal, Report, ReportItem
from src.llm.schemas import (
    AnalystChat,
    AnalystInput,
    AnalystOwner,
    AnalystPeriod,
    AnalystSignal,
    AnalystEvidence,
)


def build_analyst_input(db: Session, report: Report) -> AnalystInput:
    """
    Assemble deterministic facts and metadata into an AnalystInput payload.
    """
    owner = db.get(Owner, report.owner_id)
    assert owner is not None

    chats_stmt = select(Chat).where(Chat.owner_id == owner.id, Chat.is_active.is_(True))
    chats = list(db.execute(chats_stmt).scalars())

    signals_stmt = select(ProcessSignal).where(
        ProcessSignal.owner_id == owner.id,
        ProcessSignal.status == ProcessSignalStatus.ACTIVE,
    )
    signals = list(db.execute(signals_stmt).scalars())

    analyst_chats: List[AnalystChat] = [
        AnalystChat(id=str(c.id), title=c.title or f"Chat {c.telegram_chat_id}")
        for c in chats
    ]

    analyst_signals: List[AnalystSignal] = []
    for s in signals:
        evidence = AnalystEvidence(**(s.evidence or {}))
        analyst_signals.append(
            AnalystSignal(
                id=str(s.id),
                chat_id=str(s.chat_id),
                thread_id=str(s.thread_id),
                type=s.type.value,
                severity=s.severity.value,
                theme=(s.metadata or {}).get("theme"),
                evidence=evidence,
            )
        )

    # treat period_start/end (dates) as midnight UTC ranges
    start_dt = datetime.combine(report.period_start, datetime.min.time()).replace(
        tzinfo=timezone.utc
    )
    end_dt = datetime.combine(report.period_end, datetime.max.time()).replace(
        tzinfo=timezone.utc
    )

    period = AnalystPeriod(
        type=report.period_type,
        start=start_dt,
        end=end_dt,
    )

    return AnalystInput(
        report_id=str(report.id),
        owner=AnalystOwner(id=str(owner.id), display_name=owner.display_name or ""),
        period=period,
        chats=analyst_chats,
        signals=analyst_signals,
    )


def create_or_get_report(
    db: Session,
    *,
    owner_id: int,
    period_type: ReportPeriodType,
    period_start: date,
    period_end: date,
) -> Report:
    """
    Idempotently create a report row for the given owner and period.
    """
    stmt = select(Report).where(
        Report.owner_id == owner_id,
        Report.period_type == period_type,
        Report.period_start == period_start,
        Report.period_end == period_end,
    )
    existing = db.execute(stmt).scalar_one_or_none()
    now = datetime.utcnow()
    if existing is not None:
        existing.updated_at = now
        return existing

    report = Report(
        owner_id=owner_id,
        period_type=period_type,
        period_start=period_start,
        period_end=period_end,
        status=None,  # set by service
        created_at=now,
        updated_at=now,
        delivered_at=None,
        rejection_reason=None,
    )
    db.add(report)
    db.flush()
    return report

