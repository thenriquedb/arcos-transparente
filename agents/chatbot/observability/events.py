"""Construcao de payloads de eventos de observabilidade do chatbot."""

from __future__ import annotations

from collections.abc import Mapping
from typing import Any

from .sanitization import sanitize_error, sanitize_mapping
from .types import ObservationPayload

_ALLOWED_EVENT_KEYS = frozenset(
    {
        "request_id",
        "session_id",
        "question",
        "backend_question",
        "resolved_question",
        "history_size",
        "surface",
        "status",
        "provider",
        "local_response",
        "policy_action",
        "policy_category",
        "selection_action",
        "selection_confidence",
        "selection_reason_code",
        "selection_fallback",
        "selected_tool_names",
        "candidate_tool_names",
        "tool_name",
        "tool_arguments",
        "output_summary",
        "response_preview",
        "guardrail_triggered",
        "streaming",
        "fallback_used",
        "reason_code",
        "error_type",
        "error_message",
    }
)


def build_event_payload(payload: Mapping[str, Any] | None = None) -> ObservationPayload:
    return sanitize_mapping(payload, allowed_keys=tuple(_ALLOWED_EVENT_KEYS))


def build_error_payload(
    error: BaseException,
    *,
    extra: Mapping[str, Any] | None = None,
) -> ObservationPayload:
    payload = dict(extra or {})
    payload.update(sanitize_error(error))
    return build_event_payload(payload)
