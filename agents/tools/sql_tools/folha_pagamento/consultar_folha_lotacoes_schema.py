"""Schemas da tool publica consultar_folha_lotacoes."""

from __future__ import annotations

from typing import Any

from pydantic import Field, field_validator

from agents.tools.sql_tools.shared.base import SqlToolBaseSchema
from agents.tools.sql_tools.shared.normalization import (
    normalize_model_input,
    normalize_selected_fields,
)
from shared.utils.validation import clean_text, normalize_limit


ALLOWED_FOLHA_LOTACOES_FIELDS = {
    "lotacao",
    "servidor",
    "cargo",
    "competencia_ano",
    "competencia_mes",
    "salario_base",
    "proventos",
    "vantagens",
    "vencimentos_totais",
    "descontos",
    "liquido",
}
ALLOWED_FOLHA_LOTACOES_SORT_FIELDS = {
    "competencia_ano",
    "competencia_mes_num",
    "lotacao",
    "servidor",
    "cargo",
    "salario_base",
    "liquido",
    "vencimentos_totais",
}
ALLOWED_ORDER_VALUES = {"asc", "desc"}


class FolhaLotacoesFiltroSchema(SqlToolBaseSchema):
    """Filtros publicos aceitos pela tool."""

    lotacao: str | None = None
    servidor: str | None = None
    cargo: str | None = None
    ano: int | None = None
    mes: int | None = None

    @field_validator("lotacao", "servidor", "cargo", mode="before")
    @classmethod
    def _normalize_text(cls, value: Any) -> str | None:
        return clean_text(value)

    @field_validator("ano", mode="before")
    @classmethod
    def _normalize_ano(cls, value: Any) -> int | None:
        if value in (None, ""):
            return None
        return int(value)

    @field_validator("mes", mode="before")
    @classmethod
    def _normalize_mes(cls, value: Any) -> int | None:
        if value in (None, ""):
            return None
        mes = int(value)
        if not 1 <= mes <= 12:
            raise ValueError("mes deve ser um inteiro de 1 a 12")
        return mes


class ConsultarFolhaLotacoesParams(SqlToolBaseSchema):
    """Parametros validados da chamada da tool."""

    filtros: FolhaLotacoesFiltroSchema = Field(default_factory=FolhaLotacoesFiltroSchema)
    ordenar_por: str = "competencia_ano"
    ordem: str = "desc"
    limite: int = 20
    offset: int = 0
    campos: list[str] = Field(default_factory=list)

    @field_validator("filtros", mode="before")
    @classmethod
    def _normalize_filtros(cls, value: Any) -> FolhaLotacoesFiltroSchema:
        return normalize_model_input(value, schema_type=FolhaLotacoesFiltroSchema, field_name="filtros")

    @field_validator("ordenar_por", mode="before")
    @classmethod
    def _normalize_ordenar_por(cls, value: Any) -> str:
        normalized = clean_text(value) or "competencia_ano"
        if normalized not in ALLOWED_FOLHA_LOTACOES_SORT_FIELDS:
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
            allowed_fields=ALLOWED_FOLHA_LOTACOES_FIELDS,
            require_list=False,
            error_style="campos",
        )


class ConsultarFolhaLotacoesMetadata(SqlToolBaseSchema):
    """Metadados ecoados na resposta."""

    filtros_aplicados: dict[str, Any] = Field(default_factory=dict)
    ordenar_por: str
    ordem: str
    limite: int
    offset: int
    campos: list[str] = Field(default_factory=lambda: list(ALLOWED_FOLHA_LOTACOES_FIELDS))


class ConsultarFolhaLotacoesResponse(SqlToolBaseSchema):
    """Formato da resposta publica da tool."""

    total: int
    resultados: list[dict[str, Any]] = Field(default_factory=list)
    metadata: ConsultarFolhaLotacoesMetadata
    mensagem: str | None = None
    sugestao: str | None = None
