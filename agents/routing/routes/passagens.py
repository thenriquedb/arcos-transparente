"""Regras de roteamento para passagens."""

from __future__ import annotations

import re

from agents.routing.constants import PASSAGENS_DOMAIN_KEYWORDS
from agents.routing.extractors import _contains_any, _extract_limit, _extract_year
from agents.routing.models import RouteDecision


def _is_passagens_query(normalized_text: str) -> bool:
    return _contains_any(normalized_text, PASSAGENS_DOMAIN_KEYWORDS)


def _extract_passagens_filters(normalized_text: str) -> dict[str, object]:
    filtros: dict[str, object] = {}
    if year := _extract_year(normalized_text):
        filtros["ano"] = year
    if "saude" in normalized_text or "fumusa" in normalized_text:
        filtros["origem"] = "saude"
    elif "prefeitura" in normalized_text:
        filtros["origem"] = "prefeitura"
    elif "camara" in normalized_text:
        filtros["origem"] = "camara"

    beneficiario_match = re.search(
        r"\b(?:passagens?|locomocao)\b\s+(?:do|da|de)\s+([a-z0-9 .&/-]+?)(?=\s+\bem\b\s+\d{4}\b|\?|$)",
        normalized_text,
    )
    if beneficiario_match is not None:
        filtros["beneficiario"] = " ".join(beneficiario_match.group(1).split())

    return filtros


def _try_route_passagens_agregacao(normalized_text: str) -> RouteDecision | None:
    if not _is_passagens_query(normalized_text):
        return None
    if not any(
        keyword in normalized_text
        for keyword in ("quanto", "total", "maior", "maiores", "por ", "quantas")
    ):
        return None

    filtros = _extract_passagens_filters(normalized_text)
    if "quantas" in normalized_text:
        metrica = "contagem"
    elif "empenhado" in normalized_text:
        metrica = "soma_valor_empenhado"
    elif "anulado" in normalized_text:
        metrica = "soma_valor_anulado"
    elif "liquidado" in normalized_text:
        metrica = "soma_valor_liquidado"
    else:
        metrica = "soma_valor_pago"

    if "por beneficiario" in normalized_text or "maiores" in normalized_text:
        agrupar_por = "beneficiario"
    elif "por mes" in normalized_text or "mes a mes" in normalized_text:
        agrupar_por = "mes"
    elif "por origem" in normalized_text:
        agrupar_por = "origem"
    elif "por unidade" in normalized_text or "por unidade gestora" in normalized_text:
        agrupar_por = "unidade_gestora"
    elif "por categoria" in normalized_text or "por tipo" in normalized_text:
        agrupar_por = "categoria"
    else:
        agrupar_por = None

    return RouteDecision(
        domain="passagens",
        operation_type="agregacao_ranking",
        tool_name="agregar_passagens",
        tool_kwargs={
            "filtros": filtros,
            "agrupar_por": agrupar_por,
            "metrica": metrica,
            "ordenar_por": "metrica",
            "ordem": "desc",
            "limite": _extract_limit(normalized_text, default=10),
        },
        tags=["scope:public", "domain:passagens", "shape:aggregate"],
        confident=True,
    )


def _try_route_passagens_lista(normalized_text: str) -> RouteDecision | None:
    if not _is_passagens_query(normalized_text):
        return None
    filtros = _extract_passagens_filters(normalized_text)
    return RouteDecision(
        domain="passagens",
        operation_type="consulta_lista",
        tool_name="consultar_passagens",
        tool_kwargs={
            "filtros": filtros,
            "ordenar_por": "valor_pago"
            if any(keyword in normalized_text for keyword in ("maior", "maiores"))
            else "periodo_fim",
            "ordem": "desc",
            "limite": 100
            if any(keyword in normalized_text for keyword in ("todos", "todas"))
            else _extract_limit(normalized_text, default=10),
        },
        tags=["scope:public", "domain:passagens", "shape:lookup"],
        confident=True,
    )
