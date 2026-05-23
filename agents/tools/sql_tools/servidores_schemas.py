"""Schemas Pydantic para tools SQL de servidores."""

from __future__ import annotations

from datetime import date
from typing import Any

from pydantic import BaseModel, ConfigDict, Field, field_validator, model_validator

from shared.utils.validation import (
    clean_text,
    normalize_limit,
    parse_date,
    validate_date_period,
)


class _ServidoresToolBaseSchema(BaseModel):
    """Base de saneamento para entrada e saida das tools de servidores."""

    model_config = ConfigDict(extra="ignore")


class BuscarServidorPorNomeParams(_ServidoresToolBaseSchema):
    nome: str | None
    limite: int = 10

    @field_validator("nome", mode="before")
    @classmethod
    def _normalize_nome(cls, value: Any) -> str | None:
        return clean_text(value)

    @field_validator("limite", mode="before")
    @classmethod
    def _normalize_limite(cls, value: Any) -> int:
        return normalize_limit(value)


class BuscarServidorPorSecretariaParams(_ServidoresToolBaseSchema):
    secretaria: str | None
    limite: int = 10

    @field_validator("secretaria", mode="before")
    @classmethod
    def _normalize_secretaria(cls, value: Any) -> str | None:
        return clean_text(value)

    @field_validator("limite", mode="before")
    @classmethod
    def _normalize_limite(cls, value: Any) -> int:
        return normalize_limit(value)


class BuscarServidorPorCargoParams(_ServidoresToolBaseSchema):
    cargo: str | None
    limite: int = 10

    @field_validator("cargo", mode="before")
    @classmethod
    def _normalize_cargo(cls, value: Any) -> str | None:
        return clean_text(value)

    @field_validator("limite", mode="before")
    @classmethod
    def _normalize_limite(cls, value: Any) -> int:
        return normalize_limit(value)


class BuscarServidorPorPeriodoParams(_ServidoresToolBaseSchema):
    data_inicio: date
    data_fim: date
    limite: int = 10

    @field_validator("data_inicio", "data_fim", mode="before")
    @classmethod
    def _normalize_datas(cls, value: Any) -> date | None:
        return parse_date(value)

    @field_validator("limite", mode="before")
    @classmethod
    def _normalize_limite(cls, value: Any) -> int:
        return normalize_limit(value)

    @model_validator(mode="after")
    def _validate_period(self) -> BuscarServidorPorPeriodoParams:
        validate_date_period(self.data_inicio, self.data_fim)
        return self


class ServidorToolItem(_ServidoresToolBaseSchema):
    id: int
    nome: str
    cargo: str
    secretaria: str
    salario_base: float | None = None
    data_admissao: date


class ServidoresToolResponse(_ServidoresToolBaseSchema):
    query: str | None = None
    data_inicio: date | None = None
    data_fim: date | None = None
    total: int
    resultados: list[ServidorToolItem] = Field(default_factory=list)
    mensagem: str | None = None
    sugestao: str | None = None
