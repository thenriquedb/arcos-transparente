"""Regras de roteamento para eleitos."""

from __future__ import annotations

import re

from agents.routing.constants import ELEITOS_DOMAIN_KEYWORDS
from agents.routing.extractors import _contains_any, _extract_limit, _extract_year
from agents.routing.models import RouteDecision


def _is_eleitos_query(normalized_text: str) -> bool:
    if _contains_any(normalized_text, ELEITOS_DOMAIN_KEYWORDS):
        return True
    return (
        re.search(
            r"\b(?:quem e|biografia de|contato de|email de|telefone de)\s+([a-z]{2,}(?:\s+[a-z]{2,}){1,4})\b",
            normalized_text,
        )
        is not None
    )


def _extract_eleitos_filters(normalized_text: str) -> dict[str, object]:
    filtros: dict[str, object] = {}

    if "prefeito" in normalized_text or "prefeita" in normalized_text:
        filtros["tipo_politico"] = "prefeito"
    elif "vereador" in normalized_text:
        filtros["tipo_politico"] = "vereador"
    elif "viceprefeito" in normalized_text:
        filtros["tipo_politico"] = "vice-prefeito"

    if year := _extract_year(normalized_text):
        filtros["ano"] = year

    if "em exercicio" in normalized_text:
        filtros["em_exercicio"] = True
    elif "encerrado" in normalized_text or "encerrada" in normalized_text:
        filtros["status_mandato"] = "encerrado"

    partido_match = re.search(r"\bpartido\b\s+([a-z0-9]+)\b", normalized_text)
    if partido_match is not None:
        filtros["partido"] = partido_match.group(1)

    nome_match = re.search(
        r"\b(?:quem e|biografia de|contato de|email de|telefone de)\s+([a-z]{2,}(?:\s+[a-z]{2,}){1,4})\b",
        normalized_text,
    )
    if nome_match is not None:
        filtros["nome"] = nome_match.group(1)

    return filtros


def _try_route_eleitos_lista(normalized_text: str) -> RouteDecision | None:
    if not _is_eleitos_query(normalized_text):
        return None

    return RouteDecision(
        domain="eleitos",
        operation_type="consulta_lista",
        tool_name="consultar_eleitos",
        tool_kwargs={
            "filtros": _extract_eleitos_filters(normalized_text),
            "ordenar_por": "mandato_inicio",
            "ordem": "desc",
            "limite": 100
            if any(keyword in normalized_text for keyword in ("todos", "todas"))
            else _extract_limit(normalized_text, default=10),
        },
        tags=["scope:public", "domain:eleitos", "shape:lookup"],
        confident=True,
    )
