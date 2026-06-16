"""Schemas e helpers de filtros para o dominio de servidores da Camara."""

from __future__ import annotations

from datetime import date
from decimal import Decimal
from typing import Any

from pydantic import Field, field_validator, model_validator

from agents.tools.sql_tools.shared.base import SqlToolBaseSchema
from agents.tools.sql_tools.shared.normalization import normalize_selected_fields
from shared.utils.validation import (
    clean_text,
    parse_date,
    parse_decimal,
    validate_date_period,
)


ALLOWED_CAMARA_FIELDS = (
    "id",
    "nome",
    "matricula",
    "cargo",
    "lotacao",
    "situacao_funcional",
    "salario_base",
    "proventos",
    "descontos",
    "liquido",
    "mes_de_referencia",
)

ALLOWED_CAMARA_SORT_FIELDS = (
    "nome",
    "cargo",
    "lotacao",
    "salario_base",
    "liquido",
    "mes_de_referencia",
)

ALLOWED_CAMARA_GROUP_FIELDS = ("cargo", "lotacao", "situacao_funcional", "mes_de_referencia")
ALLOWED_CAMARA_METRICS = ("contagem", "soma_salario_base", "soma_liquido")
ALLOWED_ORDER_VALUES = ("asc", "desc")


class ServidorCamaraFiltroSchema(SqlToolBaseSchema):
    """Filtros publicos aceitos pelas tools de servidores da Camara."""

    nome: str | None = None
    cargo: str | None = None
    lotacao: str | None = None
    situacao_funcional: str | None = None
    vinculo: str | None = None
    mes_de_referencia: date | None = None
    mes_de_referencia_inicio: date | None = None
    mes_de_referencia_fim: date | None = None
    salario_min: Decimal | None = None
    salario_max: Decimal | None = None

    @field_validator("nome", "cargo", "lotacao", "situacao_funcional", "vinculo", mode="before")
    @classmethod
    def _normalize_text(cls, value: Any) -> str | None:
        return clean_text(value)

    @field_validator(
        "mes_de_referencia",
        "mes_de_referencia_inicio",
        "mes_de_referencia_fim",
        mode="before",
    )
    @classmethod
    def _normalize_date(cls, value: Any) -> date | None:
        return parse_date(value)

    @field_validator("salario_min", "salario_max", mode="before")
    @classmethod
    def _normalize_decimal(cls, value: Any) -> Decimal | None:
        return parse_decimal(value)

    @model_validator(mode="after")
    def _validate_ranges(self) -> ServidorCamaraFiltroSchema:
        if self.mes_de_referencia is not None and (
            self.mes_de_referencia_inicio is not None or self.mes_de_referencia_fim is not None
        ):
            raise ValueError(
                "mes_de_referencia nao pode ser usado junto com mes_de_referencia_inicio ou mes_de_referencia_fim"
            )
        if self.mes_de_referencia_inicio is not None or self.mes_de_referencia_fim is not None:
            if self.mes_de_referencia_inicio is None or self.mes_de_referencia_fim is None:
                raise ValueError("mes_de_referencia_inicio e mes_de_referencia_fim devem ser informados juntos")
            validate_date_period(self.mes_de_referencia_inicio, self.mes_de_referencia_fim)
        if self.salario_min is not None and self.salario_max is not None and self.salario_min > self.salario_max:
            raise ValueError("salario_min deve ser menor ou igual a salario_max")
        return self


class CamposServidorCamaraSchema(SqlToolBaseSchema):
    campos: list[str] = Field(default_factory=list)

    @field_validator("campos", mode="before")
    @classmethod
    def _normalize_campos(cls, value: Any) -> list[str]:
        return normalize_selected_fields(
            value,
            allowed_fields=ALLOWED_CAMARA_FIELDS,
            require_list=True,
            error_style="campo",
        )
