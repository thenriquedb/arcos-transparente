"""Base Pydantic para tools de planejamento."""

from __future__ import annotations

from agents.tools.sql_tools.shared.base import SqlToolBaseSchema


class PlanejamentoToolBaseSchema(SqlToolBaseSchema):
    """Config comum dos schemas das tools de planejamento."""
