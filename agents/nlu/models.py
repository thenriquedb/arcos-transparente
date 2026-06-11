"""Tipos usados pelos guardrails."""

from __future__ import annotations

from dataclasses import dataclass
from typing import Literal


GuardrailCategory = Literal[
    "allowed",
    "out_of_scope",
    "prompt_injection",
    "empty_query",
]


@dataclass(slots=True)
class GuardrailDecision:
    """Representa o resultado de segurança e escopo da pergunta."""

    allowed: bool
    category: GuardrailCategory
    message: str | None = None
