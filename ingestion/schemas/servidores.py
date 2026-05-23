"""Schemas Pydantic para ingestao de servidores."""

from __future__ import annotations

from datetime import date
from decimal import Decimal
from typing import Any

from pydantic import BaseModel, ConfigDict, field_validator, model_validator

from shared.utils.validation import clean_text, parse_competencia_as_date, parse_decimal


class _ServidoresBaseSchema(BaseModel):
    """Base compartilhada de saneamento para schemas de servidores."""

    model_config = ConfigDict(extra="ignore")


class ServidorInSchema(_ServidoresBaseSchema):
    """Schema principal de ingestao de servidores."""

    nome: str
    cargo: str | None = "nao_informado"
    secretaria: str | None = "nao_informado"
    salario_base: Decimal
    competencia_referencia: date

    @field_validator("nome", "cargo", "secretaria", mode="before")
    @classmethod
    def _normalize_text_fields(cls, value: Any) -> str | None:
        return clean_text(value)

    @field_validator("salario_base", mode="before")
    @classmethod
    def _normalize_salario_base(cls, value: Any) -> Decimal | None:
        return parse_decimal(value)

    @field_validator("competencia_referencia", mode="before")
    @classmethod
    def _normalize_competencia_referencia(cls, value: Any) -> date | None:
        return parse_competencia_as_date(value)

    @model_validator(mode="after")
    def _apply_defaults(self) -> ServidorInSchema:
        if not self.cargo:
            self.cargo = "nao_informado"
        if not self.secretaria:
            self.secretaria = "nao_informado"
        return self
