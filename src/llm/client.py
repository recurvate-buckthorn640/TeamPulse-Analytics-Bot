from __future__ import annotations

from typing import Any, Dict

import httpx

from src.app.config import settings
from src.app.container import get_http_client_for_llm


class LLMClient:
    """
    Minimal OpenAI-compatible JSON client wrapper.

    In tests this client is typically monkeypatched.
    """

    def __init__(self, *, base_url: str = "https://api.openai.com/v1") -> None:
        self._base_url = base_url.rstrip("/")

    def complete_json(self, model: str, payload: Dict[str, Any]) -> Dict[str, Any]:
        """
        Call the LLM and expect a JSON response.

        This implementation is intentionally simple and is designed
        to be safe to mock in tests.
        """
        if settings.llm_api_key is None:
            raise RuntimeError("LLM_API_KEY is not configured")

        url = f"{self._base_url}/chat/completions"
        headers = {
            "Authorization": f"Bearer {settings.llm_api_key}",
            "Content-Type": "application/json",
        }

        body: Dict[str, Any] = {
            "model": model,
            "messages": [
                {
                    "role": "user",
                    "content": "Respond strictly with a JSON object.",
                }
            ],
            "response_format": {"type": "json_object"},
            "temperature": 0,
            "extra": payload,
        }

        client = get_http_client_for_llm()
        resp = client.post(url, headers=headers, json=body)
        resp.raise_for_status()
        data = resp.json()

        # For simplicity we assume the model returns JSON in the first choice
        try:
            content = data["choices"][0]["message"]["content"]
        except (KeyError, IndexError) as exc:
            raise RuntimeError("Unexpected LLM response structure") from exc

        if isinstance(content, dict):
            return content

        # If the content is a JSON string, httpx/json will parse it in tests
        import json

        return json.loads(content)

