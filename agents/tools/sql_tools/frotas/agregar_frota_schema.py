"""Schemas da tool publica agregar_frota."""

from __future__ import annotations

from typing import Any

from pydantic import Field, field_validator, model_validator

from agents.tools.sql_tools.shared.base import SqlToolBaseSchema
from agents.tools.sql_tools.shared.normalization import normalize_model_input
from shared.utils.validation import clean_text, normalize_limit

from .consultar_frota_schema import (
    ALLOWED_ORDER_VALUES,
    FrotaFiltroSchema,
)


ALLOWED_FROTA_GROUP_FIELDS = {
    "placa_veiculo",
    "unidade_responsavel",
    "tipo_veiculo",
    "situacao",
    "localizacao",
    "marca",
}
FROTA_GROUP_FIELD_ALIASES = {
    "placa": "placa_veiculo",
    "placa do veiculo": "placa_veiculo",
    "veiculo": "placa_veiculo",
    "veiculos": "placa_veiculo",
}
ALLOWED_FROTA_AGGREGATE_METRICS = {
    "contagem",
    "soma_valor_atual",
    "soma_total_despesas",
}


class AgregarFrotaParams(SqlToolBaseSchema):
    """Parametros validados da chamada da tool."""

    filtros: FrotaFiltroSchema = Field(default_factory=FrotaFiltroSchema)
    agrupar_por: str | None = None
    metrica: str = "contagem"
    ordenar_por: str = "metrica"
    ordem: str = "desc"
    limite: int = 10

    @field_validator("filtros", mode="before")
    @classmethod
    def _normalize_filtros(cls, value: Any) -> FrotaFiltroSchema:
        return normalize_model_input(value, schema_type=FrotaFiltroSchema, field_name="filtros")

    @field_validator("agrupar_por", mode="before")
    @classmethod
    def _normalize_agrupar_por(cls, value: Any) -> str | None:
        normalized = clean_text(value)
        if normalized is None:
            return None
        normalized = FROTA_GROUP_FIELD_ALIASES.get(normalized, normalized)
        if normalized not in ALLOWED_FROTA_GROUP_FIELDS:
            raise ValueError(f"agrupar_por nao suportado: {normalized}")
        return normalized

    @field_validator("metrica", mode="before")
    @classmethod
    def _normalize_metrica(cls, value: Any) -> str:
        normalized = clean_text(value) or "contagem"
        if normalized not in ALLOWED_FROTA_AGGREGATE_METRICS:
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
    def _validate_aggregation(self) -> AgregarFrotaParams:
        if self.ordenar_por not in {"metrica", self.agrupar_por}:
            raise ValueError("ordenar_por deve ser 'metrica' ou igual a agrupar_por")
        if self.agrupar_por is None and self.ordenar_por != "metrica":
            raise ValueError("ordenar_por deve ser 'metrica' quando agrupar_por nao for informado")
        return self


class AgregarFrotaMetadata(SqlToolBaseSchema):
    """Metadados ecoados na resposta."""

    filtros_aplicados: dict[str, Any] = Field(default_factory=dict)
    agrupar_por: str | None = None
    metrica: str
    ordenar_por: str
    ordem: str
    limite: int


class AgregarFrotaResponse(SqlToolBaseSchema):
    """Formato da resposta publica da tool."""

    total_grupos: int
    resultados: list[dict[str, Any]] = Field(default_factory=list)
    metadata: AgregarFrotaMetadata
    valor_total: float | int | None = None
    mensagem: str | None = None
    sugestao: str | None = None
