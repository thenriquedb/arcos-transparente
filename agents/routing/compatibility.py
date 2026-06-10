"""Compatibility adapter for legacy deterministic public-query routing."""

from __future__ import annotations

from agents.guardrails import evaluate_public_query_guardrails
from agents.routing.conversation import normalize_conversation_text
from agents.routing.models import GuardrailDecision, RouteDecision
from agents.routing.routes.contratos import (
    _try_route_contratos_agregacao,
    _try_route_contratos_lista,
)
from agents.routing.routes.despesas import (
    _try_route_despesas_agregacao,
    _try_route_despesas_lista,
)
from agents.routing.routes.despesas_por_funcao import (
    _try_route_despesas_por_funcao_agregacao,
    _try_route_despesas_por_funcao_lista,
)
from agents.routing.routes.diarias import (
    _try_route_diarias_agregacao,
    _try_route_diarias_lista,
)
from agents.routing.routes.eleitos import _try_route_eleitos_lista
from agents.routing.routes.estoques import (
    _try_route_estoques_agregacao,
    _try_route_estoques_lista,
)
from agents.routing.routes.folha_pagamento import _try_route_historico
from agents.routing.routes.licitacoes import (
    _try_route_licitacoes_agregacao,
    _try_route_licitacoes_lista,
)
from agents.routing.routes.passagens import (
    _try_route_passagens_agregacao,
    _try_route_passagens_lista,
)
from agents.routing.routes.patrimonios import (
    _try_route_patrimonios_agregacao,
    _try_route_patrimonios_lista,
)
from agents.routing.routes.planejamento import (
    _try_route_planejamento_agregacao,
    _try_route_planejamento_saude_lista,
)
from agents.routing.routes.quadro_pessoal import (
    _try_route_quadro_pessoal_agregacao,
    _try_route_quadro_pessoal_lista,
)
from agents.routing.routes.receitas import (
    _try_route_receitas_agregacao,
    _try_route_receitas_lista,
)
from agents.routing.routes.servidores import _try_route_agregacao, _try_route_lista
from agents.routing.routes.transferencias_financeiras import (
    _try_route_transferencias_financeiras_agregacao,
    _try_route_transferencias_financeiras_lista,
)
from agents.tools.registry import get_public_tools

# The priority chain stays centralized here as the single deterministic
# precedence order. It is load-bearing for the main chatbot path: the policy
# gate and several hybrid-selection heuristics call route_public_compatibility_query
# directly, in addition to legacy compatibility callers.
ROUTE_PRIORITY_CHAIN = (
    _try_route_historico,
    _try_route_contratos_agregacao,
    _try_route_contratos_lista,
    _try_route_licitacoes_agregacao,
    _try_route_diarias_agregacao,
    _try_route_passagens_agregacao,
    _try_route_estoques_agregacao,
    _try_route_transferencias_financeiras_agregacao,
    _try_route_despesas_por_funcao_agregacao,
    _try_route_despesas_agregacao,
    _try_route_patrimonios_agregacao,
    _try_route_quadro_pessoal_agregacao,
    _try_route_planejamento_agregacao,
    _try_route_receitas_agregacao,
    _try_route_agregacao,
    _try_route_licitacoes_lista,
    _try_route_diarias_lista,
    _try_route_passagens_lista,
    _try_route_estoques_lista,
    _try_route_transferencias_financeiras_lista,
    _try_route_despesas_por_funcao_lista,
    _try_route_despesas_lista,
    _try_route_patrimonios_lista,
    _try_route_eleitos_lista,
    _try_route_quadro_pessoal_lista,
    _try_route_planejamento_saude_lista,
    _try_route_receitas_lista,
    _try_route_lista,
)


def route_public_compatibility_query(query: str) -> RouteDecision:
    """Apply legacy routing heuristics for compatibility-only callers."""

    normalized_text = normalize_conversation_text(query)
    for try_route in ROUTE_PRIORITY_CHAIN:
        if route := try_route(normalized_text):
            return route
    return _build_fallback_route()


def evaluate_public_compatibility_guardrails(
    query: str,
    *,
    route: RouteDecision | None = None,
    prior_user_queries: tuple[str, ...] = (),
    has_history: bool | None = None,
    prior_messages: tuple[tuple[str, str, bool], ...] = (),
) -> GuardrailDecision:
    """Validate compatibility queries before narrowing public tools."""

    resolved_route = route or route_public_compatibility_query(query)
    history_present = (
        has_history
        if has_history is not None
        else bool(prior_user_queries or prior_messages)
    )
    return evaluate_public_query_guardrails(
        query,
        compatibility_route=resolved_route,
        has_history=history_present,
        prior_user_queries=prior_user_queries,
        prior_messages=prior_messages,
    )


def select_public_compatibility_tools(query: str | None = None) -> list[object]:
    """Narrow public tools only for compatibility flows that still need it."""

    if not query:
        return get_public_tools()

    route = route_public_compatibility_query(query)
    guardrail = evaluate_public_compatibility_guardrails(query, route=route)
    if not guardrail.allowed:
        return []

    if not route.confident:
        return get_public_tools()

    tools = get_public_tools(tags=route.tags[1:])
    return tools or get_public_tools()


def _build_fallback_route() -> RouteDecision:
    return RouteDecision(
        domain="desconhecido",
        operation_type="desconhecido",
        tags=["scope:public"],
        confident=False,
    )
