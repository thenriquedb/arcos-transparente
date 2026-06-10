"""Regras de roteamento para o dominio de estoques."""

from __future__ import annotations

import calendar
from datetime import date
import re

from agents.routing.constants import ESTOQUES_DOMAIN_KEYWORDS
from agents.routing.extractors import (
    _contains_any,
    _contains_term,
    _extract_limit,
    _extract_year,
)
from agents.routing.models import RouteDecision
from shared.utils.validation import parse_month


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
    "comum",
    "comuns",
    "frequente",
    "frequentes",
    "maior",
    "maiores",
    "mais",
    "ranking",
    "quantas",
    "quantos",
)
_ESTOQUES_ENTITY_TERMS = (
    "material",
    "materiais",
    "item",
    "itens",
    "produto",
    "produtos",
)
_ESTOQUES_GENERIC_SIGNAL_TERMS = (
    "saldo",
    "entrada",
    "entradas",
    "saida",
    "saidas",
    "movimentacao",
    "movimentacoes",
    "almoxarifado",
)
_ESTOQUES_VALUE_SIGNAL_TERMS = (
    "valor",
    "valores",
    "custo",
    "custos",
    "financeiro",
    "financeira",
    "reais",
)
_MONTH_RANGE_PATTERN = re.compile(
    r"\b(?:em|no\s+mes\s+de|durante)\s+"
    r"(janeiro|fevereiro|marco|abril|maio|junho|julho|agosto|setembro|outubro|novembro|dezembro)"
    r"\s+de\s+(\d{4})\b"
)


def _is_estoques_query(normalized_text: str) -> bool:
    if _contains_any(normalized_text, ESTOQUES_DOMAIN_KEYWORDS):
        return True

    has_entity = any(
        _contains_term(normalized_text, term) for term in _ESTOQUES_ENTITY_TERMS
    )
    has_stock_signal = any(
        _contains_term(normalized_text, term) for term in _ESTOQUES_GENERIC_SIGNAL_TERMS
    )
    return has_entity and has_stock_signal


def _has_estoques_aggregate_intent(normalized_text: str) -> bool:
    return any(keyword in normalized_text for keyword in _ESTOQUES_AGGREGATION_KEYWORDS)


def _is_estoques_movement_history_query(normalized_text: str) -> bool:
    if any(
        keyword in normalized_text
        for keyword in (
            "requisicao",
            "requisicoes",
            "aplicacao imediata",
            "nota fiscal de compra",
        )
    ):
        return True
    if "historico" in normalized_text:
        return True
    if any(keyword in normalized_text for keyword in _ESTOQUES_MOVEMENT_KEYWORDS):
        return not _has_estoques_aggregate_intent(normalized_text)
    return False


def _extract_month_date_range(normalized_text: str) -> tuple[date, date] | None:
    match = _MONTH_RANGE_PATTERN.search(normalized_text)
    if match is None:
        return None

    month = parse_month(match.group(1))
    year = int(match.group(2))
    if month is None:
        return None

    last_day = calendar.monthrange(year, month)[1]
    return date(year, month, 1), date(year, month, last_day)


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
    if any(
        signal in normalized_text
        for signal in (
            "entrada",
            "entradas",
            "saida",
            "saidas",
            "movimentacao",
            "movimentacoes",
        )
    ) and (month_range := _extract_month_date_range(normalized_text)):
        filtros["data_movimento_inicio"], filtros["data_movimento_fim"] = month_range
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


_ESTOQUES_MOVEMENT_SCOPE_FILTER_KEYS = (
    "data_movimento_inicio",
    "data_movimento_fim",
    "tipo_movimento",
    "unidade_gestora",
    "almoxarifado",
    "localizacao",
    "classificacao",
)
_ESTOQUES_QUANTITY_UNIT_TERMS = ("quantidade", "itens", "unidades")
_ESTOQUES_RANKING_TERMS = ("maior", "maiores", "ranking", "mais")


