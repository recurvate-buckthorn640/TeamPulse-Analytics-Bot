from src.llm.schemas import (
    VerifierFacts,
    VerifierFactsSignal,
    VerifierSummaryMetrics,
    VerifierOutput,
    VerifierClaimVerdict,
    AnalystOverview,
    AnalystSection,
    AnalystClaim,
    AnalystOutput,
)
from src.llm.verifier import _postprocess_verifier_output


def test_verifier_marks_missing_claim_ids_unsupported() -> None:
    facts = VerifierFacts(
        signals=[
            VerifierFactsSignal(
                id="s1",
                type="open_loop",
                chat_id="1",
                thread_id="t1",
                severity="medium",
                evidence={},
            )
        ],
        summary_metrics=VerifierSummaryMetrics(total_open_loops=1),
    )

    analyst = AnalystOutput(
        overview=AnalystOverview(summary="ok"),
        sections=[
            AnalystSection(id="sec1", title="Open loops", description=None, signal_ids=["s1"])
        ],
        claims=[
            AnalystClaim(id="c1", text="claim", signal_ids=["s1"]),
        ],
    )

    output = VerifierOutput(
        report_id="r1",
        claims=[
            VerifierClaimVerdict(claim_id="c1", supported=True, reason="ok"),
            VerifierClaimVerdict(claim_id="missing", supported=True, reason=""),
        ],
        overall_supported=True,
    )

    processed = _postprocess_verifier_output(output, analyst)
    verdicts = {v.claim_id: v.supported for v in processed.claims}

    assert verdicts["c1"] is True
    assert verdicts["missing"] is False
    assert processed.overall_supported is False


def test_verifier_sets_overall_supported_false_when_no_claims() -> None:
    analyst = AnalystOutput(
        overview=AnalystOverview(summary="ok"),
        sections=[],
        claims=[],
    )
    output = VerifierOutput(report_id="r1", claims=[], overall_supported=True)

    processed = _postprocess_verifier_output(output, analyst)
    assert processed.overall_supported is False

