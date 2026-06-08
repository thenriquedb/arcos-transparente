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
from agents.routing.routes.diarias import (
    _try_route_diarias_agregacao,
    _try_route_diarias_lista,
)
from agents.routing.routes.passagens import (
    _try_route_passagens_agregacao,
    _try_route_passagens_lista,
)
from agents.routing.routes.estoques import (
    _try_route_estoques_agregacao,
    _try_route_estoques_lista,
)
from agents.routing.routes.transferencias_financeiras import (
    _try_route_transferencias_financeiras_agregacao,
    _try_route_transferencias_financeiras_lista,
)
from agents.routing.routes.despesas_por_funcao import (
    _try_route_despesas_por_funcao_agregacao,
    _try_route_despesas_por_funcao_lista,
)
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
    _try_route_diarias_agregacao,  # 5. Totais e rankings de diarias
    _try_route_passagens_agregacao,  # 6. Totais e rankings de passagens
    _try_route_estoques_agregacao,  # 7. Totais e rankings de estoques
    _try_route_transferencias_financeiras_agregacao,  # 8. Totais e rankings de transferencias
    _try_route_despesas_por_funcao_agregacao,  # 9. Totais e rankings do relatorio por funcao
    _try_route_despesas_agregacao,  # 10. Totais e rankings de despesas
    _try_route_patrimonios_agregacao,  # 11. Totais e rankings de patrimônio
    _try_route_quadro_pessoal_agregacao,  # 12. Totais de quadro de pessoal
    _try_route_planejamento_agregacao,  # 13. Totais e rankings de planejamento
    _try_route_receitas_agregacao,  # 14. Totais e rankings de receitas
    _try_route_agregacao,  # 15. Rankings e contagens de servidores
    _try_route_licitacoes_lista,  # 16. Listas e detalhes de licitações
    _try_route_diarias_lista,  # 17. Listas de diarias
    _try_route_passagens_lista,  # 18. Listas de passagens
    _try_route_estoques_lista,  # 19. Listas de estoques e movimentacoes
    _try_route_transferencias_financeiras_lista,  # 20. Listas de transferencias
    _try_route_despesas_por_funcao_lista,  # 21. Listas do relatorio por funcao
    _try_route_despesas_lista,  # 22. Listas de despesas
    _try_route_patrimonios_lista,  # 23. Listas de patrimônio
    _try_route_eleitos_lista,  # 24. Listas de eleitos
    _try_route_quadro_pessoal_lista,  # 25. Listas de quadro de pessoal
    _try_route_planejamento_saude_lista,  # 26. Listas de planejamento
    _try_route_receitas_lista,  # 27. Listas de receitas
    _try_route_lista,  # 28. Listas de servidores
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
    has_history: bool | None = None,
    prior_messages: tuple[tuple[str, str, bool], ...] = (),
) -> GuardrailDecision:
    """Valida escopo e tentativas de manipular o comportamento do agente."""

    route = route or route_user_query(query)
    history_present = (
        has_history
        if has_history is not None
        else bool(prior_user_queries or prior_messages)
    )
    return evaluate_public_query_guardrails(
        query,
        compatibility_route=route,
        has_history=history_present,
        prior_user_queries=prior_user_queries,
        prior_messages=prior_messages,
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
