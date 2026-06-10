"""Regras de roteamento para passagens."""

from __future__ import annotations

import re

from agents.routing.constants import PASSAGENS_DOMAIN_KEYWORDS
from agents.routing.models import RouteDecision
from agents.routing.routes.beneficiario_spend import (
    BeneficiarioSpendRouteConfig,
    try_route_beneficiario_spend_agregacao,
    try_route_beneficiario_spend_lista,
)

_PASSAGENS_ROUTE_CONFIG = BeneficiarioSpendRouteConfig(
    domain="passagens",
    domain_keywords=PASSAGENS_DOMAIN_KEYWORDS,
    beneficiario_pattern=re.compile(
        r"\b(?:passagens?|locomocao)\b\s+(?:do|da|de)\s+"
        r"([a-z0-9 .&/-]+?)(?=\s+\bem\b\s+\d{4}\b|\?|$)"
    ),
    aggregate_tool="agregar_passagens",
    list_tool="consultar_passagens",
    extra_group_by_cues=((("por categoria", "por tipo"), "categoria"),),
)


def _try_route_passagens_agregacao(normalized_text: str) -> RouteDecision | None:
    return try_route_beneficiario_spend_agregacao(_PASSAGENS_ROUTE_CONFIG, normalized_text)


def _try_route_passagens_lista(normalized_text: str) -> RouteDecision | None:
    return try_route_beneficiario_spend_lista(_PASSAGENS_ROUTE_CONFIG, normalized_text)
