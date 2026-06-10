"""Schemas da tool publica consultar_eleitos."""

from __future__ import annotations

from typing import Any

from pydantic import Field, field_validator

from agents.tools.sql_tools.shared.base import SqlToolBaseSchema
from agents.tools.sql_tools.shared.normalization import (
    normalize_model_input,
    normalize_selected_fields,
)
from shared.utils.validation import clean_text, normalize_limit, parse_int


ALLOWED_ELEITO_FIELDS = {
    "tipo_politico",
    "id_origem",
    "nome_completo",
    "nome_popular",
    "partido",
    "telefone",
    "email",
    "homepage",
    "numero_gabinete",
    "cargo",
    "biografia",
    "mandato_inicio",
    "mandato_fim",
    "mandato_status",
    "mandato_observacao",
    "municipio",
    "estado",
}
ALLOWED_ELEITO_SORT_FIELDS = {
    "mandato_inicio",
    "mandato_fim",
    "nome",
    "partido",
    "tipo_politico",
}
ALLOWED_ORDER_VALUES = {"asc", "desc"}
ALLOWED_TIPO_POLITICO = {"vereador", "prefeito", "vice-prefeito"}


class EleitoToolBaseSchema(SqlToolBaseSchema):
    pass


class EleitoFiltroSchema(EleitoToolBaseSchema):
    """Filtros publicos aceitos pela tool deste dominio."""

    tipo_politico: str | None = None
    nome: str | None = None
    nome_popular: str | None = None
    partido: str | None = None
    cargo: str | None = None
    status_mandato: str | None = None
    ano: int | None = None
    em_exercicio: bool | None = None
    municipio: str | None = None
    estado: str | None = None

    @field_validator(
        "tipo_politico",
        "nome",
        "nome_popular",
        "partido",
        "cargo",
        "status_mandato",
        "municipio",
        "estado",
        mode="before",
    )
    @classmethod
    def _normalize_text(cls, value: Any) -> str | None:
        return clean_text(value)

    @field_validator("tipo_politico", mode="after")
    @classmethod
    def _validate_tipo_politico(cls, value: str | None) -> str | None:
        if value is None:
            return None
        normalized = value.lower()
        if normalized not in ALLOWED_TIPO_POLITICO:
            raise ValueError(f"tipo_politico nao suportado: {value}")
        return normalized

    @field_validator("ano", mode="before")
    @classmethod
    def _normalize_ano(cls, value: Any) -> int | None:
        return parse_int(value)

    @field_validator("em_exercicio", mode="before")
    @classmethod
    def _normalize_em_exercicio(cls, value: Any) -> bool | None:
        if value is None:
            return None
        if isinstance(value, bool):
            return value
        text = (clean_text(value) or "").lower()
        if text in {"sim", "true", "1"}:
            return True
        if text in {"nao", "não", "false", "0"}:
            return False
        raise ValueError("em_exercicio deve ser booleano")


class ConsultarEleitosParams(EleitoToolBaseSchema):
    """Parametros validados da chamada da tool."""

    filtros: EleitoFiltroSchema = Field(default_factory=EleitoFiltroSchema)
    ordenar_por: str = "mandato_inicio"
    ordem: str = "desc"
    limite: int = 10
    offset: int = 0
    campos: list[str] = Field(default_factory=list)

    @field_validator("filtros", mode="before")
    @classmethod
    def _normalize_filtros(cls, value: Any) -> EleitoFiltroSchema:
        return normalize_model_input(
            value,
            schema_type=EleitoFiltroSchema,
            field_name="filtros",
        )

    @field_validator("ordenar_por", mode="before")
    @classmethod
    def _normalize_ordenar_por(cls, value: Any) -> str:
        normalized = clean_text(value) or "mandato_inicio"
        if normalized not in ALLOWED_ELEITO_SORT_FIELDS:
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
            allowed_fields=ALLOWED_ELEITO_FIELDS,
            require_list=True,
            error_style="campos",
        )


class ConsultarEleitosMetadata(EleitoToolBaseSchema):
    """Metadados ecoados na resposta (filtros, ordenacao, paginacao)."""

    filtros_aplicados: dict[str, Any] = Field(default_factory=dict)
    ordenar_por: str
    ordem: str
    limite: int
    offset: int
    campos: list[str] = Field(default_factory=lambda: list(ALLOWED_ELEITO_FIELDS))


class ConsultarEleitosResponse(EleitoToolBaseSchema):
    """Formato da resposta publica da tool."""

    total: int
    resultados: list[dict[str, Any]] = Field(default_factory=list)
    metadata: ConsultarEleitosMetadata
    mensagem: str | None = None
    sugestao: str | None = None
