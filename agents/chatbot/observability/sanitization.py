"""Sanitizacao de payloads antes do envio ao backend de observabilidade."""

from __future__ import annotations

from collections.abc import Mapping, Sequence
import math
import re
from typing import Any

from .types import ObservationPayload, SanitizedValue

_MAX_DEPTH = 3
_MAX_ITEMS = 10
_MAX_STRING_LENGTH = 600
_SENSITIVE_TOKEN = "[REDACTED]"
_SENSITIVE_KEYWORDS = (
    "api_key",
    "apikey",
    "auth",
    "authorization",
    "password",
    "secret",
    "token",
)


def sanitize_mapping(
    mapping: Mapping[str, Any] | None,
    *,
    allowed_keys: Sequence[str] | None = None,
) -> ObservationPayload:
    if not mapping:
        return {}

    allowed = set(allowed_keys or ())
    payload: ObservationPayload = {}
    for raw_key, raw_value in mapping.items():
        key = str(raw_key)
        if allowed and key not in allowed:
            continue
        payload[key] = sanitize_value(raw_value, key=key)
    return payload


def sanitize_value(
    value: Any,
    *,
    key: str | None = None,
    depth: int = 0,
) -> SanitizedValue:
    if key and _looks_sensitive(key):
        return _SENSITIVE_TOKEN
    if depth >= _MAX_DEPTH:
        return "<max-depth>"
    if value is None or isinstance(value, bool | int):
        return value
    if isinstance(value, float):
        return value if math.isfinite(value) else None
    if isinstance(value, str):
        return _truncate(value)
    if isinstance(value, bytes):
        return f"<bytes:{len(value)}>"
    if isinstance(value, BaseException):
        return {
            "type": value.__class__.__name__,
            "message": _truncate(str(value)),
        }
    if isinstance(value, Mapping):
        items = list(value.items())[:_MAX_ITEMS]
        return {
            str(item_key): sanitize_value(item_value, key=str(item_key), depth=depth + 1)
            for item_key, item_value in items
        }
    if isinstance(value, Sequence) and not isinstance(value, str | bytes | bytearray):
        return [sanitize_value(item, depth=depth + 1) for item in list(value)[:_MAX_ITEMS]]
    return _truncate(str(value))


def sanitize_error(error: BaseException) -> ObservationPayload:
    return {
        "error_type": error.__class__.__name__,
        "error_message": _truncate(str(error)),
    }


def summarize_result(result: Any) -> ObservationPayload:
    if isinstance(result, Mapping):
        keys = [str(key) for key in list(result.keys())[:_MAX_ITEMS]]
        return {
            "kind": "mapping",
            "size": len(result),
            "keys": keys,
        }
    if isinstance(result, Sequence) and not isinstance(result, str | bytes | bytearray):
        return {
            "kind": "sequence",
            "size": len(result),
            "preview": [sanitize_value(item, depth=1) for item in list(result)[: min(3, _MAX_ITEMS)]],
        }
    if isinstance(result, str):
        return {
            "kind": "text",
            "preview": _truncate(result),
        }
    return {
        "kind": result.__class__.__name__.lower(),
        "preview": sanitize_value(result),
    }


def _looks_sensitive(key: str) -> bool:
    normalized = re.sub(r"[^a-z0-9]+", "", key.lower())
    return any(keyword in normalized for keyword in _SENSITIVE_KEYWORDS)


def _truncate(value: str) -> str:
    trimmed = value.strip()
    if len(trimmed) <= _MAX_STRING_LENGTH:
        return trimmed
    return f"{trimmed[: _MAX_STRING_LENGTH - 3]}..."
