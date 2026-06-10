"""Regras de roteamento para diarias."""

from __future__ import annotations

import re

from agents.routing.constants import DIARIAS_DOMAIN_KEYWORDS
from agents.routing.models import RouteDecision
from agents.routing.routes.beneficiario_spend import (
    BeneficiarioSpendRouteConfig,
    try_route_beneficiario_spend_agregacao,
    try_route_beneficiario_spend_lista,
)

_DIARIAS_ROUTE_CONFIG = BeneficiarioSpendRouteConfig(
    domain="diarias",
    domain_keywords=DIARIAS_DOMAIN_KEYWORDS,
    beneficiario_pattern=re.compile(r"\bdiarias\b\s+(?:do|da|de)\s+([a-z0-9 .&/-]+?)(?=\s+\bem\b\s+\d{4}\b|\?|$)"),
    aggregate_tool="agregar_diarias",
    list_tool="consultar_diarias",
)


def _try_route_diarias_agregacao(normalized_text: str) -> RouteDecision | None:
    return try_route_beneficiario_spend_agregacao(_DIARIAS_ROUTE_CONFIG, normalized_text)


def _try_route_diarias_lista(normalized_text: str) -> RouteDecision | None:
    return try_route_beneficiario_spend_lista(_DIARIAS_ROUTE_CONFIG, normalized_text)
