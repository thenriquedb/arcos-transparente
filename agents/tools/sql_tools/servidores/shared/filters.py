"""Schemas e helpers compartilhados de filtros do dominio de servidores."""

from __future__ import annotations

from datetime import date
from decimal import Decimal
from typing import Any

from pydantic import Field, field_validator, model_validator

from agents.tools.sql_tools.shared.normalization import normalize_selected_fields
from shared.utils.validation import (
    clean_text,
    parse_date,
    parse_decimal,
    validate_date_period,
)

from .base import ServidoresToolBaseSchema


ALLOWED_SERVER_FIELDS = (
    "id",
    "nome",
    "cargo",
    "secretaria",
    "salario_base",
    "mes_de_referencia",
)

ALLOWED_SERVER_SORT_FIELDS = (
    "nome",
    "cargo",
    "secretaria",
    "salario_base",
    "mes_de_referencia",
)

ALLOWED_GROUP_FIELDS = ("secretaria", "cargo", "mes_de_referencia")
ALLOWED_METRICS = ("contagem", "soma_salario_base")
ALLOWED_ORDER_VALUES = ("asc", "desc")


class ServidoresFiltroSchema(ServidoresToolBaseSchema):
    nome: str | None = None
    secretaria: str | None = None
    cargo: str | None = None
    mes_de_referencia: date | None = None
    mes_de_referencia_inicio: date | None = None
    mes_de_referencia_fim: date | None = None
    salario_min: Decimal | None = None
    salario_max: Decimal | None = None

    @field_validator("nome", "secretaria", "cargo", mode="before")
    @classmethod
    def _normalize_text_filters(cls, value: Any) -> str | None:
        return clean_text(value)

    @field_validator(
        "mes_de_referencia",
        "mes_de_referencia_inicio",
        "mes_de_referencia_fim",
        mode="before",
    )
    @classmethod
    def _normalize_mes_de_referencia(cls, value: Any) -> date | None:
        return parse_date(value)

    @field_validator("salario_min", "salario_max", mode="before")
    @classmethod
    def _normalize_salario_filters(cls, value: Any) -> Decimal | None:
        return parse_decimal(value)

    @model_validator(mode="after")
    def _validate_ranges(self) -> "ServidoresFiltroSchema":
        if self.mes_de_referencia is not None and (
            self.mes_de_referencia_inicio is not None
            or self.mes_de_referencia_fim is not None
        ):
            raise ValueError(
                "mes_de_referencia nao pode ser usado junto com "
                "mes_de_referencia_inicio ou mes_de_referencia_fim"
            )

        if (
            self.mes_de_referencia_inicio is not None
            or self.mes_de_referencia_fim is not None
        ):
            if (
                self.mes_de_referencia_inicio is None
                or self.mes_de_referencia_fim is None
            ):
                raise ValueError(
                    "mes_de_referencia_inicio e mes_de_referencia_fim devem ser informados juntos"
                )
            validate_date_period(
                self.mes_de_referencia_inicio,
                self.mes_de_referencia_fim,
            )

        if (
            self.salario_min is not None
            and self.salario_max is not None
            and self.salario_min > self.salario_max
        ):
            raise ValueError("salario_min deve ser menor ou igual a salario_max")
        return self


class CamposServidorSchema(ServidoresToolBaseSchema):
    campos: list[str] = Field(default_factory=list)

    @field_validator("campos", mode="before")
    @classmethod
    def _normalize_campos(cls, value: Any) -> list[str]:
        return normalize_selected_fields(
            value,
            allowed_fields=ALLOWED_SERVER_FIELDS,
            require_list=True,
            error_style="campo",
        )
