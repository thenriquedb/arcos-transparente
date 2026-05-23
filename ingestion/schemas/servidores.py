"""Schemas Pydantic para ingestao de servidores."""

from __future__ import annotations

from datetime import date
from decimal import Decimal, InvalidOperation
from typing import Any

from pydantic import BaseModel, ConfigDict, field_validator, model_validator


class _ServidoresBaseSchema(BaseModel):
    """Base compartilhada de saneamento para schemas de servidores."""

    model_config = ConfigDict(extra="ignore")

    @staticmethod
    def _clean_text(value: Any) -> str | None:
        if value is None:
            return None
        if isinstance(value, str):
            value = value.strip()
            return value or None
        if isinstance(value, (int, float, Decimal)):
            value = str(value).strip()
            return value or None
        raise ValueError("valor textual invalido")

    @classmethod
    def _parse_decimal(cls, value: Any) -> Decimal | None:
        if value is None:
            return None
        if isinstance(value, Decimal):
            return value
        if isinstance(value, int):
            return Decimal(value)
        if isinstance(value, float):
            return Decimal(str(value))

        text = cls._clean_text(value)
        if text is None:
            return None

        normalized = text.replace("R$", "").replace(" ", "")
        normalized = normalized.replace(".", "").replace(",", ".")
        try:
            return Decimal(normalized)
        except (InvalidOperation, ValueError) as exc:
            raise ValueError("valor decimal invalido") from exc

    @classmethod
    def _parse_competencia_as_date(cls, value: Any) -> date | None:
        if value is None:
            return None
        if isinstance(value, date):
            return value

        text = cls._clean_text(value)
        if text is None:
            return None

        if "/" in text:
            try:
                mm, yyyy = text.split("/")
                return date(int(yyyy), int(mm), 1)
            except ValueError as exc:
                raise ValueError("competencia invalida no formato mm/yyyy") from exc

        try:
            return date.fromisoformat(text)
        except ValueError as exc:
            raise ValueError("data invalida") from exc


class ServidorInSchema(_ServidoresBaseSchema):
    """Schema principal de ingestao de servidores."""

    nome: str
    cargo: str | None = "nao_informado"
    secretaria: str | None = "nao_informado"
    salario_base: Decimal
    data_admissao: date

    @field_validator("nome", "cargo", "secretaria", mode="before")
    @classmethod
    def _normalize_text_fields(cls, value: Any) -> str | None:
        return cls._clean_text(value)

    @field_validator("salario_base", mode="before")
    @classmethod
    def _normalize_salario_base(cls, value: Any) -> Decimal | None:
        return cls._parse_decimal(value)

    @field_validator("data_admissao", mode="before")
    @classmethod
    def _normalize_data_admissao(cls, value: Any) -> date | None:
        return cls._parse_competencia_as_date(value)

    @model_validator(mode="after")
    def _apply_defaults(self) -> ServidorInSchema:
        if not self.cargo:
            self.cargo = "nao_informado"
        if not self.secretaria:
            self.secretaria = "nao_informado"
        return self
