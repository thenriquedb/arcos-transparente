"""Schemas de saida compartilhados pelas tools de folha."""

from __future__ import annotations

from datetime import date

from pydantic import Field

from .base import FolhaPagamentoToolBaseSchema


class PagamentoMensalItem(FolhaPagamentoToolBaseSchema):
    ano: int
    mes_num: int
    mes_nome: str
    cargo: str | None = None
    setor: str | None = None
    salario_base: float | None = None
    ganhos: float | None = None
    adicionais: float | None = None
    total_bruto: float | None = None
    descontos: float | None = None
    valor_recebido: float | None = None


class HistoricoPagamentosServidorItem(FolhaPagamentoToolBaseSchema):
    folha_servidor_id: int
    nome: str
    cargo_atual: str | None = None
    setor_atual: str | None = None
    mes_de_referencia_do_servidor: date | None = None
    total_meses_considerados: int
    pagamentos: list[PagamentoMensalItem] = Field(default_factory=list)
    total_recebido: float | None = None
    nota: str | None = None


class HistoricoPagamentosServidorResponse(FolhaPagamentoToolBaseSchema):
    query: str | None = None
    total: int
    resultados: list[HistoricoPagamentosServidorItem] = Field(default_factory=list)
    mensagem: str | None = None
    sugestao: str | None = None
