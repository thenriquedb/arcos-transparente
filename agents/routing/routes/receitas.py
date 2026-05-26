"""Regras de roteamento para receitas."""

from __future__ import annotations

from agents.routing.extractors import (
    _extract_limit,
    _extract_receitas_filters_from_query,
    _extract_receitas_metric,
    _extract_receitas_tipo_de_dado,
    _is_receitas_query,
)
from agents.routing.models import RouteDecision


def _extract_receitas_group_by(normalized_text: str, tipo_de_dado: str) -> str | None:
    """Infere agrupamentos simples em perguntas de totais e rankings de receitas."""

    if any(keyword in normalized_text for keyword in ("por mes", "mes a mes")):
        return "mes"
    if any(keyword in normalized_text for keyword in ("categoria", "categorias")):
        return "categoria"
    if any(
        keyword in normalized_text
        for keyword in (
            "origem do recurso",
            "origem de recurso",
            "fonte de recurso",
            "fontes de recurso",
        )
    ):
        return "origem_do_recurso"
    if any(keyword in normalized_text for keyword in ("unidade", "gestora")):
        return "unidade_responsavel"
    if tipo_de_dado == "lancamento":
        if any(keyword in normalized_text for keyword in ("tipo", "tipos")):
            return "tipo"
        if any(keyword in normalized_text for keyword in ("tributo", "tributos")):
            return "tributo"
    return None


def _try_route_receitas_agregacao(normalized_text: str) -> RouteDecision | None:
    """
    Roteia para totais, contagens e rankings de receitas.

    Casos que devem retornar RouteDecision:
        "quanto foi arrecadado com iptu em 2025"
        "quanto foi lancado de itbi em 2025"
        "qual a origem do recurso que mais arrecadou"

    Casos que devem retornar None:
        "quais as 10 maiores receitas" -> vai para _try_route_receitas_lista
        "contratos da saude"           -> vai para _try_route_contratos_lista
        "servidores da educacao"       -> vai para _try_route_lista
    """
    if not _is_receitas_query(normalized_text):
        return None

    if any(keyword in normalized_text for keyword in ("maiores", "maior", "top")):
        return None

    filtros = _extract_receitas_filters_from_query(normalized_text)
    tipo_de_dado = _extract_receitas_tipo_de_dado(normalized_text)
    metrica = _extract_receitas_metric(normalized_text, tipo_de_dado)
    agrupar_por = _extract_receitas_group_by(normalized_text, tipo_de_dado)

    if not any(
        keyword in normalized_text
        for keyword in (
            "quanto",
            "total",
            "totais",
            "quantos",
            "quantas",
            "somatorio",
            "arrecadou",
            "arrecadado",
            "lancou",
            "lancado",
            "divida ativa",
            "cobranca judicial",
            "mais arrecadou",
            "mais lancou",
        )
    ):
        return None

    return RouteDecision(
        domain="receitas",
        operation_type="agregacao_ranking",
        tool_name="agregar_receitas",
        tool_kwargs={
            "filtros": filtros,
            "agrupar_por": agrupar_por,
            "metrica": metrica,
            "ordenar_por": "metrica",
            "ordem": "desc",
            "limite": _extract_limit(normalized_text, default=10),
        },
        tags=["scope:public", "domain:receitas", "shape:aggregate"],
        confident=True,
    )


def _try_route_receitas_lista(normalized_text: str) -> RouteDecision | None:
    """
    Roteia para listagens e buscas filtradas de receitas.

    Casos que devem retornar RouteDecision:
        "quais as 10 maiores receitas de 2025"
        "liste receitas do fundeb em 2025"
        "mostre os lancamentos de iptu"

    Casos que devem retornar None:
        "quanto foi arrecadado com iptu" -> vai para _try_route_receitas_agregacao
        "licitacoes de 2025"             -> vai para _try_route_licitacoes_lista
        "salario do joao"                -> vai para _try_route_historico
    """
    if not _is_receitas_query(normalized_text):
        return None

    filtros = _extract_receitas_filters_from_query(normalized_text)
    tipo_de_dado = _extract_receitas_tipo_de_dado(normalized_text)

    if any(keyword in normalized_text for keyword in ("maiores", "maior", "top")):
        ordenar_por = (
            "valor_lancado" if tipo_de_dado == "lancamento" else "valor_recebido"
        )
        campos = (
            [
                "ano",
                "mes",
                "tipo",
                "tributo",
                "valor_lancado",
                "valor_em_divida_ativa",
                "valor_em_cobranca_judicial",
            ]
            if tipo_de_dado == "lancamento"
            else [
                "ano",
                "mes",
                "unidade_responsavel",
                "categoria",
                "valor_recebido",
                "origem_do_recurso",
            ]
        )
        return RouteDecision(
            domain="receitas",
            operation_type="consulta_lista",
            tool_name="consultar_receitas",
            tool_kwargs={
                "filtros": filtros,
                "ordenar_por": ordenar_por,
                "ordem": "desc",
                "limite": _extract_limit(normalized_text, default=10),
                "campos": campos,
            },
            tags=["scope:public", "domain:receitas", "shape:lookup"],
            confident=True,
        )

    if filtros or any(
        keyword in normalized_text
        for keyword in ("lista", "liste", "quais", "mostre", "detalhe")
    ):
        limite = (
            100
            if any(keyword in normalized_text for keyword in ("todas", "todos"))
            else 10
        )
        return RouteDecision(
            domain="receitas",
            operation_type="consulta_lista",
            tool_name="consultar_receitas",
            tool_kwargs={
                "filtros": filtros,
                "ordenar_por": "data",
                "ordem": "desc",
                "limite": limite,
            },
            tags=["scope:public", "domain:receitas", "shape:lookup"],
            confident=True,
        )

    return None
