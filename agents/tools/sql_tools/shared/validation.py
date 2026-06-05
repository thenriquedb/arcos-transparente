"""Shared validation helpers for public SQL tools."""

from __future__ import annotations

from typing import Any, Callable, TypeVar

from pydantic import BaseModel, ValidationError


ParamsT = TypeVar("ParamsT", bound=BaseModel)


def validate_tool_params(
    payload: dict[str, Any],
    *,
    schema_type: type[ParamsT],
    on_error: Callable[[ValidationError], dict[str, Any]],
) -> ParamsT | dict[str, Any]:
    """Validate tool params and delegate invalid-response shaping to the caller."""

    try:
        return schema_type.model_validate(payload)
    except ValidationError as exc:
        return on_error(exc)
