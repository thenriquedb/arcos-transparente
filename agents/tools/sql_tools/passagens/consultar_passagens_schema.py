"""Schemas da tool publica consultar_passagens."""

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


ALLOWED_PASSAGENS_FIELDS = {
    "origem",
    "ano",
    "periodo_inicio",
    "periodo_fim",
    "beneficiario",
    "unidade_gestora",
    "categoria",
    "valor_empenhado",
    "valor_em_liquidacao",
    "valor_liquidado",
    "valor_pago",
    "valor_anulado",
}
ALLOWED_PASSAGENS_SORT_FIELDS = {
    "periodo_fim",
    "valor_empenhado",
    "valor_liquidado",
    "valor_pago",
    "beneficiario",
    "categoria",
}
ALLOWED_ORDER_VALUES = {"asc", "desc"}


class PassagemFiltroSchema(SqlToolBaseSchema):
    origem: str | None = None
    ano: int | None = None
    periodo_inicio: date | None = None
    periodo_fim: date | None = None
    beneficiario: str | None = None
    cpf_cnpj: str | None = None
    unidade_gestora: str | None = None
    categoria: str | None = None

    @field_validator(
        "origem",
        "beneficiario",
        "cpf_cnpj",
        "unidade_gestora",
        "categoria",
        mode="before",
    )
    @classmethod
    def _normalize_text(cls, value: Any) -> str | None:
        return clean_text(value)

    @field_validator("ano", mode="before")
    @classmethod
    def _normalize_ano(cls, value: Any) -> int | None:
        return parse_int(value)

    @field_validator("periodo_inicio", "periodo_fim", mode="before")
    @classmethod
    def _normalize_dates(cls, value: Any) -> date | None:
        return parse_date(value)


class ConsultarPassagensParams(SqlToolBaseSchema):
    filtros: PassagemFiltroSchema = Field(default_factory=PassagemFiltroSchema)
    ordenar_por: str = "periodo_fim"
    ordem: str = "desc"
    limite: int = 10
    offset: int = 0
    campos: list[str] = Field(default_factory=list)

    @field_validator("filtros", mode="before")
    @classmethod
    def _normalize_filtros(cls, value: Any) -> PassagemFiltroSchema:
        return normalize_model_input(
            value,
            schema_type=PassagemFiltroSchema,
            field_name="filtros",
        )

    @field_validator("ordenar_por", mode="before")
    @classmethod
    def _normalize_ordenar_por(cls, value: Any) -> str:
        normalized = clean_text(value) or "periodo_fim"
        if normalized not in ALLOWED_PASSAGENS_SORT_FIELDS:
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
            allowed_fields=ALLOWED_PASSAGENS_FIELDS,
            require_list=False,
            error_style="campos",
        )


class ConsultarPassagensMetadata(SqlToolBaseSchema):
    filtros_aplicados: dict[str, Any] = Field(default_factory=dict)
    ordenar_por: str
    ordem: str
    limite: int
    offset: int
    campos: list[str] = Field(default_factory=lambda: list(ALLOWED_PASSAGENS_FIELDS))


class ConsultarPassagensResponse(SqlToolBaseSchema):
    total: int
    resultados: list[dict[str, Any]] = Field(default_factory=list)
    metadata: ConsultarPassagensMetadata
    mensagem: str | None = None
    sugestao: str | None = None
