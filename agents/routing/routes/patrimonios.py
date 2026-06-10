"""Regras de roteamento para patrimonios."""

from __future__ import annotations

import re

from agents.routing.constants import PATRIMONIOS_DOMAIN_KEYWORDS
from agents.routing.extractors import _contains_any, _extract_limit, _extract_year
from agents.routing.models import RouteDecision


def _is_patrimonios_query(normalized_text: str) -> bool:
    return _contains_any(normalized_text, PATRIMONIOS_DOMAIN_KEYWORDS)


def _extract_patrimonios_filters(normalized_text: str) -> dict[str, object]:
    filtros: dict[str, object] = {}
    if year := _extract_year(normalized_text):
        filtros["data_aquisicao_inicio"] = f"{year}-01-01"
        filtros["data_aquisicao_fim"] = f"{year}-12-31"

    placa_match = re.search(r"\bplaca\b\s+([a-z0-9_-]+)", normalized_text)
    if placa_match is not None:
        filtros["placa"] = placa_match.group(1)

    if "educacao" in normalized_text:
        filtros["localizacao"] = "educacao"
    elif "saude" in normalized_text:
        filtros["localizacao"] = "saude"
    elif "fazenda" in normalized_text:
        filtros["localizacao"] = "fazenda"

    if "normal" in normalized_text:
        filtros["status"] = "normal"
    if "compra" in normalized_text:
        filtros["tipo_ingresso"] = "compra"

    return filtros


def _try_route_patrimonios_agregacao(normalized_text: str) -> RouteDecision | None:
    if not _is_patrimonios_query(normalized_text):
        return None
    if not any(keyword in normalized_text for keyword in ("quanto", "total", "maior", "maiores", "por ", "quantos")):
        return None

    if "valor" in normalized_text:
        metrica = "soma_valor_atualizado"
    else:
        metrica = "contagem"

    if "por localizacao" in normalized_text or "por setor" in normalized_text:
        agrupar_por = "localizacao"
    elif "por status" in normalized_text:
        agrupar_por = "status"
    elif "por classificacao" in normalized_text:
        agrupar_por = "classificacao"
    elif "por tipo" in normalized_text:
        agrupar_por = "tipo_ingresso"
    else:
        agrupar_por = None

    return RouteDecision(
        domain="patrimonios",
        operation_type="agregacao_ranking",
        tool_name="agregar_patrimonios",
        tool_kwargs={
            "filtros": _extract_patrimonios_filters(normalized_text),
            "agrupar_por": agrupar_por,
            "metrica": metrica,
            "ordenar_por": "metrica",
            "ordem": "desc",
            "limite": _extract_limit(normalized_text, default=10),
        },
        tags=["scope:public", "domain:patrimonios", "shape:aggregate"],
        confident=True,
    )


def _try_route_patrimonios_lista(normalized_text: str) -> RouteDecision | None:
    if not _is_patrimonios_query(normalized_text):
        return None
    return RouteDecision(
        domain="patrimonios",
        operation_type="consulta_lista",
        tool_name="consultar_patrimonios",
        tool_kwargs={
            "filtros": _extract_patrimonios_filters(normalized_text),
            "ordenar_por": "valor_atualizado"
            if any(keyword in normalized_text for keyword in ("maior", "maiores"))
            else "data_aquisicao",
            "ordem": "desc",
            "limite": 100
            if any(keyword in normalized_text for keyword in ("todos", "todas"))
            else _extract_limit(normalized_text, default=10),
        },
        tags=["scope:public", "domain:patrimonios", "shape:lookup"],
        confident=True,
    )
