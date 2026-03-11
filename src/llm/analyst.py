from __future__ import annotations

from typing import Any, Dict

from src.llm.client import LLMClient
from src.llm.schemas import AnalystInput, AnalystOutput


def run_analyst(client: LLMClient, payload: AnalystInput) -> AnalystOutput:
    """
    Call the analyst LLM stage and validate the structured response.
    """
    raw: Dict[str, Any] = client.complete_json("analyst", payload.model_dump())
    return AnalystOutput.model_validate(raw)

