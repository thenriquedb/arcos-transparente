"""Schemas da tool publica consultar_contratos."""

from __future__ import annotations

from typing import Any

from pydantic import Field, field_validator

from shared.utils.validation import clean_text, normalize_limit

from .shared.base import ContratosToolBaseSchema
from .shared.filters import (
    ALLOWED_CONTRACT_FIELDS,
    ALLOWED_CONTRACT_SORT_FIELDS,
    ALLOWED_ORDER_VALUES,
    CamposContratoSchema,
    ContratosFiltroSchema,
)


class ConsultarContratosParams(ContratosToolBaseSchema):
    filtros: ContratosFiltroSchema = Field(default_factory=ContratosFiltroSchema)
    ordenar_por: str = "data_inicio"
    ordem: str = "desc"
    limite: int = 10
    offset: int = 0
    campos: list[str] = Field(default_factory=list)
    incluir_detalhes: bool = False

    @field_validator("filtros", mode="before")
    @classmethod
    def _normalize_filtros(cls, value: Any) -> ContratosFiltroSchema:
        if value is None:
            return ContratosFiltroSchema()
        if isinstance(value, ContratosFiltroSchema):
            return value
        if not isinstance(value, dict):
            raise ValueError("filtros deve ser um objeto")
        return ContratosFiltroSchema.model_validate(value)

    @field_validator("ordenar_por", mode="before")
    @classmethod
    def _normalize_ordenar_por(cls, value: Any) -> str:
        normalized = clean_text(value) or "data_inicio"
        if normalized not in ALLOWED_CONTRACT_SORT_FIELDS:
            raise ValueError(f"ordenar_por nao suportado: {normalized}")
        return normalized

    @field_validator("ordem", mode="before")
    @classmethod
    def _normalize_ordem(cls, value: Any) -> str:
        normalized = (clean_text(value) or "desc").lower()
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
        return CamposContratoSchema.model_validate({"campos": value}).campos


class ConsultarContratosMetadata(ContratosToolBaseSchema):
    filtros_aplicados: dict[str, Any] = Field(default_factory=dict)
    filtros_fallback_aplicados: dict[str, Any] | None = None
    ordenar_por: str
    ordem: str
    limite: int
    offset: int
    incluir_detalhes: bool = False
    campos: list[str] = Field(default_factory=lambda: list(ALLOWED_CONTRACT_FIELDS))


class ConsultarContratosResponse(ContratosToolBaseSchema):
    total: int
    resultados: list[dict[str, Any]] = Field(default_factory=list)
    metadata: ConsultarContratosMetadata
    mensagem: str | None = None
    sugestao: str | None = None
