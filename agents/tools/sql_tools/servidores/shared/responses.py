"""Schemas de saida compartilhados pelas tools amplas de servidores."""

from __future__ import annotations

from datetime import date

from agents.tools.sql_tools.shared.base import SqlToolBaseSchema


class ServidorToolItem(SqlToolBaseSchema):
    """Item individual retornado pela tool."""

    id: int
    nome: str
    cargo: str
    secretaria: str
    salario_base: float | None = None
    mes_de_referencia: date
