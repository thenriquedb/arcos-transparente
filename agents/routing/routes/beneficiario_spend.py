"""Fábrica de rotas para domínios de gasto por beneficiário (diárias, passagens).

Os dois domínios compartilham exatamente a mesma forma de roteamento: filtros
por ano/origem/beneficiário, agregação por métrica de empenho/liquidação/pagamento
e listagem ordenada por valor ou período. Cada domínio fornece apenas a sua
configuração; a lógica vive uma única vez aqui.
"""

from __future__ import annotations

from dataclasses import dataclass, field
import re

from agents.routing.extractors import _contains_any, _extract_limit, _extract_year
from agents.routing.models import RouteDecision

_AGGREGATION_SIGNAL_KEYWORDS = (
    "quanto",
    "total",
    "maior",
    "maiores",
    "por ",
    "quantas",
)

_METRIC_CUES: tuple[tuple[str, str], ...] = (
    ("quantas", "contagem"),
    ("empenhado", "soma_valor_empenhado"),
    ("anulado", "soma_valor_anulado"),
    ("liquidado", "soma_valor_liquidado"),
)

_BASE_GROUP_BY_CUES: tuple[tuple[tuple[str, ...], str], ...] = (
    (("por beneficiario", "maiores"), "beneficiario"),
    (("por mes", "mes a mes"), "mes"),
    (("por origem",), "origem"),
    (("por unidade", "por unidade gestora"), "unidade_gestora"),
)


@dataclass(frozen=True, slots=True)
class BeneficiarioSpendRouteConfig:
    """Configuração de um domínio de gasto por beneficiário."""

    domain: str
    domain_keywords: tuple[str, ...]
    beneficiario_pattern: re.Pattern[str]
    aggregate_tool: str
    list_tool: str
    extra_group_by_cues: tuple[tuple[tuple[str, ...], str], ...] = field(
        default_factory=tuple
    )


def _is_domain_query(
    config: BeneficiarioSpendRouteConfig, normalized_text: str
) -> bool:
    return _contains_any(normalized_text, config.domain_keywords)


def extract_beneficiario_spend_filters(
    config: BeneficiarioSpendRouteConfig, normalized_text: str
) -> dict[str, object]:
    """Extrai ano, origem e beneficiário citados na pergunta."""

    filtros: dict[str, object] = {}
    if year := _extract_year(normalized_text):
        filtros["ano"] = year
    if "saude" in normalized_text or "fumusa" in normalized_text:
        filtros["origem"] = "saude"
    elif "prefeitura" in normalized_text:
        filtros["origem"] = "prefeitura"
    elif "camara" in normalized_text:
        filtros["origem"] = "camara"

    beneficiario_match = config.beneficiario_pattern.search(normalized_text)
    if beneficiario_match is not None:
        filtros["beneficiario"] = " ".join(beneficiario_match.group(1).split())

    return filtros


def _extract_metric(normalized_text: str) -> str:
    for cue, metrica in _METRIC_CUES:
        if cue in normalized_text:
            return metrica
    return "soma_valor_pago"


def _extract_group_by(
    config: BeneficiarioSpendRouteConfig, normalized_text: str
) -> str | None:
    for cues, group in _BASE_GROUP_BY_CUES + config.extra_group_by_cues:
        if any(cue in normalized_text for cue in cues):
            return group
    return None


def try_route_beneficiario_spend_agregacao(
    config: BeneficiarioSpendRouteConfig, normalized_text: str
) -> RouteDecision | None:
    """Roteia totais, contagens e rankings do domínio configurado."""

    if not _is_domain_query(config, normalized_text):
        return None
    if not any(keyword in normalized_text for keyword in _AGGREGATION_SIGNAL_KEYWORDS):
        return None

    return RouteDecision(
        domain=config.domain,
        operation_type="agregacao_ranking",
        tool_name=config.aggregate_tool,
        tool_kwargs={
            "filtros": extract_beneficiario_spend_filters(config, normalized_text),
            "agrupar_por": _extract_group_by(config, normalized_text),
            "metrica": _extract_metric(normalized_text),
            "ordenar_por": "metrica",
            "ordem": "desc",
            "limite": _extract_limit(normalized_text, default=10),
        },
        tags=["scope:public", f"domain:{config.domain}", "shape:aggregate"],
        confident=True,
    )


def try_route_beneficiario_spend_lista(
    config: BeneficiarioSpendRouteConfig, normalized_text: str
) -> RouteDecision | None:
    """Roteia listagens detalhadas do domínio configurado."""

    if not _is_domain_query(config, normalized_text):
        return None
    return RouteDecision(
        domain=config.domain,
        operation_type="consulta_lista",
        tool_name=config.list_tool,
        tool_kwargs={
            "filtros": extract_beneficiario_spend_filters(config, normalized_text),
            "ordenar_por": "valor_pago"
            if any(keyword in normalized_text for keyword in ("maior", "maiores"))
            else "periodo_fim",
            "ordem": "desc",
            "limite": 100
            if any(keyword in normalized_text for keyword in ("todos", "todas"))
            else _extract_limit(normalized_text, default=10),
        },
        tags=["scope:public", f"domain:{config.domain}", "shape:lookup"],
        confident=True,
    )
