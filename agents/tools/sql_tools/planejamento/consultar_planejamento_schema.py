"""Schemas da tool publica consultar_planejamento."""

from __future__ import annotations

from typing import Any

from pydantic import Field, field_validator

from agents.tools.sql_tools.shared.base import SqlToolBaseSchema
from agents.tools.sql_tools.shared.normalization import normalize_model_input
from shared.utils.validation import clean_text, normalize_limit

from .shared.filters import (
    ALLOWED_ORDER_VALUES,
    ALLOWED_PLANNING_FIELDS,
    ALLOWED_PLANNING_SORT_FIELDS,
    CamposPlanejamentoSchema,
    PlanejamentoFiltroSchema,
)


class ConsultarPlanejamentoParams(SqlToolBaseSchema):
    filtros: PlanejamentoFiltroSchema = Field(default_factory=PlanejamentoFiltroSchema)
    ordenar_por: str = "mes_num"
    ordem: str = "asc"
    limite: int = 10
    offset: int = 0
    campos: list[str] = Field(default_factory=list)

    @field_validator("filtros", mode="before")
    @classmethod
    def _normalize_filtros(cls, value: Any) -> PlanejamentoFiltroSchema:
        return normalize_model_input(
            value,
            schema_type=PlanejamentoFiltroSchema,
            field_name="filtros",
        )

    @field_validator("ordenar_por", mode="before")
    @classmethod
    def _normalize_ordenar_por(cls, value: Any) -> str:
        normalized = clean_text(value) or "mes_num"
        if normalized not in ALLOWED_PLANNING_SORT_FIELDS:
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
        return max(0, int(value))

    @field_validator("campos", mode="before")
    @classmethod
    def _normalize_campos(cls, value: Any) -> list[str]:
        return CamposPlanejamentoSchema.model_validate({"campos": value}).campos


class ConsultarPlanejamentoMetadata(SqlToolBaseSchema):
    filtros_aplicados: dict[str, Any] = Field(default_factory=dict)
    ordenar_por: str
    ordem: str
    limite: int
    offset: int
    campos: list[str] = Field(default_factory=lambda: list(ALLOWED_PLANNING_FIELDS))


class ConsultarPlanejamentoResponse(SqlToolBaseSchema):
    total: int
    resultados: list[dict[str, Any]] = Field(default_factory=list)
    metadata: ConsultarPlanejamentoMetadata
    mensagem: str | None = None
    sugestao: str | None = None
