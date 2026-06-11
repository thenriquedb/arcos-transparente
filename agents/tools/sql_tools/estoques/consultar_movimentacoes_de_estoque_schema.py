"""Schemas da tool publica consultar_movimentacoes_de_estoque."""

from __future__ import annotations

from datetime import date
from typing import Any

from pydantic import Field, field_validator, model_validator

from agents.tools.sql_tools.shared.base import SqlToolBaseSchema
from agents.tools.sql_tools.shared.normalization import (
    normalize_model_input,
    normalize_selected_fields,
)
from shared.utils.validation import (
    clean_text,
    parse_date,
    parse_int,
    validate_date_period,
)


DEFAULT_ESTOQUE_MOVEMENT_FIELDS = (
    "origem",
    "ano",
    "material",
    "unidade_medida",
    "data_movimento",
    "tipo_movimento",
    "unidade_gestora",
    "almoxarifado",
    "localizacao",
    "classificacao",
    "quantidade",
    "valor_unitario",
    "valor_total",
    "custo_medio",
)
ALLOWED_ESTOQUE_MOVEMENT_FIELDS = set(DEFAULT_ESTOQUE_MOVEMENT_FIELDS)
ALLOWED_ESTOQUE_MOVEMENT_SORT_FIELDS = {
    "data_movimento",
    "material",
    "tipo_movimento",
    "quantidade",
    "valor_total",
    "almoxarifado",
}
ALLOWED_ORDER_VALUES = {"asc", "desc"}


class EstoqueMovimentacaoFiltroSchema(SqlToolBaseSchema):
    """Filtros publicos aceitos pela tool deste dominio."""

    origem: str | None = None
    ano: int | None = None
    material: str | None = None
    data_movimento_inicio: date | None = None
    data_movimento_fim: date | None = None
    tipo_movimento: str | None = None
    unidade_gestora: str | None = None
    almoxarifado: str | None = None
    localizacao: str | None = None
    classificacao: str | None = None

    @field_validator(
        "origem",
        "material",
        "tipo_movimento",
        "unidade_gestora",
        "almoxarifado",
        "localizacao",
        "classificacao",
        mode="before",
    )
    @classmethod
    def _normalize_text(cls, value: Any) -> str | None:
        return clean_text(value)

    @field_validator("ano", mode="before")
    @classmethod
    def _normalize_year(cls, value: Any) -> int | None:
        return parse_int(value)

    @field_validator("data_movimento_inicio", "data_movimento_fim", mode="before")
    @classmethod
    def _normalize_dates(cls, value: Any) -> date | None:
        return parse_date(value)

    @model_validator(mode="after")
    def _validate_dates(self) -> EstoqueMovimentacaoFiltroSchema:
        if self.data_movimento_inicio and self.data_movimento_fim:
            validate_date_period(self.data_movimento_inicio, self.data_movimento_fim)
        return self


class ConsultarMovimentacoesDeEstoqueParams(SqlToolBaseSchema):
    """Parametros validados da chamada da tool."""

    filtros: EstoqueMovimentacaoFiltroSchema = Field(default_factory=EstoqueMovimentacaoFiltroSchema)
    ordenar_por: str = "data_movimento"
    ordem: str = "desc"
    limite: int = 10
    offset: int = 0
    campos: list[str] = Field(default_factory=list)

    @field_validator("filtros", mode="before")
    @classmethod
    def _normalize_filtros(cls, value: Any) -> EstoqueMovimentacaoFiltroSchema:
        return normalize_model_input(
            value,
            schema_type=EstoqueMovimentacaoFiltroSchema,
            field_name="filtros",
        )

    @field_validator("ordenar_por", mode="before")
    @classmethod
    def _normalize_ordenar_por(cls, value: Any) -> str:
        normalized = clean_text(value) or "data_movimento"
        if normalized not in ALLOWED_ESTOQUE_MOVEMENT_SORT_FIELDS:
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
        if value is None:
            return 10
        return max(1, min(int(value), 100))

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
            allowed_fields=ALLOWED_ESTOQUE_MOVEMENT_FIELDS,
            require_list=False,
            error_style="campos",
        )


class ConsultarMovimentacoesDeEstoqueMetadata(SqlToolBaseSchema):
    """Metadados ecoados na resposta (filtros, ordenacao, paginacao)."""

    filtros_aplicados: dict[str, Any] = Field(default_factory=dict)
    ordenar_por: str
    ordem: str
    limite: int
    offset: int
    campos: list[str] = Field(default_factory=lambda: list(DEFAULT_ESTOQUE_MOVEMENT_FIELDS))


class ConsultarMovimentacoesDeEstoqueResponse(SqlToolBaseSchema):
    """Formato da resposta publica da tool."""

    total: int
    resultados: list[dict[str, Any]] = Field(default_factory=list)
    metadata: ConsultarMovimentacoesDeEstoqueMetadata
    mensagem: str | None = None
    sugestao: str | None = None
