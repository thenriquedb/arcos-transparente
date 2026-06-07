"""Schemas da tool publica consultar_despesas."""

from __future__ import annotations

from datetime import date
from typing import Any

from pydantic import Field, field_validator

from agents.tools.sql_tools.shared.base import SqlToolBaseSchema
from agents.tools.sql_tools.shared.normalization import (
    normalize_model_input,
    normalize_selected_fields,
)
from shared.utils.validation import clean_text, normalize_limit, parse_date, parse_int


ALLOWED_DESPESA_FIELDS = {
    "tipo",
    "origem",
    "ano",
    "data",
    "numero",
    "unidade_responsavel",
    "area",
    "credor",
    "valor_documento",
    "valor_empenhado",
    "valor_pago",
    "valor_anulado",
    "descricao",
    "conta_extra",
    "contrato",
}
ALLOWED_DESPESA_SORT_FIELDS = {
    "data",
    "valor_documento",
    "valor_empenhado",
    "valor_pago",
    "credor",
    "numero",
}
ALLOWED_ORDER_VALUES = {"asc", "desc"}
ALLOWED_TIPOS = {
    "empenho",
    "restos_a_pagar",
    "documento_extra",
    "diaria",
    "passagem",
}


class DespesaFiltroSchema(SqlToolBaseSchema):
    tipo: str | None = None
    origem: str | None = None
    ano: int | None = None
    data_inicio: date | None = None
    data_fim: date | None = None
    numero: str | None = None
    credor: str | None = None
    cpf_cnpj: str | None = None
    unidade_responsavel: str | None = None
    area: str | None = None
    conta_extra: str | None = None
    contrato: str | None = None
    descricao: str | None = None

    @field_validator(
        "tipo",
        "origem",
        "numero",
        "credor",
        "cpf_cnpj",
        "unidade_responsavel",
        "area",
        "conta_extra",
        "contrato",
        "descricao",
        mode="before",
    )
    @classmethod
    def _normalize_text(cls, value: Any) -> str | None:
        return clean_text(value)

    @field_validator("tipo")
    @classmethod
    def _validate_tipo(cls, value: str | None) -> str | None:
        if value is not None and value not in ALLOWED_TIPOS:
            raise ValueError(f"tipo nao suportado: {value}")
        return value

    @field_validator("ano", mode="before")
    @classmethod
    def _normalize_ano(cls, value: Any) -> int | None:
        return parse_int(value)

    @field_validator("data_inicio", "data_fim", mode="before")
    @classmethod
    def _normalize_dates(cls, value: Any) -> date | None:
        return parse_date(value)


class ConsultarDespesasParams(SqlToolBaseSchema):
    filtros: DespesaFiltroSchema = Field(default_factory=DespesaFiltroSchema)
    ordenar_por: str = "data"
    ordem: str = "desc"
    limite: int = 10
    offset: int = 0
    campos: list[str] = Field(default_factory=list)

    @field_validator("filtros", mode="before")
    @classmethod
    def _normalize_filtros(cls, value: Any) -> DespesaFiltroSchema:
        return normalize_model_input(
            value,
            schema_type=DespesaFiltroSchema,
            field_name="filtros",
        )

    @field_validator("ordenar_por", mode="before")
    @classmethod
    def _normalize_ordenar_por(cls, value: Any) -> str:
        normalized = clean_text(value) or "data"
        if normalized not in ALLOWED_DESPESA_SORT_FIELDS:
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
            allowed_fields=ALLOWED_DESPESA_FIELDS,
            require_list=False,
            error_style="campos",
        )


class ConsultarDespesasMetadata(SqlToolBaseSchema):
    filtros_aplicados: dict[str, Any] = Field(default_factory=dict)
    ordenar_por: str
    ordem: str
    limite: int
    offset: int
    campos: list[str] = Field(default_factory=lambda: list(ALLOWED_DESPESA_FIELDS))


class ConsultarDespesasResponse(SqlToolBaseSchema):
    total: int
    resultados: list[dict[str, Any]] = Field(default_factory=list)
    metadata: ConsultarDespesasMetadata
    mensagem: str | None = None
    sugestao: str | None = None
