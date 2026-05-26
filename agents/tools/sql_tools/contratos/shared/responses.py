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


class ContratoDespesaOrcamentariaToolItem(ContratosToolBaseSchema):
    ordem: int
    unidade_gestora: str | None = None
    exercicio: int | None = None
    orgao: str | None = None
    unidade: str | None = None
    departamento: str | None = None
    fonte_recurso: str | None = None
    natureza_despesa_rubrica: str | None = None
    classificacao_da_despesa: str | None = None
    valor_despesa: float | None = None


class ContratoItemAdquiridoToolItem(ContratosToolBaseSchema):
    ordem: int
    unidade_gestora: str | None = None
    numero_lote: str | None = None
    numero_item: str | None = None
    identificacao: str | None = None
    quantidade: float | None = None
    valor_unitario: float | None = None
    valor_total: float | None = None
