"""Regras de roteamento para licitações."""

from __future__ import annotations

from agents.routing.extractors import (
    _build_licitacoes_filters_from_query,
    _extract_limit,
    _is_licitacoes_query,
)
from agents.routing.models import RouteDecision


def _try_route_licitacoes_agregacao(normalized_text: str) -> RouteDecision | None:
    """
    Roteia para consultas agregadas e rankings de licitacoes.

    Casos que devem retornar RouteDecision:
        "quantas licitacoes existem na saude"
        "qual secretaria tem mais licitacoes"
        "quais as 10 maiores licitacoes"

    Casos que devem retornar None:
        "licitacao numero 12/2025" -> vai para _try_route_licitacoes_lista
        "salario do pedro"         -> vai para _try_route_historico
        "funcionarios da saude"    -> vai para _try_route_lista
    """
    if not _is_licitacoes_query(normalized_text):
        return None

    # Perguntas do tipo "quais... e qual foi o total gasto?" ficam com a tool de lista.
    if any(keyword in normalized_text for keyword in ("todas", "todos", "quais")) and any(
        keyword in normalized_text for keyword in ("total", "gasto", "gastos", "valor")
    ):
        return None

    if "qual secretaria" in normalized_text and "mais" in normalized_text:
        return RouteDecision(
            domain="licitacoes",
            operation_type="agregacao_ranking",
            tool_name="agregar_licitacoes",
            tool_kwargs={
                "agrupar_por": "secretaria",
                "metrica": "contagem",
                "ordenar_por": "metrica",
                "ordem": "desc",
                "limite": 1,
            },
            tags=["scope:public", "domain:licitacoes", "shape:aggregate"],
            confident=True,
        )

    if "modalidade" in normalized_text and any(
        keyword in normalized_text for keyword in ("mais", "ranking", "quantidade")
    ):
        return RouteDecision(
            domain="licitacoes",
            operation_type="agregacao_ranking",
            tool_name="agregar_licitacoes",
            tool_kwargs={
                "agrupar_por": "modalidade",
                "metrica": "contagem",
                "ordenar_por": "metrica",
                "ordem": "desc",
            },
            tags=["scope:public", "domain:licitacoes", "shape:aggregate"],
            confident=True,
        )

    if any(keyword in normalized_text for keyword in ("quantas", "quantos", "total de")):
        filtros = _build_licitacoes_filters_from_query(normalized_text)
        return RouteDecision(
            domain="licitacoes",
            operation_type="agregacao_ranking",
            tool_name="agregar_licitacoes",
            tool_kwargs={
                "filtros": filtros,
                "metrica": "contagem",
            },
            tags=["scope:public", "domain:licitacoes", "shape:aggregate"],
            confident=True,
        )

    if any(keyword in normalized_text for keyword in ("maiores", "maior", "top")):
        return RouteDecision(
            domain="licitacoes",
            operation_type="consulta_lista",
            tool_name="consultar_licitacoes",
            tool_kwargs={
                "ordenar_por": "valor_estimado",
                "ordem": "desc",
                "limite": _extract_limit(normalized_text, default=10),
                "campos": [
                    "numero",
                    "objeto",
                    "valor_estimado",
                    "secretaria",
                    "data_abertura",
                    "situacao",
                ],
            },
            tags=["scope:public", "domain:licitacoes", "shape:lookup"],
            confident=True,
        )

    return None


def _try_route_licitacoes_lista(normalized_text: str) -> RouteDecision | None:
    """
    Roteia para listagens e detalhes de licitacoes.

    Casos que devem retornar RouteDecision:
        "liste as licitacoes da saude"
        "detalhe a licitacao numero 12/2025"
        "quais licitacoes foram abertas"

    Casos que devem retornar None:
        "quantas licitacoes existem" -> vai para _try_route_licitacoes_agregacao
        "maiores licitacoes"         -> vai para _try_route_licitacoes_agregacao
        "funcionarios da saude"      -> vai para _try_route_lista
    """
    if not _is_licitacoes_query(normalized_text):
        return None

    filtros = _build_licitacoes_filters_from_query(normalized_text)
    incluir_detalhes = False

    # Número explícito ou menção a vencedores/contratos exige payload mais detalhado.
    if "numero" in filtros:
        incluir_detalhes = True
    if any(
        keyword in normalized_text
        for keyword in (
            "vencedor",
            "vencedores",
            "contrato",
            "contratos",
            "instrumento",
        )
    ):
        incluir_detalhes = True

    if filtros or any(keyword in normalized_text for keyword in ("lista", "liste", "quais", "detalhe", "mostre")):
        limite = 100 if any(keyword in normalized_text for keyword in ("todas", "todos")) else 10
        return RouteDecision(
            domain="licitacoes",
            operation_type="consulta_lista",
            tool_name="consultar_licitacoes",
            tool_kwargs={
                "filtros": filtros,
                "ordenar_por": "data_abertura",
                "ordem": "desc",
                "limite": limite,
                "incluir_detalhes": incluir_detalhes,
            },
            tags=["scope:public", "domain:licitacoes", "shape:lookup"],
            confident=True,
        )

    return None
