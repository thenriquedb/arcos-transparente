"""Schemas da tool publica consultar_historico_funcional_servidor."""

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


ALLOWED_FUNCIONAL_FIELDS = {
    "nome",
    "matricula",
    "cargo_funcao",
    "lotacao",
    "situacao_funcional",
    "forma_contratacao_investidura",
    "data_admissao",
    "data_desligamento",
    "vinculo_empregaticio",
    "regime_aposentadoria",
    "horario_trabalho",
    "carga_horaria",
    "fundamento_legal",
    "local_origem_cedencia",
    "local_destino_cedencia",
    "onus_pagamento_cedencia",
    "data_inicio_cessao",
    "data_fim_cessao",
    "competencia_referencia",
}
ALLOWED_FUNCIONAL_SORT_FIELDS = {
    "nome",
    "data_admissao",
    "data_desligamento",
    "lotacao",
    "situacao_funcional",
    "cargo_funcao",
}
ALLOWED_ORDER_VALUES = {"asc", "desc"}


class ServidorFuncionalFiltroSchema(SqlToolBaseSchema):
    """Filtros publicos aceitos pela tool."""

    nome: str | None = None
    lotacao: str | None = None
    situacao_funcional: str | None = None
    forma_contratacao: str | None = None
    vinculo_empregaticio: str | None = None
    cargo_funcao: str | None = None
    data_admissao_inicio: date | None = None
    data_admissao_fim: date | None = None
    data_desligamento_inicio: date | None = None
    data_desligamento_fim: date | None = None
    em_cessao: bool | None = None

    @field_validator(
        "nome",
        "lotacao",
        "situacao_funcional",
        "forma_contratacao",
        "vinculo_empregaticio",
        "cargo_funcao",
        mode="before",
    )
    @classmethod
    def _normalize_text(cls, value: Any) -> str | None:
        return clean_text(value)

    @field_validator(
        "data_admissao_inicio",
        "data_admissao_fim",
        "data_desligamento_inicio",
        "data_desligamento_fim",
        mode="before",
    )
    @classmethod
    def _normalize_dates(cls, value: Any) -> date | None:
        return parse_date(value)

    @field_validator("em_cessao", mode="before")
    @classmethod
    def _normalize_em_cessao(cls, value: Any) -> bool | None:
        if value in (None, ""):
            return None
        if isinstance(value, bool):
            return value
        return str(value).lower() in ("true", "1", "sim", "yes")


class ConsultarHistoricoFuncionalServidorParams(SqlToolBaseSchema):
    """Parametros validados da chamada da tool."""

    filtros: ServidorFuncionalFiltroSchema = Field(default_factory=ServidorFuncionalFiltroSchema)
    ordenar_por: str = "nome"
    ordem: str = "asc"
    limite: int = 20
    offset: int = 0
    campos: list[str] = Field(default_factory=list)

    @field_validator("filtros", mode="before")
    @classmethod
    def _normalize_filtros(cls, value: Any) -> ServidorFuncionalFiltroSchema:
        return normalize_model_input(value, schema_type=ServidorFuncionalFiltroSchema, field_name="filtros")

    @field_validator("ordenar_por", mode="before")
    @classmethod
    def _normalize_ordenar_por(cls, value: Any) -> str:
        normalized = clean_text(value) or "nome"
        if normalized not in ALLOWED_FUNCIONAL_SORT_FIELDS:
            raise ValueError(f"ordenar_por nao suportado: {normalized}")
        return normalized

    @field_validator("ordem", mode="before")
    @classmethod
    def _normalize_ordem(cls, value: Any) -> str:
        normalized = (clean_text(value) or "asc").lower()
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
            allowed_fields=ALLOWED_FUNCIONAL_FIELDS,
            require_list=False,
            error_style="campos",
        )


class ConsultarHistoricoFuncionalServidorMetadata(SqlToolBaseSchema):
    """Metadados ecoados na resposta."""

    filtros_aplicados: dict[str, Any] = Field(default_factory=dict)
    ordenar_por: str
    ordem: str
    limite: int
    offset: int
    campos: list[str] = Field(default_factory=lambda: list(ALLOWED_FUNCIONAL_FIELDS))


class ConsultarHistoricoFuncionalServidorResponse(SqlToolBaseSchema):
    """Formato da resposta publica da tool."""

    total: int
    resultados: list[dict[str, Any]] = Field(default_factory=list)
    metadata: ConsultarHistoricoFuncionalServidorMetadata
    mensagem: str | None = None
    sugestao: str | None = None