def _extract_estoques_flow_metric(
    normalized_text: str,
    flow: str,
    *,
    aggregate_ranking_intent: bool,
    mentions_material_entity: bool,
    mentions_value: bool,
) -> str | None:
    """Resolve a métrica de entrada/saída entre quantidade e valor."""

    if flow not in normalized_text:
        return None
    if any(token in normalized_text for token in _ESTOQUES_QUANTITY_UNIT_TERMS):
        return f"soma_{flow}_quantidade"
    if aggregate_ranking_intent and mentions_material_entity and not mentions_value:
        return f"soma_{flow}_quantidade"
    return f"soma_{flow}_valor"


def _extract_estoques_metric(normalized_text: str, filtros: dict[str, object]) -> str:
    """Escolhe a métrica do agregado a partir dos sinais da pergunta."""

    aggregate_ranking_intent = any(
        token in normalized_text for token in _ESTOQUES_RANKING_TERMS
    )
    mentions_material_entity = any(
        _contains_term(normalized_text, term) for term in _ESTOQUES_ENTITY_TERMS
    )
    mentions_value = any(
        _contains_term(normalized_text, term) for term in _ESTOQUES_VALUE_SIGNAL_TERMS
    )
    mentions_quantity = any(
        _contains_term(normalized_text, term)
        for term in ("quantidade", "quantidades", "itens", "item", "unidades")
    )

    if "quantas" in normalized_text or "quantos" in normalized_text:
        metrica = "contagem"
    elif "movimentacao" in normalized_text or "movimentacoes" in normalized_text:
        metrica = (
            "soma_movimentacao_valor"
            if mentions_value
            else "soma_movimentacao_quantidade"
        )
    else:
        flow_metric = None
        for flow in ("entrada", "saida"):
            flow_metric = _extract_estoques_flow_metric(
                normalized_text,
                flow,
                aggregate_ranking_intent=aggregate_ranking_intent,
                mentions_material_entity=mentions_material_entity,
                mentions_value=mentions_value,
            )
            if flow_metric is not None:
                break
        if flow_metric is not None:
            metrica = flow_metric
        elif mentions_quantity:
            metrica = "soma_saldo_quantidade"
        else:
            metrica = "soma_saldo_valor"

    has_movement_scope = any(
        key in filtros for key in _ESTOQUES_MOVEMENT_SCOPE_FILTER_KEYS
    )
    if has_movement_scope and metrica in {"soma_saldo_quantidade", "soma_saldo_valor"}:
        metrica = (
            "soma_movimentacao_valor"
            if metrica == "soma_saldo_valor"
            else "soma_movimentacao_quantidade"
        )
    return metrica


def _extract_estoques_group_by(normalized_text: str) -> str | None:
    """Escolhe a dimensão de agrupamento citada (ou implicada) na pergunta."""

    if "por origem" in normalized_text:
        return "origem"
    if "por unidade" in normalized_text or "por unidade de medida" in normalized_text:
        return "unidade_medida"
    if "por ano" in normalized_text or "por exercicio" in normalized_text:
        return "ano"
    if "por material" in normalized_text or any(
        token in normalized_text for token in _ESTOQUES_RANKING_TERMS
    ):
        return "material"
    return None


def _try_route_estoques_agregacao(normalized_text: str) -> RouteDecision | None:
    if not _is_estoques_query(normalized_text):
        return None
    if _is_estoques_movement_history_query(normalized_text):
        return None
    if not _has_estoques_aggregate_intent(normalized_text):
        return None

    filtros = _extract_estoques_filters(normalized_text)
    metrica = _extract_estoques_metric(normalized_text, filtros)
    agrupar_por = _extract_estoques_group_by(normalized_text)

    return RouteDecision(
        domain="estoques",
        operation_type="agregacao_ranking",
        tool_name="agregar_estoques",
        tool_kwargs={
            "filtros": filtros,
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
    if _is_estoques_movement_history_query(normalized_text):
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
            "filtros": {
                k: v
                for k, v in filtros.items()
                if k != "almoxarifado" and k != "tipo_movimento"
            },
            "ordenar_por": "saldo_valor"
            if any(
                keyword in normalized_text for keyword in ("maior", "maiores", "saldo")
            )
            else "periodo_fim",
            "ordem": "desc",
            "limite": 100
            if any(keyword in normalized_text for keyword in ("todos", "todas"))
            else _extract_limit(normalized_text, default=10),
        },
        tags=["scope:public", "domain:estoques", "shape:lookup", "kind:summary"],
        confident=True,
    )
