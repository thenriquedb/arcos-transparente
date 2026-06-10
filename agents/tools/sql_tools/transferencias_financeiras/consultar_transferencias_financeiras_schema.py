"""Schemas da tool publica consultar_transferencias_financeiras."""

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


ALLOWED_TIPO_REGISTRO_VALUES = {"movimentacao", "emenda"}
ALLOWED_TRANSFERENCIAS_FIELDS = {
    "tipo_registro",
    "ano",
    "data",
    "identificacao",
    "unidade_concessora",
    "unidade_recebedora",
    "tipo_movimento",
    "finalidade",
    "fonte_recurso",
    "detalhamento_fonte",
    "programacao_inicial",
    "valor",
    "exercicio_consulta",
    "ano_numero",
    "autor",
    "objeto",
    "tipo_emenda",
    "funcao",
}
ALLOWED_TRANSFERENCIAS_SORT_FIELDS = {
    "ano",
    "data",
    "valor",
    "tipo_registro",
    "unidade_recebedora",
    "tipo_movimento",
    "autor",
    "funcao",
    "ano_numero",
}
ALLOWED_ORDER_VALUES = {"asc", "desc"}


class TransferenciasFinanceirasFiltroSchema(SqlToolBaseSchema):
    """Filtros publicos aceitos pela tool deste dominio."""

    tipo_registro: str | None = None
    ano: int | None = None
    data_inicio: date | None = None
    data_fim: date | None = None
    identificacao: str | None = None
    unidade_concessora: str | None = None
    unidade_recebedora: str | None = None
    tipo_movimento: str | None = None
    finalidade: str | None = None
    fonte_recurso: str | None = None
    exercicio_consulta: int | None = None
    ano_numero: str | None = None
    autor: str | None = None
    objeto: str | None = None
    tipo_emenda: str | None = None
    funcao: str | None = None

    @field_validator(
        "identificacao",
        "unidade_concessora",
        "unidade_recebedora",
        "tipo_movimento",
        "finalidade",
        "fonte_recurso",
        "ano_numero",
        "autor",
        "objeto",
        "tipo_emenda",
        "funcao",
        mode="before",
    )
    @classmethod
    def _normalize_text(cls, value: Any) -> str | None:
        return clean_text(value)

    @field_validator("tipo_registro", mode="before")
    @classmethod
    def _normalize_tipo_registro(cls, value: Any) -> str | None:
        normalized = clean_text(value)
        if normalized is None:
            return None
        if normalized not in ALLOWED_TIPO_REGISTRO_VALUES:
            raise ValueError(f"tipo_registro nao suportado: {normalized}")
        return normalized

    @field_validator("ano", "exercicio_consulta", mode="before")
    @classmethod
    def _normalize_ints(cls, value: Any) -> int | None:
        return parse_int(value)

    @field_validator("data_inicio", "data_fim", mode="before")
    @classmethod
    def _normalize_dates(cls, value: Any) -> date | None:
        return parse_date(value)


class ConsultarTransferenciasFinanceirasParams(SqlToolBaseSchema):
    """Parametros validados da chamada da tool."""

    filtros: TransferenciasFinanceirasFiltroSchema = Field(default_factory=TransferenciasFinanceirasFiltroSchema)
    ordenar_por: str = "data"
    ordem: str = "desc"
    limite: int = 10
    offset: int = 0
    campos: list[str] = Field(default_factory=list)

    @field_validator("filtros", mode="before")
    @classmethod
    def _normalize_filtros(
        cls,
        value: Any,
    ) -> TransferenciasFinanceirasFiltroSchema:
        return normalize_model_input(
            value,
            schema_type=TransferenciasFinanceirasFiltroSchema,
            field_name="filtros",
        )

    @field_validator("ordenar_por", mode="before")
    @classmethod
    def _normalize_ordenar_por(cls, value: Any) -> str:
        normalized = clean_text(value) or "data"
        if normalized not in ALLOWED_TRANSFERENCIAS_SORT_FIELDS:
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
            allowed_fields=ALLOWED_TRANSFERENCIAS_FIELDS,
            require_list=False,
            error_style="campos",
        )


class ConsultarTransferenciasFinanceirasMetadata(SqlToolBaseSchema):
    """Metadados ecoados na resposta (filtros, ordenacao, paginacao)."""

    filtros_aplicados: dict[str, Any] = Field(default_factory=dict)
    ordenar_por: str
    ordem: str
    limite: int
    offset: int
    campos: list[str] = Field(default_factory=lambda: list(ALLOWED_TRANSFERENCIAS_FIELDS))


class ConsultarTransferenciasFinanceirasResponse(SqlToolBaseSchema):
    """Formato da resposta publica da tool."""

    total: int
    resultados: list[dict[str, Any]] = Field(default_factory=list)
    metadata: ConsultarTransferenciasFinanceirasMetadata
    mensagem: str | None = None
    sugestao: str | None = None
