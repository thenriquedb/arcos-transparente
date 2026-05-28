"""Tipos usados pelo router e pelos guardrails."""

from __future__ import annotations

from dataclasses import dataclass, field
from typing import Any, Literal


Domain = Literal[
    "servidores",
    "folha_pagamento",
    "contratos",
    "licitacoes",
    "planejamento",
    "receitas",
    "despesas",
    "patrimonios",
    "quadro_pessoal",
    "eleitos",
    "desconhecido",
]
OperationType = Literal[
    "consulta_lista",
    "agregacao_ranking",
    "historico_detalhado",
    "desconhecido",
]
GuardrailCategory = Literal[
    "allowed",
    "out_of_scope",
    "prompt_injection",
    "empty_query",
]


@dataclass(slots=True)
class RouteDecision:
    """Representa a decisão final de roteamento para uma pergunta."""

    domain: Domain
    operation_type: OperationType
    tool_name: str | None = None
    tool_kwargs: dict[str, Any] = field(default_factory=dict)
    tags: list[str] = field(default_factory=lambda: ["scope:public"])
    confident: bool = False


@dataclass(slots=True)
class GuardrailDecision:
    """Representa o resultado de segurança e escopo da pergunta."""

    allowed: bool
    category: GuardrailCategory
    message: str | None = None
