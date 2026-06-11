"""Schemas da tool publica consultar_estoques."""

from __future__ import annotations

from datetime import date
from decimal import Decimal
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
    parse_number,
    validate_date_period,
)


DEFAULT_ESTOQUES_FIELDS = (
    "origem",
    "ano",
    "material",
    "unidade_medida",
    "periodo_inicio",
    "periodo_fim",
    "saldo_anterior_quantidade",
    "saldo_anterior_valor",
    "entrada_quantidade",
    "entrada_valor",
    "saida_quantidade",
    "saida_valor",
    "saldo_quantidade",
    "saldo_valor",
)
ALLOWED_ESTOQUES_FIELDS = set(DEFAULT_ESTOQUES_FIELDS)
ALLOWED_ESTOQUES_SORT_FIELDS = {
    "periodo_fim",
    "material",
    "entrada_valor",
    "saida_valor",
    "saldo_quantidade",
    "saldo_valor",
}
ALLOWED_ORDER_VALUES = {"asc", "desc"}


class EstoqueFiltroSchema(SqlToolBaseSchema):
    """Filtros publicos aceitos pela tool deste dominio."""

    origem: str | None = None
    ano: int | None = None
    material: str | None = None
    unidade_medida: str | None = None
    periodo_inicio: date | None = None
    periodo_fim: date | None = None
    entrada_valor_min: Decimal | None = None
    entrada_valor_max: Decimal | None = None
    saida_valor_min: Decimal | None = None
    saida_valor_max: Decimal | None = None
    saldo_quantidade_min: Decimal | None = None
    saldo_quantidade_max: Decimal | None = None
    saldo_valor_min: Decimal | None = None
    saldo_valor_max: Decimal | None = None

    @field_validator("origem", "material", "unidade_medida", mode="before")
    @classmethod
    def _normalize_text(cls, value: Any) -> str | None:
        return clean_text(value)

    @field_validator("ano", mode="before")
    @classmethod
    def _normalize_year(cls, value: Any) -> int | None:
        return parse_int(value)

    @field_validator("periodo_inicio", "periodo_fim", mode="before")
    @classmethod
    def _normalize_dates(cls, value: Any) -> date | None:
        return parse_date(value)

    @field_validator(
        "entrada_valor_min",
        "entrada_valor_max",
        "saida_valor_min",
        "saida_valor_max",
        "saldo_quantidade_min",
        "saldo_quantidade_max",
        "saldo_valor_min",
        "saldo_valor_max",
        mode="before",
    )
    @classmethod
    def _normalize_numbers(cls, value: Any) -> Decimal | None:
        return parse_number(value)

    @model_validator(mode="after")
    def _validate_filters(self) -> EstoqueFiltroSchema:
        if self.periodo_inicio and self.periodo_fim:
            validate_date_period(self.periodo_inicio, self.periodo_fim)
        range_pairs = (
            ("entrada_valor_min", "entrada_valor_max"),
            ("saida_valor_min", "saida_valor_max"),
            ("saldo_quantidade_min", "saldo_quantidade_max"),
            ("saldo_valor_min", "saldo_valor_max"),
        )
        for min_field, max_field in range_pairs:
            min_value = getattr(self, min_field)
            max_value = getattr(self, max_field)
            if min_value is not None and max_value is not None and min_value > max_value:
                raise ValueError(f"{min_field} deve ser menor ou igual a {max_field}")
        return self


class ConsultarEstoquesParams(SqlToolBaseSchema):
    """Parametros validados da chamada da tool."""

    filtros: EstoqueFiltroSchema = Field(default_factory=EstoqueFiltroSchema)
    ordenar_por: str = "periodo_fim"
    ordem: str = "desc"
    limite: int = 10
    offset: int = 0
    campos: list[str] = Field(default_factory=list)

    @field_validator("filtros", mode="before")
    @classmethod
    def _normalize_filtros(cls, value: Any) -> EstoqueFiltroSchema:
        return normalize_model_input(
            value,
            schema_type=EstoqueFiltroSchema,
            field_name="filtros",
        )

    @field_validator("ordenar_por", mode="before")
    @classmethod
    def _normalize_ordenar_por(cls, value: Any) -> str:
        normalized = clean_text(value) or "periodo_fim"
        if normalized not in ALLOWED_ESTOQUES_SORT_FIELDS:
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
            allowed_fields=ALLOWED_ESTOQUES_FIELDS,
            require_list=False,
            error_style="campos",
        )


class ConsultarEstoquesMetadata(SqlToolBaseSchema):
    """Metadados ecoados na resposta (filtros, ordenacao, paginacao)."""

    filtros_aplicados: dict[str, Any] = Field(default_factory=dict)
    ordenar_por: str
    ordem: str
    limite: int
    offset: int
    campos: list[str] = Field(default_factory=lambda: list(DEFAULT_ESTOQUES_FIELDS))


class ConsultarEstoquesResponse(SqlToolBaseSchema):
    """Formato da resposta publica da tool."""

    total: int
    resultados: list[dict[str, Any]] = Field(default_factory=list)
    metadata: ConsultarEstoquesMetadata
    mensagem: str | None = None
    sugestao: str | None = None
