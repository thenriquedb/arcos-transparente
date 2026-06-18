"""Schemas da tool publica agregar_servidores_camara."""

from __future__ import annotations

from datetime import date
from typing import Any

from pydantic import Field, field_validator, model_validator

from agents.tools.sql_tools.shared.base import SqlToolBaseSchema
from agents.tools.sql_tools.shared.normalization import normalize_model_input
from shared.utils.validation import clean_text, normalize_limit

from .shared.filters import (
    ALLOWED_CAMARA_GROUP_FIELDS,
    ALLOWED_CAMARA_METRICS,
    ALLOWED_ORDER_VALUES,
    ServidorCamaraFiltroSchema,
)


class AgregarServidoresCamaraParams(SqlToolBaseSchema):
    filtros: ServidorCamaraFiltroSchema = Field(default_factory=ServidorCamaraFiltroSchema)
    agrupar_por: str | None = None
    metrica: str = "contagem"
    ordenar_por: str = "metrica"
    ordem: str = "desc"
    limite: int = 10

    @field_validator("filtros", mode="before")
    @classmethod
    def _normalize_filtros(cls, value: Any) -> ServidorCamaraFiltroSchema:
        return normalize_model_input(value, schema_type=ServidorCamaraFiltroSchema, field_name="filtros")

    @field_validator("agrupar_por", mode="before")
    @classmethod
    def _normalize_agrupar_por(cls, value: Any) -> str | None:
        normalized = clean_text(value)
        if normalized is None:
            return None
        if normalized not in ALLOWED_CAMARA_GROUP_FIELDS:
            raise ValueError(f"agrupar_por nao suportado: {normalized}")
        return normalized

    @field_validator("metrica", mode="before")
    @classmethod
    def _normalize_metrica(cls, value: Any) -> str:
        normalized = clean_text(value) or "contagem"
        if normalized not in ALLOWED_CAMARA_METRICS:
            raise ValueError(f"metrica nao suportada: {normalized}")
        return normalized

    @field_validator("ordenar_por", mode="before")
    @classmethod
    def _normalize_ordenar_por(cls, value: Any) -> str:
        return clean_text(value) or "metrica"

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

    @model_validator(mode="after")
    def _validate_aggregation(self) -> AgregarServidoresCamaraParams:
        if self.ordenar_por not in {"metrica", self.agrupar_por}:
            raise ValueError("ordenar_por deve ser 'metrica' ou igual a agrupar_por")
        if self.agrupar_por is None and self.ordenar_por != "metrica":
            raise ValueError("ordenar_por deve ser 'metrica' quando agrupar_por nao for informado")
        return self


class AgregarServidoresCamaraMetadata(SqlToolBaseSchema):
    filtros_aplicados: dict[str, Any] = Field(default_factory=dict)
    agrupar_por: str | None = None
    metrica: str
    ordenar_por: str
    ordem: str
    limite: int
    mes_de_referencia_considerado: date | None = None
    mes_de_referencia_padrao_aplicado: bool = False


class AgregacaoServidoresCamaraItem(SqlToolBaseSchema):
    cargo: str | None = None
    lotacao: str | None = None
    situacao_funcional: str | None = None
    mes_de_referencia: date | None = None
    contagem: int | None = None
    soma_salario_base: float | None = None
    soma_liquido: float | None = None


class AgregarServidoresCamaraResponse(SqlToolBaseSchema):
    total_grupos: int
    resultados: list[dict[str, Any]] = Field(default_factory=list)
    metadata: AgregarServidoresCamaraMetadata
    valor_total: float | int | None = None
    mensagem: str | None = None
    sugestao: str | None = None
