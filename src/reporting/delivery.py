from __future__ import annotations

import asyncio
from typing import Any

from sqlalchemy.orm import Session

from src.db.enums import ReportStatus
from src.db.models import Owner, Report
from src.reporting.audit import write_audit_log
from src.telegram_bot.client import get_bot


async def _send_telegram_message(telegram_user_id: int, text: str) -> None:
    bot = get_bot()
    await bot.send_message(chat_id=telegram_user_id, text=text)


def deliver_report(
    db: Session,
    *,
    report: Report,
    owner: Owner,
    text: str,
) -> None:
    """
    Send the final report text as a private Telegram message to the owner.
    """
    asyncio.run(_send_telegram_message(owner.telegram_user_id, text))

    report.status = ReportStatus.DELIVERED
    from datetime import datetime

    report.delivered_at = datetime.utcnow()

    write_audit_log(
        db,
        event_type="report_delivery",
        actor_type="system",
        actor_id=None,
        context={"report_id": report.id, "owner_id": owner.id},
        message="Report delivered to owner via Telegram",
    )

