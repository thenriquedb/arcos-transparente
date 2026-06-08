from __future__ import annotations

from typing import Literal, TypeAlias

SanitizedScalar: TypeAlias = str | int | float | bool | None
SanitizedValue: TypeAlias = (
    SanitizedScalar | list["SanitizedValue"] | dict[str, "SanitizedValue"]
)
ObservationPayload: TypeAlias = dict[str, SanitizedValue]
ObservationRunType: TypeAlias = Literal[
    "chain",
    "tool",
    "llm",
    "retriever",
    "embedding",
    "prompt",
    "parser",
]
