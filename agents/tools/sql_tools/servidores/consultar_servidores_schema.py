"""Schemas da tool publica consultar_servidores."""

from __future__ import annotations

from datetime import date
from typing import Any

from pydantic import Field, field_validator

from shared.utils.validation import clean_text, normalize_limit

from .shared.base import ServidoresToolBaseSchema
from .shared.filters import (
    ALLOWED_ORDER_VALUES,
    ALLOWED_SERVER_FIELDS,
    ALLOWED_SERVER_SORT_FIELDS,
    CamposServidorSchema,
    ServidoresFiltroSchema,
)


class ConsultarServidoresParams(ServidoresToolBaseSchema):
    filtros: ServidoresFiltroSchema = Field(default_factory=ServidoresFiltroSchema)
    ordenar_por: str = "nome"
    ordem: str = "asc"
    limite: int = 10
    offset: int = 0
    campos: list[str] = Field(default_factory=list)

    @field_validator("filtros", mode="before")
    @classmethod
    def _normalize_filtros(cls, value: Any) -> ServidoresFiltroSchema:
        if value is None:
            return ServidoresFiltroSchema()
        if isinstance(value, ServidoresFiltroSchema):
            return value
        if not isinstance(value, dict):
            raise ValueError("filtros deve ser um objeto")
        return ServidoresFiltroSchema.model_validate(value)

    @field_validator("ordenar_por", mode="before")
    @classmethod
    def _normalize_ordenar_por(cls, value: Any) -> str:
        normalized = clean_text(value) or "nome"
        if normalized not in ALLOWED_SERVER_SORT_FIELDS:
            raise ValueError(f"ordenar_por nao suportado: {normalized}")
        return normalized

    @field_validator("ordem", mode="before")
    @classmethod
    def _normalize_ordem(cls, value: Any) -> str:
        normalized = (clean_text(value) or "asc").lower()
        if normalized not in ALLOWED_ORDER_VALUES:
            raise ValueError(f"ordem nao suportada: {normalized}")
        return normalized

    @field_validator("limite", mode="before")
    @classmethod
    def _normalize_limite(cls, value: Any) -> int:
        return normalize_limit(value, maximum=100)

    @field_validator("offset", mode="before")
    @classmethod
    def _normalize_offset(cls, value: Any) -> int:
        if value is None:
            return 0
        try:
            offset = int(value)
        except (TypeError, ValueError) as exc:
            raise ValueError("offset invalido") from exc
        return max(0, offset)

    @field_validator("campos", mode="before")
    @classmethod
    def _normalize_campos(cls, value: Any) -> list[str]:
        return CamposServidorSchema.model_validate({"campos": value}).campos


class ConsultarServidoresMetadata(ServidoresToolBaseSchema):
    filtros_aplicados: dict[str, Any] = Field(default_factory=dict)
    ordenar_por: str
    ordem: str
    limite: int
    offset: int
    campos: list[str] = Field(default_factory=lambda: list(ALLOWED_SERVER_FIELDS))
    mes_de_referencia_considerado: date | None = None
    mes_de_referencia_padrao_aplicado: bool = False


class ConsultarServidoresResponse(ServidoresToolBaseSchema):
    total: int
    resultados: list[dict[str, Any]] = Field(default_factory=list)
    metadata: ConsultarServidoresMetadata
    mensagem: str | None = None
    sugestao: str | None = None
