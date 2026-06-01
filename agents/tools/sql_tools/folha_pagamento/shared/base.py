"""Schemas base das tools de folha de pagamento."""

from __future__ import annotations

from agents.tools.sql_tools.shared.base import SqlToolBaseSchema


class FolhaPagamentoToolBaseSchema(SqlToolBaseSchema):
    """Base de saneamento para entrada e saida das tools de folha."""
