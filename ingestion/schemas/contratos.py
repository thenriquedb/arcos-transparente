"""Schemas Pydantic para ingestao de contratos."""

from __future__ import annotations

from datetime import date
from decimal import Decimal
from typing import Any

from pydantic import BaseModel, ConfigDict, field_validator, model_validator

from shared.utils.validation import clean_text, parse_date, parse_decimal


class _ContratosBaseSchema(BaseModel):
    model_config = ConfigDict(extra="ignore")


class ContratoInSchema(_ContratosBaseSchema):
    numero: str
    fornecedor: str
    cnpj: str
    valor: Decimal
    data_inicio: date
    data_fim: date | None = None
    categoria: str | None = "nao_informado"
    secretaria: str | None = "nao_informado"
    descricao: str | None = None
    descricao_despesa: str | None = None

    @field_validator(
        "numero",
        "fornecedor",
        "cnpj",
        "categoria",
        "secretaria",
        "descricao",
        "descricao_despesa",
        mode="before",
    )
    @classmethod
    def _normalize_text_fields(cls, value: Any) -> str | None:
        return clean_text(value)

    @field_validator("valor", mode="before")
    @classmethod
    def _normalize_valor(cls, value: Any) -> Decimal | None:
        return parse_decimal(value)

    @field_validator("data_inicio", "data_fim", mode="before")
    @classmethod
    def _normalize_datas(cls, value: Any) -> date | None:
        return parse_date(value)

    @model_validator(mode="after")
    def _apply_defaults_and_validate(self) -> "ContratoInSchema":
        if not self.numero:
            raise ValueError("numero e obrigatorio")
        if not self.fornecedor:
            raise ValueError("fornecedor e obrigatorio")
        if not self.cnpj:
            raise ValueError("cnpj e obrigatorio")
        if self.valor is None:
            raise ValueError("valor e obrigatorio")
        if self.data_inicio is None:
            raise ValueError("data_inicio e obrigatoria")

        self.categoria = self.categoria or "nao_informado"
        self.secretaria = self.secretaria or "nao_informado"
        return self
