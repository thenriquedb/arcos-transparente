"""Guardrails compartilhados para perguntas cidadãs antes da execução do modelo."""

from __future__ import annotations

import re

from agents.routing.constants import (
    SUPPORTED_SCOPE_STRONG_KEYWORDS,
    SUPPORTED_SCOPE_WEAK_KEYWORDS,
)
from agents.routing.extractors import (
    _contains_prompt_injection,
    _count_keyword_hits,
    _normalize,
)
from agents.routing.models import GuardrailDecision, RouteDecision

_CONTEXTUAL_REFERENCE_PATTERN = re.compile(
    r"\b(?:dele|dela|ele|ela|esse|essa|esses|essas|desse|dessa|disso|nisso)\b"
)


def evaluate_public_query_guardrails(
    query: str,
    *,
    compatibility_route: RouteDecision | None = None,
    has_history: bool = False,
) -> GuardrailDecision:
    """Aplica bloqueios hard-coded antes da execução do modelo."""

    normalized_text = _normalize(query)

    if not normalized_text:
        return GuardrailDecision(
            allowed=False,
            category="empty_query",
            message=(
                "Envie uma pergunta sobre os dados públicos municipais disponíveis "
                "no sistema, como servidores, secretarias, salários-base ou "
                "licitações, despesas, patrimônio, planejamento, receitas "
                "ou políticos eleitos."
            ),
        )

    if _contains_prompt_injection(normalized_text):
        return GuardrailDecision(
            allowed=False,
            category="prompt_injection",
            message=(
                "Não posso seguir pedidos para ignorar instruções, revelar prompts "
                "internos ou contornar regras do sistema. Posso ajudar apenas com "
                "consultas aos dados públicos municipais disponíveis."
            ),
        )

    strong_hits = _count_keyword_hits(normalized_text, SUPPORTED_SCOPE_STRONG_KEYWORDS)
    weak_hits = _count_keyword_hits(normalized_text, SUPPORTED_SCOPE_WEAK_KEYWORDS)

    if has_history and (
        _looks_like_contextual_follow_up(normalized_text)
        or strong_hits >= 1
        or weak_hits >= 1
    ):
        return GuardrailDecision(allowed=True, category="allowed")

    if compatibility_route is not None and compatibility_route.confident:
        return GuardrailDecision(allowed=True, category="allowed")

    if strong_hits >= 1 or weak_hits >= 2:
        return GuardrailDecision(allowed=True, category="allowed")

    return GuardrailDecision(
        allowed=False,
        category="out_of_scope",
        message=(
            "Posso ajudar apenas com consultas aos dados públicos municipais "
            "disponíveis neste sistema, especialmente sobre servidores, "
            "secretarias, salários-base, histórico de pagamentos, licitações, "
            "despesas, patrimônio, quadro de pessoal, planejamento, receitas "
            "e políticos eleitos."
        ),
    )


def _looks_like_contextual_follow_up(normalized_text: str) -> bool:
    """Permite continuação curta dependente de histórico sem forçar nova rota."""

    if _CONTEXTUAL_REFERENCE_PATTERN.search(normalized_text) is not None:
        return True
    return False
