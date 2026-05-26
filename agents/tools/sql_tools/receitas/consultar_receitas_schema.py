"""Schemas da tool publica consultar_receitas."""

from __future__ import annotations

from typing import Any

from pydantic import Field, field_validator

from shared.utils.validation import clean_text, normalize_limit

from .shared.base import ReceitasToolBaseSchema
from .shared.filters import (
    ALLOWED_ORDER_VALUES,
    ALLOWED_RECEITA_FIELDS,
    ALLOWED_RECEITA_SORT_FIELDS,
    CamposReceitaSchema,
    ReceitaFiltroSchema,
)


class ConsultarReceitasParams(ReceitasToolBaseSchema):
    filtros: ReceitaFiltroSchema = Field(default_factory=ReceitaFiltroSchema)
    ordenar_por: str = "data"
    ordem: str = "desc"
    limite: int = 10
    offset: int = 0
    campos: list[str] = Field(default_factory=list)

    @field_validator("filtros", mode="before")
    @classmethod
    def _normalize_filtros(cls, value: Any) -> ReceitaFiltroSchema:
        if value is None:
            return ReceitaFiltroSchema()
        if isinstance(value, ReceitaFiltroSchema):
            return value
        if not isinstance(value, dict):
            raise ValueError("filtros deve ser um objeto")
        return ReceitaFiltroSchema.model_validate(value)

    @field_validator("ordenar_por", mode="before")
    @classmethod
    def _normalize_ordenar_por(cls, value: Any) -> str:
        normalized = clean_text(value) or "data"
        if normalized not in ALLOWED_RECEITA_SORT_FIELDS:
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
        return CamposReceitaSchema.model_validate({"campos": value}).campos


class ConsultarReceitasMetadata(ReceitasToolBaseSchema):
    filtros_aplicados: dict[str, Any] = Field(default_factory=dict)
    ordenar_por: str
    ordem: str
    limite: int
    offset: int
    campos: list[str] = Field(default_factory=lambda: list(ALLOWED_RECEITA_FIELDS))


class ConsultarReceitasResponse(ReceitasToolBaseSchema):
    total: int
    resultados: list[dict[str, Any]] = Field(default_factory=list)
    metadata: ConsultarReceitasMetadata
    mensagem: str | None = None
    sugestao: str | None = None
