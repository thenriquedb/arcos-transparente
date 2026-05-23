"""Schemas Pydantic para tools SQL de servidores."""

from __future__ import annotations

from datetime import date, datetime
from typing import Any

from pydantic import BaseModel, ConfigDict, Field, field_validator, model_validator


class _ServidoresToolBaseSchema(BaseModel):
    """Base de saneamento para entrada e saida das tools de servidores."""

    model_config = ConfigDict(extra="ignore")

    @staticmethod
    def _clean_text(value: Any) -> str | None:
        if value is None:
            return None
        if isinstance(value, str):
            value = value.strip()
            return value or None
        return str(value).strip() or None

    @staticmethod
    def _normalize_limit(value: Any) -> int:
        try:
            limit = int(value)
        except (TypeError, ValueError) as exc:
            raise ValueError("limite invalido") from exc
        return max(1, min(limit, 50))

    @classmethod
    def _parse_date(cls, value: Any) -> date | None:
        if value is None:
            return None
        if isinstance(value, datetime):
            return value.date()
        if isinstance(value, date):
            return value

        text = cls._clean_text(value)
        if text is None:
            return None

        if "/" in text:
            try:
                dd, mm, yyyy = text.split("/")
                return date(int(yyyy), int(mm), int(dd))
            except ValueError as exc:
                raise ValueError("data invalida no formato dd/mm/yyyy") from exc

        try:
            return date.fromisoformat(text)
        except ValueError as exc:
            raise ValueError("data invalida") from exc


class BuscarServidorPorNomeParams(_ServidoresToolBaseSchema):
    nome: str | None
    limite: int = 10

    @field_validator("nome", mode="before")
    @classmethod
    def _normalize_nome(cls, value: Any) -> str | None:
        return cls._clean_text(value)

    @field_validator("limite", mode="before")
    @classmethod
    def _normalize_limite(cls, value: Any) -> int:
        return cls._normalize_limit(value)


class BuscarServidorPorSecretariaParams(_ServidoresToolBaseSchema):
    secretaria: str | None
    limite: int = 10

    @field_validator("secretaria", mode="before")
    @classmethod
    def _normalize_secretaria(cls, value: Any) -> str | None:
        return cls._clean_text(value)

    @field_validator("limite", mode="before")
    @classmethod
    def _normalize_limite(cls, value: Any) -> int:
        return cls._normalize_limit(value)


class BuscarServidorPorCargoParams(_ServidoresToolBaseSchema):
    cargo: str | None
    limite: int = 10

    @field_validator("cargo", mode="before")
    @classmethod
    def _normalize_cargo(cls, value: Any) -> str | None:
        return cls._clean_text(value)

    @field_validator("limite", mode="before")
    @classmethod
    def _normalize_limite(cls, value: Any) -> int:
        return cls._normalize_limit(value)


class BuscarServidorPorPeriodoParams(_ServidoresToolBaseSchema):
    data_inicio: date
    data_fim: date
    limite: int = 10

    @field_validator("data_inicio", "data_fim", mode="before")
    @classmethod
    def _normalize_datas(cls, value: Any) -> date | None:
        return cls._parse_date(value)

    @field_validator("limite", mode="before")
    @classmethod
    def _normalize_limite(cls, value: Any) -> int:
        return cls._normalize_limit(value)

    @model_validator(mode="after")
    def _validate_period(self) -> BuscarServidorPorPeriodoParams:
        if self.data_inicio > self.data_fim:
            raise ValueError("data_inicio deve ser menor ou igual a data_fim")
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
