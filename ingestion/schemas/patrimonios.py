"""Schemas Pydantic para ingestao de patrimonio."""

from __future__ import annotations

from datetime import date
from decimal import Decimal
from typing import Any

from pydantic import BaseModel, ConfigDict, field_validator

from shared.utils.validation import clean_text, parse_date, parse_number


class PatrimonioInSchema(BaseModel):
    """Schema principal de um bem patrimonial."""

    model_config = ConfigDict(extra="ignore")

    unidade_gestora: str
    placa: str
    situacao_bem: str | None = None
    comandatario: str | None = None
    classificacao: str | None = None
    descricao_item: str
    tipo_ingresso: str | None = None
    data_aquisicao: date | None = None
    data_baixa: date | None = None
    localizacao: str | None = None
    status: str | None = None
    valor_ingresso: Decimal | None = None
    valor_atualizado: Decimal | None = None

    @field_validator(
        "unidade_gestora",
        "placa",
        "situacao_bem",
        "comandatario",
        "classificacao",
        "descricao_item",
        "tipo_ingresso",
        "localizacao",
        "status",
        mode="before",
    )
    @classmethod
    def _normalize_text_fields(cls, value: Any) -> str | None:
        return clean_text(value)

    @field_validator("data_aquisicao", "data_baixa", mode="before")
    @classmethod
    def _normalize_dates(cls, value: Any) -> date | None:
        return parse_date(value)

    @field_validator("valor_ingresso", "valor_atualizado", mode="before")
    @classmethod
    def _normalize_decimals(cls, value: Any) -> Decimal | None:
        return parse_number(value)
