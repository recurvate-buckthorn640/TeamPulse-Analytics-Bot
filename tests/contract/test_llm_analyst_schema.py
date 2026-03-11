from datetime import datetime, timezone

import pytest

from src.llm.schemas import (
    AnalystOwner,
    AnalystPeriod,
    AnalystChat,
    AnalystEvidence,
    AnalystSignal,
    AnalystInput,
    AnalystOverview,
    AnalystSection,
    AnalystClaim,
    AnalystOutput,
)
from src.db.enums import ReportPeriodType


def _dt() -> datetime:
    return datetime(2024, 1, 1, tzinfo=timezone.utc)


def test_analyst_input_requires_core_fields() -> None:
    owner = AnalystOwner(id="1", display_name="Owner")
    period = AnalystPeriod(type=ReportPeriodType.DAILY, start=_dt(), end=_dt())
    chat = AnalystChat(id="10", title="Team")
    ev = AnalystEvidence(root_message_id="1")
    signal = AnalystSignal(
        id="s1",
        chat_id="10",
        thread_id="t1",
        type="open_loop",
        severity="medium",
        theme=None,
        evidence=ev,
    )

    payload = AnalystInput(
        report_id="r1",
        owner=owner,
        period=period,
        chats=[chat],
        signals=[signal],
    )

    assert payload.report_id == "r1"
    assert payload.signals[0].id == "s1"


def test_analyst_output_claim_must_reference_signals() -> None:
    overview = AnalystOverview(summary="ok")
    section = AnalystSection(id="sec1", title="Open loops", description=None, signal_ids=["s1"])
    claim = AnalystClaim(id="c1", text="something", signal_ids=["s1"])

    # this should pass because claim has at least one signal id
    out = AnalystOutput(overview=overview, sections=[section], claims=[claim])
    assert out.claims[0].signal_ids == ["s1"]

    # missing signal_ids should fail validation
    with pytest.raises(ValueError):
        AnalystOutput(overview=overview, sections=[section], claims=[AnalystClaim(id="c2", text="x", signal_ids=[])])

