"""Regras de roteamento para o dominio de estoques."""

from __future__ import annotations

import re

from agents.routing.constants import ESTOQUES_DOMAIN_KEYWORDS
from agents.routing.extractors import _contains_any, _extract_limit, _extract_year
from agents.routing.models import RouteDecision


_ESTOQUES_MOVEMENT_KEYWORDS = (
    "movimentacao",
    "movimentacoes",
    "requisicao",
    "requisicoes",
    "aplicacao imediata",
    "nota fiscal de compra",
    "almoxarifado",
)
_ESTOQUES_AGGREGATION_KEYWORDS = (
    "quanto",
    "total",
    "totais",
    "maior",
    "maiores",
    "ranking",
    "quantas",
    "quantos",
)


def _is_estoques_query(normalized_text: str) -> bool:
    return _contains_any(normalized_text, ESTOQUES_DOMAIN_KEYWORDS)


def _is_estoques_movement_query(normalized_text: str) -> bool:
    return any(keyword in normalized_text for keyword in _ESTOQUES_MOVEMENT_KEYWORDS)


def _extract_material_query(normalized_text: str) -> str | None:
    patterns = (
        r"\bmaterial(?:\s+de|\s+do|\s+da)?\s+([a-z0-9 .&/%()-]+?)(?=\s+\bem\b\s+\d{4}\b|\s+\bno\b\s+almoxarifado\b|\?|$)",
        r"\bestoque(?:\s+de|\s+do|\s+da)\s+([a-z0-9 .&/%()-]+?)(?=\s+\bem\b\s+\d{4}\b|\s+\bno\b\s+almoxarifado\b|\?|$)",
        r"\bsaldo(?:\s+de|\s+do|\s+da)\s+material\s+([a-z0-9 .&/%()-]+?)(?=\s+\bem\b\s+\d{4}\b|\?|$)",
    )
    ignored_values = {
        "estoque",
        "estoques",
        "material",
        "materiais",
        "almoxarifado",
        "prefeitura",
        "camara",
        "saude",
    }

    for pattern in patterns:
        match = re.search(pattern, normalized_text)
        if match is None:
            continue
        value = " ".join(match.group(1).split()).strip(" .")
        if value.startswith("almoxarifado"):
            continue
        if value and value not in ignored_values:
            return value
    return None


def _extract_estoques_filters(normalized_text: str) -> dict[str, object]:
    filtros: dict[str, object] = {}
    if year := _extract_year(normalized_text):
        filtros["ano"] = year
    if ("saude" in normalized_text or "fumusa" in normalized_text) and (
        "almoxarifado" not in normalized_text
    ):
        filtros["origem"] = "saude"
    elif "prefeitura" in normalized_text:
        filtros["origem"] = "prefeitura"
    elif "camara" in normalized_text:
        filtros["origem"] = "camara"
    elif "consolidada" in normalized_text:
        filtros["origem"] = "consolidada"

    if material := _extract_material_query(normalized_text):
        filtros["material"] = material

    almoxarifado_match = re.search(
        r"\balmoxarifado\b\s+(?:da|de|do)?\s*([a-z0-9 .&/%()-]+?)(?=\s+\bem\b\s+\d{4}\b|\?|$)",
        normalized_text,
    )
    if almoxarifado_match is not None:
        filtros["almoxarifado"] = " ".join(almoxarifado_match.group(1).split())

    if "requisicao" in normalized_text or "requisicoes" in normalized_text:
        filtros["tipo_movimento"] = "requisicao"
    elif "aplicacao imediata" in normalized_text:
        filtros["tipo_movimento"] = "aplicacao imediata"
    elif "nota fiscal de compra" in normalized_text:
        filtros["tipo_movimento"] = "nota fiscal de compra"

    return filtros


def _try_route_estoques_agregacao(normalized_text: str) -> RouteDecision | None:
    if not _is_estoques_query(normalized_text):
        return None
    if _is_estoques_movement_query(normalized_text):
        return None
    if not any(keyword in normalized_text for keyword in _ESTOQUES_AGGREGATION_KEYWORDS):
        return None

    filtros = _extract_estoques_filters(normalized_text)
    if "quantas" in normalized_text or "quantos" in normalized_text:
        metrica = "contagem"
    elif "entrada" in normalized_text and any(
        token in normalized_text for token in ("quantidade", "itens", "unidades")
    ):
        metrica = "soma_entrada_quantidade"
    elif "entrada" in normalized_text:
        metrica = "soma_entrada_valor"
    elif "saida" in normalized_text and any(
        token in normalized_text for token in ("quantidade", "itens", "unidades")
    ):
        metrica = "soma_saida_quantidade"
    elif "saida" in normalized_text:
        metrica = "soma_saida_valor"
    elif any(token in normalized_text for token in ("quantidade", "itens", "unidades")):
        metrica = "soma_saldo_quantidade"
    else:
        metrica = "soma_saldo_valor"

    if "por origem" in normalized_text:
        agrupar_por = "origem"
    elif "por unidade" in normalized_text or "por unidade de medida" in normalized_text:
        agrupar_por = "unidade_medida"
    elif "por ano" in normalized_text or "por exercicio" in normalized_text:
        agrupar_por = "ano"
    elif "por material" in normalized_text or any(
        token in normalized_text for token in ("maior", "maiores", "ranking")
    ):
        agrupar_por = "material"
    else:
        agrupar_por = None

    return RouteDecision(
        domain="estoques",
        operation_type="agregacao_ranking",
        tool_name="agregar_estoques",
        tool_kwargs={
            "filtros": {k: v for k, v in filtros.items() if k != "almoxarifado" and k != "tipo_movimento"},
            "agrupar_por": agrupar_por,
            "metrica": metrica,
            "ordenar_por": "metrica",
            "ordem": "desc",
            "limite": _extract_limit(normalized_text, default=10),
        },
        tags=["scope:public", "domain:estoques", "shape:aggregate"],
        confident=True,
    )


def _try_route_estoques_lista(normalized_text: str) -> RouteDecision | None:
    if not _is_estoques_query(normalized_text):
        return None

    filtros = _extract_estoques_filters(normalized_text)
    if _is_estoques_movement_query(normalized_text):
        return RouteDecision(
            domain="estoques",
            operation_type="consulta_lista",
            tool_name="consultar_movimentacoes_de_estoque",
            tool_kwargs={
                "filtros": filtros,
                "ordenar_por": "data_movimento",
                "ordem": "desc",
                "limite": 100
                if any(keyword in normalized_text for keyword in ("todos", "todas"))
                else _extract_limit(normalized_text, default=10),
            },
            tags=["scope:public", "domain:estoques", "shape:lookup", "kind:movements"],
            confident=True,
        )

    return RouteDecision(
        domain="estoques",
        operation_type="consulta_lista",
        tool_name="consultar_estoques",
        tool_kwargs={
            "filtros": {k: v for k, v in filtros.items() if k != "almoxarifado" and k != "tipo_movimento"},
            "ordenar_por": "saldo_valor"
            if any(keyword in normalized_text for keyword in ("maior", "maiores", "saldo"))
            else "periodo_fim",
            "ordem": "desc",
            "limite": 100
            if any(keyword in normalized_text for keyword in ("todos", "todas"))
            else _extract_limit(normalized_text, default=10),
        },
        tags=["scope:public", "domain:estoques", "shape:lookup", "kind:summary"],
        confident=True,
    )
