from __future__ import annotations

from typing import Any, Dict

from src.llm.client import LLMClient
from src.llm.schemas import FinalizerInput, FinalizerOutput


def run_finalizer(client: LLMClient, payload: FinalizerInput) -> FinalizerOutput:
    """
    Call the finalizer LLM stage and validate the response.
    """
    raw: Dict[str, Any] = client.complete_json("finalizer", payload.model_dump())
    return FinalizerOutput.model_validate(raw)

