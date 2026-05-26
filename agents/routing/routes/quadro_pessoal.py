"""Regras de roteamento para quadro de pessoal."""

from __future__ import annotations

from agents.routing.constants import QUADRO_PESSOAL_DOMAIN_KEYWORDS
from agents.routing.extractors import _contains_any, _extract_limit, _extract_year
from agents.routing.models import RouteDecision


def _is_quadro_pessoal_query(normalized_text: str) -> bool:
    return _contains_any(normalized_text, QUADRO_PESSOAL_DOMAIN_KEYWORDS)


def _extract_quadro_filters(normalized_text: str) -> dict[str, object]:
    filtros: dict[str, object] = {}
    if year := _extract_year(normalized_text):
        filtros["ano"] = year
    if "saude" in normalized_text or "fumusa" in normalized_text:
        filtros["origem"] = "saude"
    elif "prefeitura" in normalized_text:
        filtros["origem"] = "prefeitura"
    if "comissionado" in normalized_text:
        filtros["regime"] = "comissionado"
    elif "contrato" in normalized_text:
        filtros["regime"] = "contrato"
    elif "efetivo" in normalized_text:
        filtros["regime"] = "efetivo"
    elif "aposentado" in normalized_text:
        filtros["regime"] = "aposentado"
    elif "temporario" in normalized_text:
        filtros["regime"] = "temporario"
    return filtros


def _try_route_quadro_pessoal_agregacao(
    normalized_text: str,
) -> RouteDecision | None:
    if not _is_quadro_pessoal_query(normalized_text):
        return None
    if not any(
        keyword in normalized_text
        for keyword in ("quantas", "quantos", "total", "por ", "maior", "maiores")
    ):
        return None

    if "criadas" in normalized_text:
        metrica = "soma_vagas_criadas"
    elif "saldo" in normalized_text:
        metrica = "saldo_vagas"
    else:
        metrica = "soma_vagas_preenchidas"

    if "por regime" in normalized_text:
        agrupar_por = "regime"
    elif "por mes" in normalized_text:
        agrupar_por = "mes"
    elif "por origem" in normalized_text:
        agrupar_por = "origem"
    else:
        agrupar_por = None

    return RouteDecision(
        domain="quadro_pessoal",
        operation_type="agregacao_ranking",
        tool_name="agregar_quadro_pessoal",
        tool_kwargs={
            "filtros": _extract_quadro_filters(normalized_text),
            "agrupar_por": agrupar_por,
            "metrica": metrica,
            "ordenar_por": "metrica",
            "ordem": "desc",
            "limite": _extract_limit(normalized_text, default=10),
        },
        tags=["scope:public", "domain:quadro_pessoal", "shape:aggregate"],
        confident=True,
    )


def _try_route_quadro_pessoal_lista(normalized_text: str) -> RouteDecision | None:
    if not _is_quadro_pessoal_query(normalized_text):
        return None
    return RouteDecision(
        domain="quadro_pessoal",
        operation_type="consulta_lista",
        tool_name="consultar_quadro_pessoal",
        tool_kwargs={
            "filtros": _extract_quadro_filters(normalized_text),
            "ordenar_por": "mes_de_referencia",
            "ordem": "asc",
            "limite": 100
            if any(keyword in normalized_text for keyword in ("todos", "todas"))
            else _extract_limit(normalized_text, default=10),
        },
        tags=["scope:public", "domain:quadro_pessoal", "shape:lookup"],
        confident=True,
    )
