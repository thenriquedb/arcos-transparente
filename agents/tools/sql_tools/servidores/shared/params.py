"""Schemas de entrada compartilhados pelas tools de servidores."""

from __future__ import annotations

from datetime import date
from typing import Any

from pydantic import field_validator, model_validator

from shared.utils.validation import (
    clean_text,
    normalize_limit,
    parse_date,
    validate_date_period,
)

from .base import ServidoresToolBaseSchema


class BuscarServidorPorNomeParams(ServidoresToolBaseSchema):
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


class BuscarServidorPorSecretariaParams(ServidoresToolBaseSchema):
    secretaria: str | None
    limite: int = 10

    @field_validator("secretaria", mode="before")
    @classmethod
    def _normalize_secretaria(cls, value: Any) -> str | None:
        return clean_text(value)

    @field_validator("limite", mode="before")
    @classmethod
    def _normalize_limite(cls, value: Any) -> int:
        return normalize_limit(value, maximum=200)


class BuscarServidorPorCargoParams(ServidoresToolBaseSchema):
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


class BuscarServidorPorMesDeReferenciaParams(ServidoresToolBaseSchema):
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
    def _validate_period(self) -> "BuscarServidorPorMesDeReferenciaParams":
        validate_date_period(self.data_inicio, self.data_fim)
        return self


class RankingSecretariasParams(ServidoresToolBaseSchema):
    limite: int = 10

    @field_validator("limite", mode="before")
    @classmethod
    def _normalize_limite(cls, value: Any) -> int:
        return normalize_limit(value)


class RankingSalariosParams(ServidoresToolBaseSchema):
    limite: int = 10

    @field_validator("limite", mode="before")
    @classmethod
    def _normalize_limite(cls, value: Any) -> int:
        return normalize_limit(value)
