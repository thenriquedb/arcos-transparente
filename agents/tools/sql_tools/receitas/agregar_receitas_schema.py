"""Schemas da tool publica agregar_receitas."""

from __future__ import annotations

from typing import Any

from pydantic import Field, field_validator, model_validator

from agents.tools.sql_tools.shared.base import SqlToolBaseSchema
from agents.tools.sql_tools.shared.normalization import normalize_model_input
from shared.utils.validation import clean_text, normalize_limit

from .shared.filters import (
    ALLOWED_GROUP_FIELDS,
    ALLOWED_METRICS,
    ALLOWED_ORDER_VALUES,
    ReceitaFiltroSchema,
)


class AgregarReceitasParams(SqlToolBaseSchema):
    """Parametros validados da chamada da tool."""

    filtros: ReceitaFiltroSchema = Field(default_factory=ReceitaFiltroSchema)
    agrupar_por: str | None = None
    metrica: str = "soma_valor_recebido"
    ordenar_por: str = "metrica"
    ordem: str = "desc"
    limite: int = 10

    @field_validator("filtros", mode="before")
    @classmethod
    def _normalize_filtros(cls, value: Any) -> ReceitaFiltroSchema:
        return normalize_model_input(
            value,
            schema_type=ReceitaFiltroSchema,
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
        normalized = clean_text(value) or "soma_valor_recebido"
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
    def _validate_aggregation(self) -> "AgregarReceitasParams":
        if self.ordenar_por not in {"metrica", self.agrupar_por}:
            raise ValueError("ordenar_por deve ser 'metrica' ou igual a agrupar_por")
        if self.agrupar_por is None and self.ordenar_por != "metrica":
            raise ValueError(
                "ordenar_por deve ser 'metrica' quando agrupar_por nao for informado"
            )
        return self


class AgregarReceitasMetadata(SqlToolBaseSchema):
    """Metadados ecoados na resposta (filtros, ordenacao, paginacao)."""

    filtros_aplicados: dict[str, Any] = Field(default_factory=dict)
    agrupar_por: str | None = None
    metrica: str
    ordenar_por: str
    ordem: str
    limite: int


class AgregacaoReceitasItem(SqlToolBaseSchema):
    """Item individual retornado pela tool."""

    mes: str | None = None
    unidade_responsavel: str | None = None
    categoria: str | None = None
    tipo: str | None = None
    tributo: str | None = None
    origem_do_recurso: str | None = None
    contagem: int | None = None
    soma_valor_previsto: float | None = None
    soma_valor_recebido: float | None = None
    soma_valor_lancado: float | None = None
    soma_valor_em_divida_ativa: float | None = None
    soma_valor_em_cobranca_judicial: float | None = None


class AgregarReceitasResponse(SqlToolBaseSchema):
    """Formato da resposta publica da tool."""

    total_grupos: int
    resultados: list[dict[str, Any]] = Field(default_factory=list)
    metadata: AgregarReceitasMetadata
    valor_total: float | int | None = None
    mensagem: str | None = None
    sugestao: str | None = None
