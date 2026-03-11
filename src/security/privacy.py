import logging
from typing import Mapping, Any


SENSITIVE_KEYS = {"token", "authorization", "api_key", "password"}


def redact_payload(payload: Mapping[str, Any]) -> Mapping[str, Any]:
    redacted: dict[str, Any] = {}
    for key, value in payload.items():
        if key.lower() in SENSITIVE_KEYS:
            redacted[key] = "***redacted***"
        else:
            redacted[key] = value
    return redacted


def get_logger(name: str) -> logging.Logger:
    logger = logging.getLogger(name)
    return logger

