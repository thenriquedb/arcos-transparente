"""Schemas base das tools de licitacoes."""

from __future__ import annotations

from agents.tools.sql_tools.shared.base import SqlToolBaseSchema


class LicitacoesToolBaseSchema(SqlToolBaseSchema):
    """Base de saneamento para entrada e saida das tools de licitacoes."""
