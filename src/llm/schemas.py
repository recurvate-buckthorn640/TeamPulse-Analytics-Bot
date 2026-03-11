from __future__ import annotations

from datetime import datetime
from typing import List, Optional

from pydantic import BaseModel, Field, RootModel, field_validator, model_validator

from src.db.enums import (
    LLMRunStage,
    LLMRunStatus,
    ReportPeriodType,
)


class AnalystOwner(BaseModel):
    id: str
    display_name: str


class AnalystPeriod(BaseModel):
    type: ReportPeriodType
    start: datetime
    end: datetime


class AnalystChat(BaseModel):
    id: str
    title: str


class AnalystEvidence(BaseModel):
    root_message_id: Optional[str] = None
    message_ids: List[str] = Field(default_factory=list)
    # keep structure flexible but enforce basic shape
    time_range: Optional[dict] = None
    metrics: dict = Field(default_factory=dict)


class AnalystSignal(BaseModel):
    id: str
    chat_id: str
    thread_id: str
    type: str
    severity: str
    theme: Optional[str] = None
    evidence: AnalystEvidence


class AnalystOverview(BaseModel):
    summary: str


class AnalystSection(BaseModel):
    id: str
    title: str
    description: Optional[str] = None
    signal_ids: List[str]


class AnalystClaim(BaseModel):
    id: str
    text: str
    signal_ids: List[str]
    recommendation: bool = False


class AnalystInput(BaseModel):
    report_id: str
    owner: AnalystOwner
    period: AnalystPeriod
    chats: List[AnalystChat]
    signals: List[AnalystSignal]


class AnalystOutput(BaseModel):
    overview: AnalystOverview
    sections: List[AnalystSection]
    claims: List[AnalystClaim]

    @model_validator(mode="after")
    def _validate_claim_signal_links(self) -> "AnalystOutput":
        signal_ids = {s.id for s in getattr(self, "signals", [])}  # type: ignore[attr-defined]
        # signals are not part of this model, but in end-to-end validation
        # we still want at least non-empty signal_ids per-claim
        for claim in self.claims:
            if not claim.signal_ids:
                raise ValueError("Analyst claim must reference at least one signal id")
        _ = signal_ids
        return self


class VerifierFactsSignal(BaseModel):
    id: str
    type: str
    chat_id: str
    thread_id: str
    severity: str
    evidence: dict


class VerifierSummaryMetrics(BaseModel):
    total_open_loops: int = 0
    total_unresolved_threads: int = 0
    total_missing_owners: int = 0
    total_missing_deadlines: int = 0
    total_slow_mentions: int = 0


class VerifierFacts(BaseModel):
    signals: List[VerifierFactsSignal]
    summary_metrics: VerifierSummaryMetrics = Field(
        default_factory=VerifierSummaryMetrics
    )


class VerifierClaimVerdict(BaseModel):
    claim_id: str
    supported: bool
    reason: str


class VerifierOutput(BaseModel):
    report_id: str
    claims: List[VerifierClaimVerdict]
    overall_supported: bool
    notes: Optional[str] = None

    @model_validator(mode="after")
    def _ensure_overall_supported_consistency(self) -> "VerifierOutput":
        if any(not c.supported for c in self.claims) and self.overall_supported:
            raise ValueError(
                "overall_supported cannot be true when some claims are unsupported"
            )
        return self


class FinalizerSupportedClaim(BaseModel):
    id: str
    text: str
    signal_ids: List[str]


class FinalizerOwner(BaseModel):
    display_name: str


class FinalizerPeriod(BaseModel):
    type: ReportPeriodType
    label: str


class FinalizerInput(BaseModel):
    report_id: str
    owner: FinalizerOwner
    period: FinalizerPeriod
    supported_claims: List[FinalizerSupportedClaim]


class FinalizerOutput(BaseModel):
    report_id: str
    text: str


class LLMRunEnvelope(BaseModel):
    """
    Shared structure for persisting LLM runs.
    """

    report_id: int
    stage: LLMRunStage
    status: LLMRunStatus
    request_payload: dict
    response_payload: Optional[dict] = None
    error_message: Optional[str] = None

