"""Schemas de saida compartilhados pelas tools amplas de contratos."""

from __future__ import annotations

from datetime import date

from .base import ContratosToolBaseSchema


class ContratoToolItem(ContratosToolBaseSchema):
    id: int
    numero: str
    fornecedor: str
    documento_fornecedor: str
    valor: float | None = None
    data_inicio: date
    data_fim: date | None = None
    categoria: str
    secretaria: str
    descricao: str | None = None
    classificacao_da_despesa: str | None = None
