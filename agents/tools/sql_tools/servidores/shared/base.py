"""Schemas base das tools de servidores."""

from __future__ import annotations

from agents.tools.sql_tools.shared.base import SqlToolBaseSchema


class ServidoresToolBaseSchema(SqlToolBaseSchema):
    """Base de saneamento para entrada e saida das tools de servidores."""
