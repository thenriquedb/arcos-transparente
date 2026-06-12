"""Schemas da tool publica consultar_itens_adquiridos_contrato."""

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


ALLOWED_ITENS_FIELDS = {
    "numero_contrato",
    "fornecedor",
    "secretaria",
    "categoria",
    "data_inicio",
    "numero_lote",
    "numero_item",
    "identificacao",
    "quantidade",
    "valor_unitario",
    "valor_total",
}
ALLOWED_ITENS_SORT_FIELDS = {
    "valor_total",
    "valor_unitario",
    "quantidade",
    "identificacao",
    "numero_contrato",
}
ALLOWED_ORDER_VALUES = {"asc", "desc"}


class ItensFiltroSchema(SqlToolBaseSchema):
    """Filtros publicos aceitos pela tool."""

    numero_contrato: str | None = None
    fornecedor: str | None = None
    secretaria: str | None = None
    identificacao: str | None = None
    data_inicio_inicio: date | None = None
    data_inicio_fim: date | None = None

    @field_validator(
        "numero_contrato",
        "fornecedor",
        "secretaria",
        "identificacao",
        mode="before",
    )
    @classmethod
    def _normalize_text(cls, value: Any) -> str | None:
        return clean_text(value)

    @field_validator("data_inicio_inicio", "data_inicio_fim", mode="before")
    @classmethod
    def _normalize_dates(cls, value: Any) -> date | None:
        return parse_date(value)


class ConsultarItensAdquiridosContratoParams(SqlToolBaseSchema):
    """Parametros validados da chamada da tool."""

    filtros: ItensFiltroSchema = Field(default_factory=ItensFiltroSchema)
    ordenar_por: str = "valor_total"
    ordem: str = "desc"
    limite: int = 20
    offset: int = 0
    campos: list[str] = Field(default_factory=list)

    @field_validator("filtros", mode="before")
    @classmethod
    def _normalize_filtros(cls, value: Any) -> ItensFiltroSchema:
        return normalize_model_input(value, schema_type=ItensFiltroSchema, field_name="filtros")

    @field_validator("ordenar_por", mode="before")
    @classmethod
    def _normalize_ordenar_por(cls, value: Any) -> str:
        normalized = clean_text(value) or "valor_total"
        if normalized not in ALLOWED_ITENS_SORT_FIELDS:
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
            allowed_fields=ALLOWED_ITENS_FIELDS,
            require_list=False,
            error_style="campos",
        )


class ConsultarItensAdquiridosContratoMetadata(SqlToolBaseSchema):
    """Metadados ecoados na resposta."""

    filtros_aplicados: dict[str, Any] = Field(default_factory=dict)
    ordenar_por: str
    ordem: str
    limite: int
    offset: int
    campos: list[str] = Field(default_factory=lambda: list(ALLOWED_ITENS_FIELDS))


class ConsultarItensAdquiridosContratoResponse(SqlToolBaseSchema):
    """Formato da resposta publica da tool."""

    total: int
    resultados: list[dict[str, Any]] = Field(default_factory=list)
    metadata: ConsultarItensAdquiridosContratoMetadata
    mensagem: str | None = None
    sugestao: str | None = None
