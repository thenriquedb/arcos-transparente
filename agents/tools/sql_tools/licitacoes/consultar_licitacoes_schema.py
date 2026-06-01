"""Schemas da tool publica consultar_licitacoes."""

from __future__ import annotations

from typing import Any

from pydantic import Field, field_validator

from agents.tools.sql_tools.shared.normalization import normalize_model_input
from shared.utils.validation import clean_text, normalize_limit

from .shared.base import LicitacoesToolBaseSchema
from .shared.filters import (
    ALLOWED_BIDDING_FIELDS,
    ALLOWED_BIDDING_SORT_FIELDS,
    ALLOWED_ORDER_VALUES,
    CamposLicitacaoSchema,
    LicitacoesFiltroSchema,
)


class ConsultarLicitacoesParams(LicitacoesToolBaseSchema):
    filtros: LicitacoesFiltroSchema = Field(default_factory=LicitacoesFiltroSchema)
    ordenar_por: str = "data_abertura"
    ordem: str = "desc"
    limite: int = 10
    offset: int = 0
    campos: list[str] = Field(default_factory=list)
    incluir_detalhes: bool = False
    max_vencedores: int = 5
    max_instrumentos: int = 5
    max_itens: int = 10

    @field_validator("filtros", mode="before")
    @classmethod
    def _normalize_filtros(cls, value: Any) -> LicitacoesFiltroSchema:
        return normalize_model_input(
            value,
            schema_type=LicitacoesFiltroSchema,
            field_name="filtros",
        )

    @field_validator("ordenar_por", mode="before")
    @classmethod
    def _normalize_ordenar_por(cls, value: Any) -> str:
        normalized = clean_text(value) or "data_abertura"
        if normalized not in ALLOWED_BIDDING_SORT_FIELDS:
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
        return CamposLicitacaoSchema.model_validate({"campos": value}).campos

    @field_validator("incluir_detalhes", mode="before")
    @classmethod
    def _normalize_incluir_detalhes(cls, value: Any) -> bool:
        return bool(value)

    @field_validator("max_vencedores", "max_instrumentos", mode="before")
    @classmethod
    def _normalize_small_limits(cls, value: Any) -> int:
        return normalize_limit(value, maximum=20)

    @field_validator("max_itens", mode="before")
    @classmethod
    def _normalize_max_itens(cls, value: Any) -> int:
        return normalize_limit(value, maximum=50)


class ConsultarLicitacoesMetadata(LicitacoesToolBaseSchema):
    filtros_aplicados: dict[str, Any] = Field(default_factory=dict)
    ordenar_por: str
    ordem: str
    limite: int
    offset: int
    campos: list[str] = Field(default_factory=lambda: list(ALLOWED_BIDDING_FIELDS))
    incluir_detalhes: bool = False


class ConsultarLicitacoesResponse(LicitacoesToolBaseSchema):
    total: int
    valor_total_estimado: float | None = None
    resultados: list[dict[str, Any]] = Field(default_factory=list)
    metadata: ConsultarLicitacoesMetadata
    mensagem: str | None = None
    sugestao: str | None = None
