"""Schemas da tool publica consultar_patrimonios."""

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


ALLOWED_PATRIMONIO_FIELDS = {
    "unidade_responsavel",
    "placa",
    "descricao",
    "classificacao",
    "localizacao",
    "status",
    "situacao",
    "tipo_ingresso",
    "data_aquisicao",
    "data_baixa",
    "valor_ingresso",
    "valor_atualizado",
}
ALLOWED_PATRIMONIO_SORT_FIELDS = {
    "data_aquisicao",
    "valor_atualizado",
    "valor_ingresso",
    "descricao",
    "localizacao",
    "placa",
}
ALLOWED_ORDER_VALUES = {"asc", "desc"}


class PatrimonioFiltroSchema(SqlToolBaseSchema):
    unidade_responsavel: str | None = None
    placa: str | None = None
    descricao: str | None = None
    classificacao: str | None = None
    localizacao: str | None = None
    status: str | None = None
    situacao: str | None = None
    tipo_ingresso: str | None = None
    data_aquisicao_inicio: date | None = None
    data_aquisicao_fim: date | None = None

    @field_validator(
        "unidade_responsavel",
        "placa",
        "descricao",
        "classificacao",
        "localizacao",
        "status",
        "situacao",
        "tipo_ingresso",
        mode="before",
    )
    @classmethod
    def _normalize_text(cls, value: Any) -> str | None:
        return clean_text(value)

    @field_validator("data_aquisicao_inicio", "data_aquisicao_fim", mode="before")
    @classmethod
    def _normalize_dates(cls, value: Any) -> date | None:
        return parse_date(value)


class ConsultarPatrimoniosParams(SqlToolBaseSchema):
    filtros: PatrimonioFiltroSchema = Field(default_factory=PatrimonioFiltroSchema)
    ordenar_por: str = "data_aquisicao"
    ordem: str = "desc"
    limite: int = 10
    offset: int = 0
    campos: list[str] = Field(default_factory=list)

    @field_validator("filtros", mode="before")
    @classmethod
    def _normalize_filtros(cls, value: Any) -> PatrimonioFiltroSchema:
        return normalize_model_input(
            value,
            schema_type=PatrimonioFiltroSchema,
            field_name="filtros",
        )

    @field_validator("ordenar_por", mode="before")
    @classmethod
    def _normalize_ordenar_por(cls, value: Any) -> str:
        normalized = clean_text(value) or "data_aquisicao"
        if normalized not in ALLOWED_PATRIMONIO_SORT_FIELDS:
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
            allowed_fields=ALLOWED_PATRIMONIO_FIELDS,
            require_list=False,
            error_style="campos",
        )


class ConsultarPatrimoniosMetadata(SqlToolBaseSchema):
    filtros_aplicados: dict[str, Any] = Field(default_factory=dict)
    ordenar_por: str
    ordem: str
    limite: int
    offset: int
    campos: list[str] = Field(default_factory=lambda: list(ALLOWED_PATRIMONIO_FIELDS))


class ConsultarPatrimoniosResponse(SqlToolBaseSchema):
    total: int
    resultados: list[dict[str, Any]] = Field(default_factory=list)
    metadata: ConsultarPatrimoniosMetadata
    mensagem: str | None = None
    sugestao: str | None = None
