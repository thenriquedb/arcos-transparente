"""Schemas da tool publica consultar_despesas_frota."""

from __future__ import annotations

from datetime import date
from typing import Any

from pydantic import Field, field_validator

from agents.tools.sql_tools.shared.base import SqlToolBaseSchema
from agents.tools.sql_tools.shared.normalization import (
    normalize_model_input,
    normalize_selected_fields,
)
from shared.utils.validation import clean_text, normalize_limit, parse_date


ALLOWED_DESPESAS_FROTA_FIELDS = {
    "placa_veiculo",
    "tipo_veiculo",
    "descricao_material",
    "unidade_gestora",
    "descricao_evento",
    "tipo_despesa",
    "data_evento",
    "quantidade_lancamento",
    "valor_lancamento",
    "total_despesa",
}
ALLOWED_DESPESAS_FROTA_SORT_FIELDS = {
    "data_evento",
    "total_despesa",
    "valor_lancamento",
    "placa_veiculo",
    "tipo_despesa",
}
ALLOWED_ORDER_VALUES = {"asc", "desc"}


class DespesasFrotaFiltroSchema(SqlToolBaseSchema):
    """Filtros publicos aceitos pela tool."""

    placa: str | None = None
    tipo_veiculo: str | None = None
    tipo_despesa: str | None = None
    descricao: str | None = None
    data_evento_inicio: date | None = None
    data_evento_fim: date | None = None

    @field_validator("placa", "tipo_veiculo", "tipo_despesa", "descricao", mode="before")
    @classmethod
    def _normalize_text(cls, value: Any) -> str | None:
        return clean_text(value)

    @field_validator("data_evento_inicio", "data_evento_fim", mode="before")
    @classmethod
    def _normalize_dates(cls, value: Any) -> date | None:
        return parse_date(value)


class ConsultarDespesasFrotaParams(SqlToolBaseSchema):
    """Parametros validados da chamada da tool."""

    filtros: DespesasFrotaFiltroSchema = Field(default_factory=DespesasFrotaFiltroSchema)
    ordenar_por: str = "data_evento"
    ordem: str = "desc"
    limite: int = 20
    offset: int = 0
    campos: list[str] = Field(default_factory=list)

    @field_validator("filtros", mode="before")
    @classmethod
    def _normalize_filtros(cls, value: Any) -> DespesasFrotaFiltroSchema:
        return normalize_model_input(value, schema_type=DespesasFrotaFiltroSchema, field_name="filtros")

    @field_validator("ordenar_por", mode="before")
    @classmethod
    def _normalize_ordenar_por(cls, value: Any) -> str:
        normalized = clean_text(value) or "data_evento"
        if normalized not in ALLOWED_DESPESAS_FROTA_SORT_FIELDS:
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
        return max(0, int(value))

    @field_validator("campos", mode="before")
    @classmethod
    def _normalize_campos(cls, value: Any) -> list[str]:
        return normalize_selected_fields(
            value,
            allowed_fields=ALLOWED_DESPESAS_FROTA_FIELDS,
            require_list=False,
            error_style="campos",
        )


class ConsultarDespesasFrotaMetadata(SqlToolBaseSchema):
    """Metadados ecoados na resposta."""

    filtros_aplicados: dict[str, Any] = Field(default_factory=dict)
    ordenar_por: str
    ordem: str
    limite: int
    offset: int
    campos: list[str] = Field(default_factory=lambda: list(ALLOWED_DESPESAS_FROTA_FIELDS))


class ConsultarDespesasFrotaResponse(SqlToolBaseSchema):
    """Formato da resposta publica da tool."""

    total: int
    resultados: list[dict[str, Any]] = Field(default_factory=list)
    metadata: ConsultarDespesasFrotaMetadata
    mensagem: str | None = None
    sugestao: str | None = None
