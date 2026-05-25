"""Schemas de saida compartilhados pelas tools amplas de servidores."""

from __future__ import annotations

from datetime import date

from .base import ServidoresToolBaseSchema


class ServidorToolItem(ServidoresToolBaseSchema):
    id: int
    nome: str
    cargo: str
    secretaria: str
    salario_base: float | None = None
    mes_de_referencia: date
