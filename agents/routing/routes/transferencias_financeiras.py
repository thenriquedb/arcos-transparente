"""Regras de roteamento para transferencias financeiras."""

from __future__ import annotations

import re

from agents.routing.constants import TRANSFERENCIAS_FINANCEIRAS_DOMAIN_KEYWORDS
from agents.routing.extractors import (
    _contains_any_term,
    _extract_limit,
    _extract_year,
)
from agents.routing.models import RouteDecision


def _is_transferencias_financeiras_query(normalized_text: str) -> bool:
    return _contains_any_term(
        normalized_text,
        TRANSFERENCIAS_FINANCEIRAS_DOMAIN_KEYWORDS,
    )


def _is_emenda_query(normalized_text: str) -> bool:
    return _contains_any_term(
        normalized_text,
        (
            "emenda",
            "emendas",
            "ementa",
            "ementas",
            "parlamentar",
            "parlamentares",
        ),
    )


def _extract_transferencias_financeiras_filters(
    normalized_text: str,
) -> dict[str, object]:
    filtros: dict[str, object] = {}
    emenda_query = _is_emenda_query(normalized_text)
    filtros["tipo_registro"] = "emenda" if emenda_query else "movimentacao"

    if year := _extract_year(normalized_text):
        filtros["ano"] = year

    identificador = re.search(r"\b(20\d{2}/[a-z0-9-]+)\b", normalized_text)
    if identificador is not None:
        filtros["ano_numero"] = identificador.group(1)

    if emenda_query:
        if "saude" in normalized_text:
            filtros["funcao"] = "saude"
        elif "assistencia social" in normalized_text:
            filtros["funcao"] = "assistencia social"
        elif "urbanismo" in normalized_text:
            filtros["funcao"] = "urbanismo"

        autor_match = re.search(
            r"\b(?:emendas?|ementas?)\s+(?:do|da|de)\s+([a-z0-9 .&/-]+?)(?=\s+\bem\b\s+\d{4}\b|\?|$)",
            normalized_text,
        )
        if autor_match is None:
            autor_match = re.search(
                r"\bautor(?:a)?\s+([a-z0-9 .&/-]+?)(?=\s+\bem\b\s+\d{4}\b|\?|$)",
                normalized_text,
            )
        if autor_match is None:
            autor_match = re.search(
                r"\b(?:quanto|quantos|quantas)\s+(?:o|a)?\s*([a-z0-9 .&/-]+?)\s+(?:enviou|destinou|mandou|indicou)\s+de\s+(?:emendas?|ementas?)\b",
                normalized_text,
            )
        if autor_match is not None:
            filtros["autor"] = " ".join(autor_match.group(1).split())
        return filtros

    if "prefeitura" in normalized_text:
        filtros["unidade_concessora"] = "prefeitura"
    if "camara" in normalized_text:
        filtros["unidade_recebedora"] = "camara"
    if "devolucao" in normalized_text:
        filtros["tipo_movimento"] = "devolucao"
    elif "estorno" in normalized_text:
        filtros["tipo_movimento"] = "estorno"
    elif "recebimento" in normalized_text or "repasse" in normalized_text:
        filtros["tipo_movimento"] = "recebimento"

    return filtros


def _extract_transferencias_financeiras_group_by(
    normalized_text: str,
    *,
    emenda_query: bool,
) -> str | None:
    if "por ano" in normalized_text or "ano a ano" in normalized_text:
        return "ano"

    if emenda_query:
        if any(keyword in normalized_text for keyword in ("por autor", "autores", "quem enviou", "quem destinou")):
            return "autor"
        if "por funcao" in normalized_text:
            return "funcao"
        if "por tipo" in normalized_text:
            return "tipo_emenda"
        return None

    if any(keyword in normalized_text for keyword in ("por unidade recebedora", "quem recebeu", "para quem")):
        return "unidade_recebedora"
    if any(keyword in normalized_text for keyword in ("por unidade concessora", "quem repassou", "quem transferiu")):
        return "unidade_concessora"
    if "por tipo" in normalized_text:
        return "tipo_movimento"
    if "por finalidade" in normalized_text:
        return "finalidade"
    if "por fonte" in normalized_text:
        return "fonte_recurso"
    return None


def _try_route_transferencias_financeiras_agregacao(
    normalized_text: str,
) -> RouteDecision | None:
    if not _is_transferencias_financeiras_query(normalized_text):
        return None

    emenda_query = _is_emenda_query(normalized_text)
    if "maiores" in normalized_text and any(keyword in normalized_text for keyword in ("quais", "liste", "mostre")):
        return None

    if not any(
        keyword in normalized_text
        for keyword in (
            "quanto",
            "total",
            "totais",
            "quantos",
            "quantas",
            "por ",
            "quem recebeu",
            "quem repassou",
        )
    ):
        return None

    filtros = _extract_transferencias_financeiras_filters(normalized_text)
    agrupar_por = _extract_transferencias_financeiras_group_by(
        normalized_text,
        emenda_query=emenda_query,
    )
    metrica = "contagem" if "quantos" in normalized_text or "quantas" in normalized_text else "soma_valor"

    return RouteDecision(
        domain="transferencias_financeiras",
        operation_type="agregacao_ranking",
        tool_name="agregar_transferencias_financeiras",
        tool_kwargs={
            "filtros": filtros,
            "agrupar_por": agrupar_por,
            "metrica": metrica,
            "ordenar_por": "metrica",
            "ordem": "desc",
            "limite": _extract_limit(normalized_text, default=10),
        },
        tags=[
            "scope:public",
            "domain:transferencias_financeiras",
            "shape:aggregate",
        ],
        confident=True,
    )


def _try_route_transferencias_financeiras_lista(
    normalized_text: str,
) -> RouteDecision | None:
    if not _is_transferencias_financeiras_query(normalized_text):
        return None

    filtros = _extract_transferencias_financeiras_filters(normalized_text)
    return RouteDecision(
        domain="transferencias_financeiras",
        operation_type="consulta_lista",
        tool_name="consultar_transferencias_financeiras",
        tool_kwargs={
            "filtros": filtros,
            "ordenar_por": "valor" if any(keyword in normalized_text for keyword in ("maior", "maiores")) else "data",
            "ordem": "desc",
            "limite": 100
            if any(keyword in normalized_text for keyword in ("todos", "todas"))
            else _extract_limit(normalized_text, default=10),
        },
        tags=[
            "scope:public",
            "domain:transferencias_financeiras",
            "shape:lookup",
        ],
        confident=True,
    )
