from __future__ import annotations

from typing import Iterable, Set

from src.llm.client import LLMClient
from src.llm.schemas import (
    AnalystOutput,
    VerifierFacts,
    VerifierOutput,
)


def run_verifier(
    client: LLMClient,
    facts: VerifierFacts,
    analyst_output: AnalystOutput,
) -> VerifierOutput:
    """
    Call the verifier LLM stage and then enforce basic consistency rules.
    """
    raw = client.complete_json(
        "verifier",
        {
            "facts": facts.model_dump(),
            "analyst_output": analyst_output.model_dump(),
        },
    )
    output = VerifierOutput.model_validate(raw)
    return _postprocess_verifier_output(output, analyst_output)


def _postprocess_verifier_output(
    output: VerifierOutput,
    analyst_output: AnalystOutput,
) -> VerifierOutput:
    """
    Ensure that all verdicts reference existing analyst claims and
    derive overall_supported accordingly.
    """
    analyst_claim_ids: Set[str] = {c.id for c in analyst_output.claims}

    unsupported_due_to_missing_claim = False
    for verdict in output.claims:
        if verdict.claim_id not in analyst_claim_ids:
            verdict.supported = False
            unsupported_due_to_missing_claim = True

    if unsupported_due_to_missing_claim:
        output.overall_supported = False

    if not output.claims:
        output.overall_supported = False

    return output

