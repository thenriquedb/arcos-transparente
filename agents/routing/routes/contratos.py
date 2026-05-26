"""Regras de roteamento para contratos."""

from __future__ import annotations

from agents.routing.extractors import (
    _build_contratos_filters_from_query,
    _extract_limit,
    _is_contratos_query,
)
from agents.routing.models import RouteDecision


def _try_route_contratos_agregacao(normalized_text: str) -> RouteDecision | None:
    """
    Roteia para consultas agregadas e rankings de contratos.

    Casos que devem retornar RouteDecision:
        "qual o total contratado pela educacao"
        "qual secretaria tem mais contratos"
        "quantos contratos existem na saude"

    Casos que devem retornar None:
        "detalhe o contrato 12/2025" -> vai para _try_route_contratos_lista
        "licitacao numero 12/2025"   -> vai para _try_route_licitacoes_lista
        "salario do pedro"           -> vai para _try_route_historico
    """
    if not _is_contratos_query(normalized_text):
        return None

    filtros = _build_contratos_filters_from_query(normalized_text)

    if "qual secretaria" in normalized_text and "mais contrato" in normalized_text:
        return RouteDecision(
            domain="contratos",
            operation_type="agregacao_ranking",
            tool_name="agregar_contratos",
            tool_kwargs={
                "agrupar_por": "secretaria",
                "metrica": "contagem",
                "ordenar_por": "metrica",
                "ordem": "desc",
                "limite": 1,
            },
            tags=["scope:public", "domain:contratos", "shape:aggregate"],
            confident=True,
        )

    if any(keyword in normalized_text for keyword in ("quantos", "quantas")):
        return RouteDecision(
            domain="contratos",
            operation_type="agregacao_ranking",
            tool_name="agregar_contratos",
            tool_kwargs={
                "filtros": filtros,
                "metrica": "contagem",
            },
            tags=["scope:public", "domain:contratos", "shape:aggregate"],
            confident=True,
        )

    if any(
        keyword in normalized_text for keyword in ("total", "somatorio", "somatorio")
    ):
        return RouteDecision(
            domain="contratos",
            operation_type="agregacao_ranking",
            tool_name="agregar_contratos",
            tool_kwargs={
                "filtros": filtros,
                "metrica": "soma_valor",
                "ordenar_por": "metrica",
                "ordem": "desc",
                "limite": _extract_limit(normalized_text, default=10),
            },
            tags=["scope:public", "domain:contratos", "shape:aggregate"],
            confident=True,
        )

    return None


def _try_route_contratos_lista(normalized_text: str) -> RouteDecision | None:
    """
    Roteia para listagens e detalhes de contratos.

    Casos que devem retornar RouteDecision:
        "quais contratos da saude"
        "detalhe o contrato 12/2025"
        "quais os maiores contratos de 2025"

    Casos que devem retornar None:
        "qual o total contratado"    -> vai para _try_route_contratos_agregacao
        "quantos contratos existem"  -> vai para _try_route_contratos_agregacao
        "licitacoes da saude"        -> vai para _try_route_licitacoes_lista
    """
    if not _is_contratos_query(normalized_text):
        return None

    filtros = _build_contratos_filters_from_query(normalized_text)

    if any(keyword in normalized_text for keyword in ("maiores", "maior", "top")):
        return RouteDecision(
            domain="contratos",
            operation_type="consulta_lista",
            tool_name="consultar_contratos",
            tool_kwargs={
                "filtros": filtros,
                "ordenar_por": "valor",
                "ordem": "desc",
                "limite": _extract_limit(normalized_text, default=10),
                "campos": [
                    "numero",
                    "fornecedor",
                    "valor",
                    "secretaria",
                    "data_inicio",
                    "categoria",
                ],
            },
            tags=["scope:public", "domain:contratos", "shape:lookup"],
            confident=True,
        )

    if filtros or any(
        keyword in normalized_text
        for keyword in ("lista", "liste", "quais", "detalhe", "mostre")
    ):
        incluir_detalhes = any(
            keyword in normalized_text
            for keyword in ("detalhe", "detalhes", "completo", "completos")
        )
        limite = (
            100
            if any(keyword in normalized_text for keyword in ("todas", "todos"))
            else 10
        )
        return RouteDecision(
            domain="contratos",
            operation_type="consulta_lista",
            tool_name="consultar_contratos",
            tool_kwargs={
                "filtros": filtros,
                "ordenar_por": "data_inicio",
                "ordem": "desc",
                "limite": limite,
                **({"incluir_detalhes": True} if incluir_detalhes else {}),
            },
            tags=["scope:public", "domain:contratos", "shape:lookup"],
            confident=True,
        )

    return None
