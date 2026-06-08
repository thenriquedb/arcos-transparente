"""Schemas Pydantic para ingestao de XMLs de `estoques`."""

from __future__ import annotations

from datetime import date
from decimal import Decimal
from typing import Any

from pydantic import BaseModel, ConfigDict, Field, field_validator, model_validator

from shared.utils.validation import (
    clean_text,
    parse_date,
    parse_int,
    parse_number,
    validate_date_period,
)


class EstoqueMovimentacaoInSchema(BaseModel):
    """Schema de uma linha de movimentacao diaria de estoque."""

    model_config = ConfigDict(extra="ignore")

    sequencia_movimentacao: int
    data_movimento: date
    tipo_movimento: str
    unidade_gestora: str | None = None
    almoxarifado: str | None = None
    localizacao: str | None = None
    classificacao: str | None = None
    quantidade: Decimal | None = None
    valor_unitario: Decimal | None = None
    valor_total: Decimal | None = None
    custo_medio: Decimal | None = None

    @field_validator("sequencia_movimentacao", mode="before")
    @classmethod
    def _normalize_sequence(cls, value: Any) -> int:
        normalized = parse_int(value)
        if normalized is None:
            raise ValueError("sequencia_movimentacao obrigatoria")
        return normalized

    @field_validator("data_movimento", mode="before")
    @classmethod
    def _normalize_date(cls, value: Any) -> date:
        parsed = parse_date(value)
        if parsed is None:
            raise ValueError("data_movimento obrigatoria")
        return parsed

    @field_validator(
        "tipo_movimento",
        "unidade_gestora",
        "almoxarifado",
        "localizacao",
        "classificacao",
        mode="before",
    )
    @classmethod
    def _normalize_text(cls, value: Any) -> str | None:
        return clean_text(value)

    @field_validator(
        "quantidade",
        "valor_unitario",
        "valor_total",
        "custo_medio",
        mode="before",
    )
    @classmethod
    def _normalize_numbers(cls, value: Any) -> Decimal | None:
        return parse_number(value)

    @model_validator(mode="after")
    def _validate_required_values(self) -> "EstoqueMovimentacaoInSchema":
        if not self.tipo_movimento:
            raise ValueError("tipo_movimento obrigatorio")
        return self


class EstoqueMaterialInSchema(BaseModel):
    """Schema do saldo sumarizado de um material de estoque."""

    model_config = ConfigDict(extra="ignore")

    arquivo_origem: str
    sequencia_material: int
    origem: str
    exercicio: int
    material: str
    unidade_medida: str
    periodo_inicio: date
    periodo_fim: date
    saldo_anterior_quantidade: Decimal | None = None
    saldo_anterior_valor: Decimal | None = None
    entrada_quantidade: Decimal | None = None
    entrada_valor: Decimal | None = None
    saida_quantidade: Decimal | None = None
    saida_valor: Decimal | None = None
    saldo_quantidade: Decimal | None = None
    saldo_valor: Decimal | None = None
    movimentacoes: list[EstoqueMovimentacaoInSchema] = Field(default_factory=list)

    @field_validator("sequencia_material", "exercicio", mode="before")
    @classmethod
    def _normalize_integers(cls, value: Any) -> int:
        normalized = parse_int(value)
        if normalized is None:
            raise ValueError("campo inteiro obrigatorio")
        return normalized

    @field_validator("periodo_inicio", "periodo_fim", mode="before")
    @classmethod
    def _normalize_dates(cls, value: Any) -> date:
        parsed = parse_date(value)
        if parsed is None:
            raise ValueError("periodo obrigatorio")
        return parsed

    @field_validator(
        "arquivo_origem",
        "origem",
        "material",
        "unidade_medida",
        mode="before",
    )
    @classmethod
    def _normalize_text(cls, value: Any) -> str | None:
        return clean_text(value)

    @field_validator(
        "saldo_anterior_quantidade",
        "saldo_anterior_valor",
        "entrada_quantidade",
        "entrada_valor",
        "saida_quantidade",
        "saida_valor",
        "saldo_quantidade",
        "saldo_valor",
        mode="before",
    )
    @classmethod
    def _normalize_numbers(cls, value: Any) -> Decimal | None:
        return parse_number(value)

    @model_validator(mode="after")
    def _validate_payload(self) -> "EstoqueMaterialInSchema":
        if not self.origem:
            self.origem = "prefeitura"
        if not self.material:
            raise ValueError("material obrigatorio")
        if not self.unidade_medida:
            raise ValueError("unidade_medida obrigatoria")
        validate_date_period(self.periodo_inicio, self.periodo_fim)
        return self
