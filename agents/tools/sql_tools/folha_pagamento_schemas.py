"""Schemas Pydantic para tools SQL de folha de pagamento."""

from __future__ import annotations

from datetime import date
from typing import Any

from pydantic import BaseModel, ConfigDict, Field, field_validator

from shared.utils.validation import clean_text, normalize_limit


class _FolhaPagamentoToolBaseSchema(BaseModel):
    """Base de saneamento para entrada e saida das tools de folha."""

    model_config = ConfigDict(extra="ignore")


class BuscarHistoricoPagamentosServidorParams(_FolhaPagamentoToolBaseSchema):
    nome: str | None
    limite: int = 10
    max_meses: int = 24

    @field_validator("nome", mode="before")
    @classmethod
    def _normalize_nome(cls, value: Any) -> str | None:
        return clean_text(value)

    @field_validator("limite", mode="before")
    @classmethod
    def _normalize_limite(cls, value: Any) -> int:
        return normalize_limit(value, maximum=50)

    @field_validator("max_meses", mode="before")
    @classmethod
    def _normalize_max_meses(cls, value: Any) -> int:
        return normalize_limit(value, maximum=48)


class PagamentoMensalItem(_FolhaPagamentoToolBaseSchema):
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


class HistoricoPagamentosServidorItem(_FolhaPagamentoToolBaseSchema):
    folha_servidor_id: int
    nome: str
    cargo_atual: str | None = None
    setor_atual: str | None = None
    mes_de_referencia_do_servidor: date | None = None
    total_meses_considerados: int
    pagamentos: list[PagamentoMensalItem] = Field(default_factory=list)
    total_recebido: float | None = None
    nota: str | None = None


class HistoricoPagamentosServidorResponse(_FolhaPagamentoToolBaseSchema):
    query: str | None = None
    total: int
    resultados: list[HistoricoPagamentosServidorItem] = Field(default_factory=list)
    mensagem: str | None = None
    sugestao: str | None = None
