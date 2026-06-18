"""Schemas Pydantic para ingestao de servidores e cargos da Camara Municipal."""

from __future__ import annotations

from datetime import date
from decimal import Decimal
from typing import Any

from pydantic import BaseModel, ConfigDict, field_validator

from shared.utils.validation import (
    clean_text,
    parse_competencia_as_date,
    parse_date,
    parse_number,
)


class _CamaraBaseSchema(BaseModel):
    model_config = ConfigDict(extra="ignore")


class ServidorCamaraInSchema(_CamaraBaseSchema):
    """Schema de ingestao de um registro mensal do CSV de servidores da Camara."""

    competencia_referencia: date
    matricula: str
    nome: str
    cargo: str | None = None
    lotacao: str | None = None
    vinculo: str | None = None
    situacao_funcional: str | None = None
    data_admissao: date | None = None
    salario_base: Decimal | None = None
    proventos: Decimal | None = None
    vantagens: Decimal | None = None
    proventos_totais: Decimal | None = None
    descontos: Decimal | None = None
    liquido: Decimal | None = None

    @field_validator("competencia_referencia", mode="before")
    @classmethod
    def _normalize_competencia(cls, value: Any) -> date | None:
        return parse_competencia_as_date(value)

    @field_validator("data_admissao", mode="before")
    @classmethod
    def _normalize_data_admissao(cls, value: Any) -> date | None:
        return parse_date(value)

    @field_validator(
        "nome",
        "matricula",
        "cargo",
        "lotacao",
        "vinculo",
        "situacao_funcional",
        mode="before",
    )
    @classmethod
    def _normalize_text(cls, value: Any) -> str | None:
        return clean_text(value)

    @field_validator(
        "salario_base",
        "proventos",
        "vantagens",
        "proventos_totais",
        "descontos",
        "liquido",
        mode="before",
    )
    @classmethod
    def _normalize_decimal(cls, value: Any) -> Decimal | None:
        result = parse_number(value)
        if result is None:
            return None
        return Decimal(str(result))


class SalarioPorCargoCamaraInSchema(_CamaraBaseSchema):
    """Schema de ingestao de um cargo da tabela de remuneracao da Camara."""

    competencia_referencia: date
    codigo: str
    descricao: str

    @field_validator("competencia_referencia", mode="before")
    @classmethod
    def _normalize_competencia(cls, value: Any) -> date | None:
        return parse_competencia_as_date(value)

    @field_validator("codigo", "descricao", mode="before")
    @classmethod
    def _normalize_text(cls, value: Any) -> str | None:
        return clean_text(value)
