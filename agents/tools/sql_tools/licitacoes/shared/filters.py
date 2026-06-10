"""Schemas e helpers compartilhados de filtros do dominio de licitacoes."""

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

from .base import LicitacoesToolBaseSchema


ALLOWED_BIDDING_FIELDS = (
    "id",
    "numero",
    "modalidade",
    "objeto",
    "valor_estimado",
    "data_abertura",
    "situacao",
    "secretaria",
)

ALLOWED_BIDDING_SORT_FIELDS = (
    "numero",
    "modalidade",
    "valor_estimado",
    "data_abertura",
    "situacao",
    "secretaria",
)

ALLOWED_GROUP_FIELDS = ("secretaria", "modalidade", "situacao", "ano_abertura")
ALLOWED_METRICS = ("contagem", "soma_valor_estimado", "media_valor_estimado")
ALLOWED_ORDER_VALUES = ("asc", "desc")


class LicitacoesFiltroSchema(LicitacoesToolBaseSchema):
    """Filtros publicos aceitos pela tool deste dominio."""

    numero: str | None = None
    modalidade: str | None = None
    objeto: str | None = None
    secretaria: str | None = None
    situacao: str | None = None
    fornecedor: str | None = None
    cnpj_cpf: str | None = None
    data_abertura: date | None = None
    data_abertura_inicio: date | None = None
    data_abertura_fim: date | None = None
    valor_estimado_min: Decimal | None = None
    valor_estimado_max: Decimal | None = None

    @field_validator(
        "numero",
        "modalidade",
        "objeto",
        "secretaria",
        "situacao",
        "fornecedor",
        "cnpj_cpf",
        mode="before",
    )
    @classmethod
    def _normalize_text_filters(cls, value: Any) -> str | None:
        return clean_text(value)

    @field_validator(
        "data_abertura",
        "data_abertura_inicio",
        "data_abertura_fim",
        mode="before",
    )
    @classmethod
    def _normalize_date_filters(cls, value: Any) -> date | None:
        return parse_date(value)

    @field_validator("valor_estimado_min", "valor_estimado_max", mode="before")
    @classmethod
    def _normalize_value_filters(cls, value: Any) -> Decimal | None:
        return parse_decimal(value)

    @model_validator(mode="after")
    def _validate_ranges(self) -> "LicitacoesFiltroSchema":
        if self.data_abertura is not None and (
            self.data_abertura_inicio is not None or self.data_abertura_fim is not None
        ):
            raise ValueError(
                "data_abertura nao pode ser usada junto com "
                "data_abertura_inicio ou data_abertura_fim"
            )

        if self.data_abertura_inicio is not None or self.data_abertura_fim is not None:
            if self.data_abertura_inicio is None or self.data_abertura_fim is None:
                raise ValueError(
                    "data_abertura_inicio e data_abertura_fim devem ser informadas juntas"
                )
            validate_date_period(self.data_abertura_inicio, self.data_abertura_fim)

        if (
            self.valor_estimado_min is not None
            and self.valor_estimado_max is not None
            and self.valor_estimado_min > self.valor_estimado_max
        ):
            raise ValueError(
                "valor_estimado_min deve ser menor ou igual a valor_estimado_max"
            )
        return self


class CamposLicitacaoSchema(LicitacoesToolBaseSchema):
    campos: list[str] = Field(default_factory=list)

    @field_validator("campos", mode="before")
    @classmethod
    def _normalize_campos(cls, value: Any) -> list[str]:
        return normalize_selected_fields(
            value,
            allowed_fields=ALLOWED_BIDDING_FIELDS,
            require_list=True,
            error_style="campo",
        )
