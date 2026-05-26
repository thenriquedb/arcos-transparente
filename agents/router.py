"""Fachada do router determinístico usada pelo agente principal."""

from __future__ import annotations

from agents.routing.constants import (
    SUPPORTED_SCOPE_STRONG_KEYWORDS,
    SUPPORTED_SCOPE_WEAK_KEYWORDS,
)
from agents.routing.extractors import (
    _contains_prompt_injection,
    _count_keyword_hits,
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
    _try_route_quadro_pessoal_lista,  # 14. Listas de quadro de pessoal
    _try_route_planejamento_saude_lista,  # 15. Listas de planejamento
    _try_route_receitas_lista,  # 16. Listas de receitas
    _try_route_lista,  # 17. Listas de servidores
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
    """Aplica as heurísticas do router na ordem de prioridade definida acima."""

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
) -> GuardrailDecision:
    """Valida escopo e tentativas de manipular o comportamento do agente."""

    normalized_text = _normalize(query)

    if not normalized_text:
        return GuardrailDecision(
            allowed=False,
            category="empty_query",
            message=(
                "Envie uma pergunta sobre os dados públicos municipais disponíveis "
                "no sistema, como servidores, secretarias, salários-base ou "
                "licitações, despesas, patrimônio, planejamento ou receitas."
            ),
        )

    # Bloqueia pedidos para ignorar regras, revelar prompts ou burlar o sistema.
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

    route = route or route_user_query(query)
    strong_hits = _count_keyword_hits(normalized_text, SUPPORTED_SCOPE_STRONG_KEYWORDS)
    weak_hits = _count_keyword_hits(normalized_text, SUPPORTED_SCOPE_WEAK_KEYWORDS)

    # Uma rota confiante ou várias palavras-chave municipais já bastam para liberar.
    if route.confident or strong_hits >= 1 or weak_hits >= 2:
        return GuardrailDecision(
            allowed=True,
            category="allowed",
        )

    return GuardrailDecision(
        allowed=False,
        category="out_of_scope",
        message=(
            "Posso ajudar apenas com consultas aos dados públicos municipais "
            "disponíveis neste sistema, especialmente sobre servidores, "
            "secretarias, salários-base, histórico de pagamentos, licitações, "
            "despesas, patrimônio, quadro de pessoal, planejamento e receitas."
        ),
    )


def select_public_tools_for_query(query: str | None = None) -> list[object]:
    """Seleciona apenas as tools públicas relevantes para a pergunta."""

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
