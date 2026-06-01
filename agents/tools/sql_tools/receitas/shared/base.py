"""Base Pydantic para tools de receitas."""

from __future__ import annotations

from agents.tools.sql_tools.shared.base import SqlToolBaseSchema


class ReceitasToolBaseSchema(SqlToolBaseSchema):
    """Config comum dos schemas das tools de receitas."""
