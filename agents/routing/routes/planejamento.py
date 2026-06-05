"""Regras de roteamento para planejamento."""

from __future__ import annotations

from agents.routing.routes.despesas_por_funcao import _is_despesas_por_funcao_query
from agents.routing.extractors import (
    _contains_term,
    _extract_limit,
    _extract_planejamento_filters_from_query,
    _extract_planejamento_metric,
    _is_planejamento_query,
)
from agents.routing.models import RouteDecision


def _try_route_planejamento_agregacao(normalized_text: str) -> RouteDecision | None:
    """
    Roteia para totais e rankings do planejamento publico.

    Casos que devem retornar RouteDecision:
        "quanto foi planejado para saude em 2025"
        "quanto foi pago em saude no primeiro trimestre de 2025"
        "quais acoes de saude tiveram maior orcamento"
        "quanto foi pago na prefeitura em 2025"
        "quanto foi pago na educacao em 2025"

    Casos que devem retornar None:
        "licitacoes da saude"       -> vai para _try_route_licitacoes_lista
        "funcionarios da saude"     -> vai para _try_route_lista
        "salario do pedro"          -> vai para _try_route_historico
    """
    if not _is_planejamento_query(normalized_text):
        return None
    if _is_despesas_por_funcao_query(normalized_text):
        return None

    # Pedidos de lista sem linguagem de total/ranking ficam com a tool de consulta.
    if any(
        keyword in normalized_text
        for keyword in ("lista", "liste", "mostre", "quais", "detalhe")
    ) and not any(
        keyword in normalized_text
        for keyword in ("maior", "maiores", "mais", "quanto", "total", "por mes")
    ):
        return None

    filtros = _extract_planejamento_filters_from_query(normalized_text)
    metrica = _extract_planejamento_metric(normalized_text)

    # O agrupamento é inferido pela dimensão mais explícita mencionada na pergunta.
    if any(
        _contains_term(normalized_text, keyword) for keyword in ("por mes", "mes a mes")
    ):
        agrupar_por = "mes"
    elif _contains_term(normalized_text, "programa"):
        agrupar_por = "programa"
    elif _contains_term(normalized_text, "subarea") or _contains_term(
        normalized_text, "subfuncao"
    ):
        agrupar_por = "subarea"
    elif _contains_term(normalized_text, "acao") or _contains_term(
        normalized_text, "acoes"
    ):
        agrupar_por = "acao"
    elif _contains_term(normalized_text, "grupo") or _contains_term(
        normalized_text, "tipo de gasto"
    ):
        agrupar_por = "grupo_de_gasto"
    else:
        agrupar_por = None

    return RouteDecision(
        domain="planejamento",
        operation_type="agregacao_ranking",
        tool_name="agregar_planejamento",
        tool_kwargs={
            "filtros": filtros,
            "agrupar_por": agrupar_por,
            "metrica": metrica,
            "ordenar_por": "metrica",
            "ordem": "desc",
            "limite": _extract_limit(normalized_text, default=10),
        },
        tags=["scope:public", "domain:planejamento", "shape:aggregate"],
        confident=True,
    )


def _try_route_planejamento_saude_lista(normalized_text: str) -> RouteDecision | None:
    """
    Roteia para listagens do planejamento publico.

    Casos que devem retornar RouteDecision:
        "liste o planejamento da saude em 2025"
        "mostre as acoes planejadas da saude"
        "quais linhas do orcamento da saude"
        "liste o planejamento da prefeitura em 2025"
        "mostre as acoes planejadas da educacao"

    Casos que devem retornar None:
        "quanto foi pago na saude"  -> vai para _try_route_planejamento_agregacao
        "licitacao numero 12/2025"  -> vai para _try_route_licitacoes_lista
        "funcionarios da saude"     -> vai para _try_route_lista
    """
    if not _is_planejamento_query(normalized_text):
        return None
    if not any(
        keyword in normalized_text
        for keyword in ("lista", "liste", "mostre", "quais", "detalhe")
    ):
        return None

    filtros = _extract_planejamento_filters_from_query(normalized_text)
    return RouteDecision(
        domain="planejamento",
        operation_type="consulta_lista",
        tool_name="consultar_planejamento",
        tool_kwargs={
            "filtros": filtros,
            "ordenar_por": "mes_num",
            "ordem": "asc",
            "limite": 100
            if any(keyword in normalized_text for keyword in ("todas", "todos"))
            else 10,
        },
        tags=["scope:public", "domain:planejamento", "shape:lookup"],
        confident=True,
    )
