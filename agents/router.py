"""Stable compatibility facade for legacy deterministic routing helpers."""

from __future__ import annotations

from agents.routing.compatibility import (
    evaluate_public_compatibility_guardrails,
    route_public_compatibility_query,
    select_public_compatibility_tools,
)
from agents.routing.extractors import (
    _extract_limit,
    _extract_planejamento_entidade,
    _extract_secretaria,
    _normalize,
)
from agents.routing.models import (
    Domain,
    GuardrailCategory,
    GuardrailDecision,
    OperationType,
    RouteDecision,
)
from agents.routing.routes.folha_pagamento import _try_route_historico
from agents.routing.routes.diarias import _try_route_diarias_agregacao
from agents.routing.routes.passagens import _try_route_passagens_agregacao
from agents.routing.routes.estoques import _try_route_estoques_agregacao
from agents.routing.routes.transferencias_financeiras import (
    _try_route_transferencias_financeiras_agregacao,
)
from agents.routing.routes.despesas_por_funcao import (
    _try_route_despesas_por_funcao_agregacao,
)
from agents.routing.routes.despesas import _try_route_despesas_agregacao
from agents.routing.routes.contratos import _try_route_contratos_agregacao
from agents.routing.routes.licitacoes import _try_route_licitacoes_agregacao
from agents.routing.routes.planejamento import _try_route_planejamento_agregacao
from agents.routing.routes.patrimonios import _try_route_patrimonios_agregacao
from agents.routing.routes.quadro_pessoal import _try_route_quadro_pessoal_agregacao
from agents.routing.routes.receitas import _try_route_receitas_agregacao
from agents.routing.routes.servidores import _try_route_agregacao, _try_route_lista


def route_user_query(query: str) -> RouteDecision:
    """Backwards-compatible facade for legacy public-query routing."""

    return route_public_compatibility_query(query)


def evaluate_query_guardrails(
    query: str,
    route: RouteDecision | None = None,
    prior_user_queries: tuple[str, ...] = (),
    has_history: bool | None = None,
    prior_messages: tuple[tuple[str, str, bool], ...] = (),
) -> GuardrailDecision:
    """Backwards-compatible facade for legacy public guardrails."""

    return evaluate_public_compatibility_guardrails(
        query,
        route=route,
        prior_user_queries=prior_user_queries,
        has_history=has_history,
        prior_messages=prior_messages,
    )


def select_public_tools_for_query(query: str | None = None) -> list[object]:
    """Backwards-compatible facade for legacy public-tool narrowing."""

    return select_public_compatibility_tools(query)


__all__ = [
    "Domain",
    "OperationType",
    "GuardrailCategory",
    "RouteDecision",
    "GuardrailDecision",
    "route_user_query",
    "evaluate_query_guardrails",
    "select_public_tools_for_query",
    "_extract_limit",
    "_extract_planejamento_entidade",
    "_extract_secretaria",
    "_normalize",
    "_try_route_agregacao",
    "_try_route_contratos_agregacao",
    "_try_route_diarias_agregacao",
    "_try_route_despesas_por_funcao_agregacao",
    "_try_route_estoques_agregacao",
    "_try_route_passagens_agregacao",
    "_try_route_despesas_agregacao",
    "_try_route_historico",
    "_try_route_lista",
    "_try_route_patrimonios_agregacao",
    "_try_route_planejamento_agregacao",
    "_try_route_quadro_pessoal_agregacao",
    "_try_route_receitas_agregacao",
]
