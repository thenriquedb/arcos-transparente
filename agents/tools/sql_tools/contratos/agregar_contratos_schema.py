"""Schemas da tool publica agregar_contratos."""

from __future__ import annotations

from typing import Any

from pydantic import Field, field_validator, model_validator

from agents.tools.sql_tools.shared.normalization import normalize_model_input
from shared.utils.validation import clean_text, normalize_limit

from .shared.base import ContratosToolBaseSchema
from .shared.filters import (
    ALLOWED_GROUP_FIELDS,
    ALLOWED_METRICS,
    ALLOWED_ORDER_VALUES,
    ContratosFiltroSchema,
)


class AgregarContratosParams(ContratosToolBaseSchema):
    filtros: ContratosFiltroSchema = Field(default_factory=ContratosFiltroSchema)
    agrupar_por: str | None = None
    metrica: str = "contagem"
    ordenar_por: str = "metrica"
    ordem: str = "desc"
    limite: int = 10

    @field_validator("filtros", mode="before")
    @classmethod
    def _normalize_filtros(cls, value: Any) -> ContratosFiltroSchema:
        return normalize_model_input(
            value,
            schema_type=ContratosFiltroSchema,
            field_name="filtros",
        )

    @field_validator("agrupar_por", mode="before")
    @classmethod
    def _normalize_agrupar_por(cls, value: Any) -> str | None:
        normalized = clean_text(value)
        if normalized is None:
            return None
        if normalized not in ALLOWED_GROUP_FIELDS:
            raise ValueError(f"agrupar_por nao suportado: {normalized}")
        return normalized

    @field_validator("metrica", mode="before")
    @classmethod
    def _normalize_metrica(cls, value: Any) -> str:
        normalized = clean_text(value) or "contagem"
        if normalized not in ALLOWED_METRICS:
            raise ValueError(f"metrica nao suportada: {normalized}")
        return normalized

    @field_validator("ordenar_por", mode="before")
    @classmethod
    def _normalize_ordenar_por(cls, value: Any) -> str:
        return clean_text(value) or "metrica"

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

    @model_validator(mode="after")
    def _validate_aggregation(self) -> "AgregarContratosParams":
        if self.ordenar_por not in {"metrica", self.agrupar_por}:
            raise ValueError("ordenar_por deve ser 'metrica' ou igual a agrupar_por")
        if self.agrupar_por is None and self.ordenar_por != "metrica":
            raise ValueError(
                "ordenar_por deve ser 'metrica' quando agrupar_por nao for informado"
            )
        return self


class AgregarContratosMetadata(ContratosToolBaseSchema):
    filtros_aplicados: dict[str, Any] = Field(default_factory=dict)
    filtros_fallback_aplicados: dict[str, Any] | None = None
    agrupar_por: str | None = None
    metrica: str
    ordenar_por: str
    ordem: str
    limite: int


class AgregacaoContratosItem(ContratosToolBaseSchema):
    secretaria: str | None = None
    categoria: str | None = None
    fornecedor: str | None = None
    ano_inicio: int | None = None
    contagem: int | None = None
    soma_valor: float | None = None
    media_valor: float | None = None


class AgregarContratosResponse(ContratosToolBaseSchema):
    total_grupos: int
    resultados: list[dict[str, Any]] = Field(default_factory=list)
    metadata: AgregarContratosMetadata
    valor_total: float | int | None = None
    mensagem: str | None = None
    sugestao: str | None = None
