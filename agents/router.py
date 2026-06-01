"""Fachada de compatibilidade para heurísticas determinísticas legadas."""

from __future__ import annotations

from agents.guardrails import evaluate_public_query_guardrails
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
from agents.routing.routes.despesas import (
    _try_route_despesas_agregacao,
    _try_route_despesas_lista,
)
from agents.routing.routes.contratos import (
    _try_route_contratos_agregacao,
    _try_route_contratos_lista,
)
from agents.routing.routes.licitacoes import (
    _try_route_licitacoes_agregacao,
    _try_route_licitacoes_lista,
)
from agents.routing.routes.planejamento import (
    _try_route_planejamento_agregacao,
    _try_route_planejamento_saude_lista,
)
from agents.routing.routes.patrimonios import (
    _try_route_patrimonios_agregacao,
    _try_route_patrimonios_lista,
)
from agents.routing.routes.eleitos import _try_route_eleitos_lista
from agents.routing.routes.quadro_pessoal import (
    _try_route_quadro_pessoal_agregacao,
    _try_route_quadro_pessoal_lista,
)
from agents.routing.routes.receitas import (
    _try_route_receitas_agregacao,
    _try_route_receitas_lista,
)
from agents.routing.routes.servidores import _try_route_agregacao, _try_route_lista
from agents.tools.registry import get_public_tools


# A cadeia de prioridades fica centralizada aqui para deixar explícito
# qual domínio vence quando mais de uma heurística faz match.
ROUTE_PRIORITY_CHAIN = (
    _try_route_historico,  # 1. Histórico individual de pagamentos
    _try_route_contratos_agregacao,  # 2. Rankings e totais de contratos
    _try_route_contratos_lista,  # 3. Listas e detalhes de contratos
    _try_route_licitacoes_agregacao,  # 4. Rankings e contagens de licitações
    _try_route_despesas_agregacao,  # 5. Totais e rankings de despesas
    _try_route_patrimonios_agregacao,  # 6. Totais e rankings de patrimônio
    _try_route_quadro_pessoal_agregacao,  # 7. Totais de quadro de pessoal
    _try_route_planejamento_agregacao,  # 8. Totais e rankings de planejamento
    _try_route_receitas_agregacao,  # 9. Totais e rankings de receitas
    _try_route_agregacao,  # 10. Rankings e contagens de servidores
    _try_route_licitacoes_lista,  # 11. Listas e detalhes de licitações
    _try_route_despesas_lista,  # 12. Listas de despesas
    _try_route_patrimonios_lista,  # 13. Listas de patrimônio
    _try_route_eleitos_lista,  # 14. Listas de eleitos
    _try_route_quadro_pessoal_lista,  # 15. Listas de quadro de pessoal
    _try_route_planejamento_saude_lista,  # 16. Listas de planejamento
    _try_route_receitas_lista,  # 17. Listas de receitas
    _try_route_lista,  # 18. Listas de servidores
)


def _build_fallback_route() -> RouteDecision:
    """Cria a rota padrão quando nenhuma heurística reconhece a pergunta."""

    return RouteDecision(
        domain="desconhecido",
        operation_type="desconhecido",
        tags=["scope:public"],
        confident=False,
    )


def route_user_query(query: str) -> RouteDecision:
    """Aplica heurísticas legadas de compatibilidade na ordem definida acima."""

    normalized_text = _normalize(query)

    # Cada função abaixo tenta reconhecer um formato específico de pergunta.
    for try_route in ROUTE_PRIORITY_CHAIN:
        if route := try_route(normalized_text):
            return route

    # Se nada bater, devolvemos uma rota neutra e deixamos o LLM decidir.
    return _build_fallback_route()


def evaluate_query_guardrails(
    query: str,
    route: RouteDecision | None = None,
    prior_user_queries: tuple[str, ...] = (),
) -> GuardrailDecision:
    """Valida escopo e tentativas de manipular o comportamento do agente."""

    route = route or route_user_query(query)
    return evaluate_public_query_guardrails(
        query,
        compatibility_route=route,
        has_history=bool(prior_user_queries),
        prior_user_queries=prior_user_queries,
    )


def select_public_tools_for_query(query: str | None = None) -> list[object]:
    """Sugere subconjuntos de tools apenas para fluxos legados/compatíveis."""

    if not query:
        return get_public_tools()

    route = route_user_query(query)
    guardrail = evaluate_query_guardrails(query, route=route)
    if not guardrail.allowed:
        return []

    # Quando a heurística não tem confiança, deixamos o agente ver todas as tools.
    if not route.confident:
        return get_public_tools()

    tools = get_public_tools(tags=route.tags[1:])
    return tools or get_public_tools()


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
    "_try_route_despesas_agregacao",
    "_try_route_historico",
    "_try_route_lista",
    "_try_route_patrimonios_agregacao",
    "_try_route_planejamento_agregacao",
    "_try_route_quadro_pessoal_agregacao",
    "_try_route_receitas_agregacao",
]
