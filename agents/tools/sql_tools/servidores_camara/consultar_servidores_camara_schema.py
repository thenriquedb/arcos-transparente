"""Schemas da tool publica consultar_servidores_camara."""

from __future__ import annotations

from datetime import date
from typing import Any

from pydantic import Field, field_validator

from agents.tools.sql_tools.shared.base import SqlToolBaseSchema
from agents.tools.sql_tools.shared.normalization import normalize_model_input
from shared.utils.validation import clean_text, normalize_limit

from .shared.filters import (
    ALLOWED_CAMARA_FIELDS,
    ALLOWED_CAMARA_SORT_FIELDS,
    ALLOWED_ORDER_VALUES,
    CamposServidorCamaraSchema,
    ServidorCamaraFiltroSchema,
)


class ConsultarServidoresCamaraParams(SqlToolBaseSchema):
    filtros: ServidorCamaraFiltroSchema = Field(default_factory=ServidorCamaraFiltroSchema)
    ordenar_por: str = "nome"
    ordem: str = "asc"
    limite: int = 10
    offset: int = 0
    campos: list[str] = Field(default_factory=list)

    @field_validator("filtros", mode="before")
    @classmethod
    def _normalize_filtros(cls, value: Any) -> ServidorCamaraFiltroSchema:
        return normalize_model_input(value, schema_type=ServidorCamaraFiltroSchema, field_name="filtros")

    @field_validator("ordenar_por", mode="before")
    @classmethod
    def _normalize_ordenar_por(cls, value: Any) -> str:
        normalized = clean_text(value) or "nome"
        if normalized not in ALLOWED_CAMARA_SORT_FIELDS:
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
            return max(0, int(value))
        except (TypeError, ValueError) as exc:
            raise ValueError("offset invalido") from exc

    @field_validator("campos", mode="before")
    @classmethod
    def _normalize_campos(cls, value: Any) -> list[str]:
        return CamposServidorCamaraSchema.model_validate({"campos": value}).campos


class ConsultarServidoresCamaraMetadata(SqlToolBaseSchema):
    filtros_aplicados: dict[str, Any] = Field(default_factory=dict)
    ordenar_por: str
    ordem: str
    limite: int
    offset: int
    campos: list[str] = Field(default_factory=lambda: list(ALLOWED_CAMARA_FIELDS))
    mes_de_referencia_considerado: date | None = None
    mes_de_referencia_padrao_aplicado: bool = False


class ConsultarServidoresCamaraResponse(SqlToolBaseSchema):
    total: int
    resultados: list[dict[str, Any]] = Field(default_factory=list)
    metadata: ConsultarServidoresCamaraMetadata
    mensagem: str | None = None
    sugestao: str | None = None
