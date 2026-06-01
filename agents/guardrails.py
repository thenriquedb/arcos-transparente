"""Guardrails compartilhados para perguntas cidadãs antes da execução do modelo."""

from __future__ import annotations

from collections.abc import Sequence
import re

from agents.routing.constants import (
    SUPPORTED_SCOPE_STRONG_KEYWORDS,
    SUPPORTED_SCOPE_WEAK_KEYWORDS,
)
from agents.routing.extractors import (
    _contains_prompt_injection,
    _count_keyword_hits,
    _extract_contratos_descricao,
    _extract_licitacoes_objeto,
    _normalize,
)
from agents.routing.models import GuardrailDecision, RouteDecision

_CONTEXTUAL_REFERENCE_PATTERN = re.compile(
    r"\b(?:dele|dela|ele|ela|esse|essa|esses|essas|desse|dessa|disso|nisso)\b"
)
_ELLIPTICAL_YEAR_FOLLOW_UP_PATTERN = re.compile(
    r"^(?:e\s+)?(?:(?:o|a|os|as)\s+)?(?:(?:de|do|da|em)\s+)?20\d{2}\??$"
)
_PUBLIC_SPEND_SIGNAL_TERMS = (
    "custo",
    "custos",
    "custou",
    "gasto",
    "gastos",
    "pago",
    "pagos",
)


def evaluate_public_query_guardrails(
    query: str,
    *,
    compatibility_route: RouteDecision | None = None,
    has_history: bool = False,
    prior_user_queries: Sequence[str] = (),
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

    contextual_follow_up = _looks_like_contextual_follow_up(normalized_text)
    if has_history and (
        (
            contextual_follow_up
            and _has_public_context_anchor(prior_user_queries)
        )
        or strong_hits >= 1
        or weak_hits >= 1
    ):
        return GuardrailDecision(allowed=True, category="allowed")

    if compatibility_route is not None and compatibility_route.confident:
        return GuardrailDecision(allowed=True, category="allowed")

    if strong_hits >= 1 or weak_hits >= 2:
        return GuardrailDecision(allowed=True, category="allowed")

    if _looks_like_public_spend_query(normalized_text):
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
    if _ELLIPTICAL_YEAR_FOLLOW_UP_PATTERN.fullmatch(normalized_text) is not None:
        return True
    return False


def _looks_like_public_spend_query(normalized_text: str) -> bool:
    """Permite perguntas de gasto/custo quando o objeto público é reconhecível."""

    has_spend_signal = any(
        re.search(rf"\b{re.escape(term)}\b", normalized_text) is not None
        for term in _PUBLIC_SPEND_SIGNAL_TERMS
    )
    if not has_spend_signal:
        return False

    if _extract_licitacoes_objeto(normalized_text) is not None:
        return True
    if _extract_contratos_descricao(normalized_text) is not None:
        return True
    return False


def _has_public_context_anchor(prior_user_queries: Sequence[str]) -> bool:
    """Aceita follow-up curto apenas quando ele continua uma trilha pública válida."""

    for prior_query in reversed(prior_user_queries):
        normalized_prior_query = _normalize(prior_query)
        if not normalized_prior_query:
            continue
        if _query_establishes_public_context(normalized_prior_query):
            return True
        if _looks_like_contextual_follow_up(normalized_prior_query):
            continue
        return False
    return False


def _query_establishes_public_context(normalized_text: str) -> bool:
    """Reconhece uma pergunta que por si só já estabelece escopo público."""

    strong_hits = _count_keyword_hits(normalized_text, SUPPORTED_SCOPE_STRONG_KEYWORDS)
    weak_hits = _count_keyword_hits(normalized_text, SUPPORTED_SCOPE_WEAK_KEYWORDS)
    if strong_hits >= 1 or weak_hits >= 2:
        return True
    return _looks_like_public_spend_query(normalized_text)
