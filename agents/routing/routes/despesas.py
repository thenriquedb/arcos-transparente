"""Regras de roteamento para despesas."""

from __future__ import annotations

import re

from agents.routing.constants import DESPESAS_DOMAIN_KEYWORDS
from agents.routing.extractors import _contains_any, _extract_limit, _extract_year
from agents.routing.models import RouteDecision


def _is_despesas_query(normalized_text: str) -> bool:
    return _contains_any(normalized_text, DESPESAS_DOMAIN_KEYWORDS)


def _extract_despesas_filters(normalized_text: str) -> dict[str, object]:
    filtros: dict[str, object] = {}
    if "restos a pagar" in normalized_text or "resto a pagar" in normalized_text:
        filtros["tipo"] = "restos_a_pagar"
    elif "documento extra" in normalized_text or "documentos extras" in normalized_text:
        filtros["tipo"] = "documento_extra"
    elif "empenho" in normalized_text or "empenhos" in normalized_text:
        filtros["tipo"] = "empenho"

    if year := _extract_year(normalized_text):
        filtros["ano"] = year
    if "saude" in normalized_text or "fumusa" in normalized_text:
        filtros["origem"] = "saude"
    elif "prefeitura" in normalized_text:
        filtros["origem"] = "prefeitura"
    elif "camara" in normalized_text:
        filtros["origem"] = "camara"
    if "diaria" in normalized_text or "diarias" in normalized_text:
        filtros["descricao"] = "diaria"

    credor_match = re.search(
        r"\b(?:credor|fornecedor|pago a|pagos a|para)\b\s+([a-z0-9 .&/-]+?)(?=\s+\bem\b\s+\d{4}\b|\?|$)",
        normalized_text,
    )
    if credor_match is not None:
        filtros["credor"] = " ".join(credor_match.group(1).split())

    return filtros


def _try_route_despesas_agregacao(normalized_text: str) -> RouteDecision | None:
    if not _is_despesas_query(normalized_text):
        return None
    if not any(
        keyword in normalized_text
        for keyword in ("quanto", "total", "maior", "maiores", "por ", "quantas")
    ):
        return None

    filtros = _extract_despesas_filters(normalized_text)
    if "quantas" in normalized_text:
        metrica = "contagem"
    elif "empenhado" in normalized_text:
        metrica = "soma_valor_empenhado"
    elif "anulado" in normalized_text:
        metrica = "soma_valor_anulado"
    else:
        metrica = "soma_valor_pago"

    if "por credor" in normalized_text or "maiores credores" in normalized_text:
        agrupar_por = "credor"
    elif "por mes" in normalized_text:
        agrupar_por = "mes"
    elif "por area" in normalized_text or "por funcao" in normalized_text:
        agrupar_por = "area"
    elif "por tipo" in normalized_text:
        agrupar_por = "tipo"
    else:
        agrupar_por = None

    return RouteDecision(
        domain="despesas",
        operation_type="agregacao_ranking",
        tool_name="agregar_despesas",
        tool_kwargs={
            "filtros": filtros,
            "agrupar_por": agrupar_por,
            "metrica": metrica,
            "ordenar_por": "metrica",
            "ordem": "desc",
            "limite": _extract_limit(normalized_text, default=10),
        },
        tags=["scope:public", "domain:despesas", "shape:aggregate"],
        confident=True,
    )


def _try_route_despesas_lista(normalized_text: str) -> RouteDecision | None:
    if not _is_despesas_query(normalized_text):
        return None
    filtros = _extract_despesas_filters(normalized_text)
    return RouteDecision(
        domain="despesas",
        operation_type="consulta_lista",
        tool_name="consultar_despesas",
        tool_kwargs={
            "filtros": filtros,
            "ordenar_por": "valor_pago"
            if any(keyword in normalized_text for keyword in ("maior", "maiores"))
            else "data",
            "ordem": "desc",
            "limite": 100
            if any(keyword in normalized_text for keyword in ("todos", "todas"))
            else _extract_limit(normalized_text, default=10),
        },
        tags=["scope:public", "domain:despesas", "shape:lookup"],
        confident=True,
    )
