"""Schemas Pydantic para ingestao de relatorios `despesas-por-funcao`."""

from __future__ import annotations

from datetime import date
from decimal import Decimal
from typing import Any

from pydantic import BaseModel, ConfigDict, field_validator, model_validator

from shared.utils.text import normalize_search_text
from shared.utils.validation import (
    clean_text,
    parse_date,
    parse_decimal,
    validate_date_period,
)


class DespesaPorFuncaoInSchema(BaseModel):
    """Schema principal de uma linha agregada por funcao."""

    model_config = ConfigDict(extra="ignore")

    arquivo_origem: str
    linha_origem: int
    origem: str = "prefeitura"
    exercicio: int
    periodo_inicio: date
    periodo_fim: date
    unidade_gestora: str
    funcao: str
    dotacao_inicial: Decimal | None = None
    creditos_adicionais: Decimal | None = None
    dotacao_atualizada: Decimal | None = None
    valor_empenhado: Decimal | None = None
    valor_em_liquidacao: Decimal | None = None
    valor_liquidado: Decimal | None = None
    valor_pago: Decimal | None = None

    @field_validator("linha_origem", "exercicio", mode="before")
    @classmethod
    def _normalize_int_fields(cls, value: Any) -> int:
        if value is None:
            raise ValueError("campo inteiro obrigatorio")
        return int(value)

    @field_validator("periodo_inicio", "periodo_fim", mode="before")
    @classmethod
    def _normalize_date_fields(cls, value: Any) -> date:
        parsed = parse_date(value)
        if parsed is None:
            raise ValueError("periodo obrigatorio")
        return parsed

    @field_validator(
        "arquivo_origem",
        "origem",
        "unidade_gestora",
        "funcao",
        mode="before",
    )
    @classmethod
    def _normalize_text_fields(cls, value: Any) -> str | None:
        return clean_text(value)

    @field_validator(
        "dotacao_inicial",
        "creditos_adicionais",
        "dotacao_atualizada",
        "valor_empenhado",
        "valor_em_liquidacao",
        "valor_liquidado",
        "valor_pago",
        mode="before",
    )
    @classmethod
    def _normalize_decimal_fields(cls, value: Any) -> Decimal | None:
        return parse_decimal(value)

    @model_validator(mode="after")
    def _validate_payload(self) -> "DespesaPorFuncaoInSchema":
        if not self.origem:
            self.origem = "prefeitura"
        if normalize_search_text(self.funcao) == "totais":
            raise ValueError("linha sintetica de totais nao deve ser persistida")
        validate_date_period(self.periodo_inicio, self.periodo_fim)
        return self
