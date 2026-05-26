"""Schemas e helpers compartilhados de filtros do dominio de contratos."""

from __future__ import annotations

from datetime import date
from decimal import Decimal
from typing import Any

from pydantic import Field, field_validator, model_validator

from shared.utils.validation import (
    clean_text,
    parse_date,
    parse_decimal,
    validate_date_period,
)

from .base import ContratosToolBaseSchema


ALLOWED_CONTRACT_FIELDS = (
    "id",
    "numero",
    "fornecedor",
    "documento_fornecedor",
    "valor",
    "data_inicio",
    "data_fim",
    "categoria",
    "secretaria",
    "descricao",
    "classificacao_da_despesa",
)

ALLOWED_CONTRACT_SORT_FIELDS = (
    "numero",
    "fornecedor",
    "valor",
    "data_inicio",
    "data_fim",
    "categoria",
    "secretaria",
)

ALLOWED_GROUP_FIELDS = ("secretaria", "categoria", "fornecedor", "ano_inicio")
ALLOWED_METRICS = ("contagem", "soma_valor", "media_valor")
ALLOWED_ORDER_VALUES = ("asc", "desc")


class ContratosFiltroSchema(ContratosToolBaseSchema):
    numero: str | None = None
    fornecedor: str | None = None
    documento_fornecedor: str | None = None
    categoria: str | None = None
    secretaria: str | None = None
    descricao: str | None = None
    data_inicio: date | None = None
    data_inicio_inicio: date | None = None
    data_inicio_fim: date | None = None
    valor_min: Decimal | None = None
    valor_max: Decimal | None = None

    @field_validator(
        "numero",
        "fornecedor",
        "documento_fornecedor",
        "categoria",
        "secretaria",
        "descricao",
        mode="before",
    )
    @classmethod
    def _normalize_text_filters(cls, value: Any) -> str | None:
        return clean_text(value)

    @field_validator(
        "data_inicio",
        "data_inicio_inicio",
        "data_inicio_fim",
        mode="before",
    )
    @classmethod
    def _normalize_date_filters(cls, value: Any) -> date | None:
        return parse_date(value)

    @field_validator("valor_min", "valor_max", mode="before")
    @classmethod
    def _normalize_value_filters(cls, value: Any) -> Decimal | None:
        return parse_decimal(value)

    @model_validator(mode="after")
    def _validate_ranges(self) -> "ContratosFiltroSchema":
        if self.data_inicio is not None and (
            self.data_inicio_inicio is not None or self.data_inicio_fim is not None
        ):
            raise ValueError(
                "data_inicio nao pode ser usada junto com data_inicio_inicio ou data_inicio_fim"
            )

        if self.data_inicio_inicio is not None or self.data_inicio_fim is not None:
            if self.data_inicio_inicio is None or self.data_inicio_fim is None:
                raise ValueError(
                    "data_inicio_inicio e data_inicio_fim devem ser informadas juntas"
                )
            validate_date_period(self.data_inicio_inicio, self.data_inicio_fim)

        if (
            self.valor_min is not None
            and self.valor_max is not None
            and self.valor_min > self.valor_max
        ):
            raise ValueError("valor_min deve ser menor ou igual a valor_max")
        return self

    def build_fornecedor_descricao_fallback(self) -> "ContratosFiltroSchema | None":
        """Cria um filtro alternativo por descricao quando fornecedor nao encontra match."""

        if self.fornecedor is None or self.descricao is not None:
            return None
        return self.model_copy(
            update={
                "fornecedor": None,
                "descricao": self.fornecedor,
            }
        )

    def to_metadata_dict(self) -> dict[str, Any]:
        return self.model_dump(mode="json", exclude_none=True)


class CamposContratoSchema(ContratosToolBaseSchema):
    campos: list[str] = Field(default_factory=list)

    @field_validator("campos", mode="before")
    @classmethod
    def _normalize_campos(cls, value: Any) -> list[str]:
        if value is None:
            return []
        if not isinstance(value, list):
            raise ValueError("campos deve ser uma lista")

        normalized_fields: list[str] = []
        for item in value:
            field_name = clean_text(item)
            if field_name is None:
                continue
            if field_name not in ALLOWED_CONTRACT_FIELDS:
                raise ValueError(f"campo nao suportado: {field_name}")
            normalized_fields.append(field_name)
        return normalized_fields
