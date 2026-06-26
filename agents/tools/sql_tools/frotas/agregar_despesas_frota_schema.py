"""Schemas da tool publica agregar_despesas_frota."""

from __future__ import annotations

from typing import Any

from pydantic import Field, field_validator, model_validator

from agents.tools.sql_tools.shared.base import SqlToolBaseSchema
from agents.tools.sql_tools.shared.normalization import normalize_model_input
from shared.utils.validation import clean_text, normalize_limit

from .consultar_despesas_frota_schema import (
    ALLOWED_ORDER_VALUES,
    DespesasFrotaFiltroSchema,
)


ALLOWED_AGREGAR_DESPESAS_FROTA_GROUP_FIELDS = {
    "tipo_despesa",
    "descricao_evento",
    "tipo_veiculo",
    "placa_veiculo",
    "unidade_responsavel",
}
AGREGAR_DESPESAS_FROTA_GROUP_FIELD_ALIASES = {
    "tipo": "tipo_despesa",
    "despesa": "tipo_despesa",
    "despesas": "tipo_despesa",
    "tipo de despesa": "tipo_despesa",
    "evento": "descricao_evento",
    "descricao": "descricao_evento",
    "veiculo": "placa_veiculo",
    "veiculos": "placa_veiculo",
    "placa": "placa_veiculo",
    "unidade": "unidade_responsavel",
}
ALLOWED_AGREGAR_DESPESAS_FROTA_METRICS = {
    "contagem",
    "soma_total_despesa",
    "soma_valor_lancamento",
}


class AgregarDespesasFrotaParams(SqlToolBaseSchema):
    """Parametros validados da chamada da tool."""

    filtros: DespesasFrotaFiltroSchema = Field(default_factory=DespesasFrotaFiltroSchema)
    agrupar_por: str | None = "tipo_despesa"
    metrica: str = "soma_total_despesa"
    ordenar_por: str = "metrica"
    ordem: str = "desc"
    limite: int = 10

    @field_validator("filtros", mode="before")
    @classmethod
    def _normalize_filtros(cls, value: Any) -> DespesasFrotaFiltroSchema:
        return normalize_model_input(value, schema_type=DespesasFrotaFiltroSchema, field_name="filtros")

    @field_validator("agrupar_por", mode="before")
    @classmethod
    def _normalize_agrupar_por(cls, value: Any) -> str | None:
        normalized = clean_text(value)
        if normalized is None:
            return None
        normalized = AGREGAR_DESPESAS_FROTA_GROUP_FIELD_ALIASES.get(normalized, normalized)
        if normalized not in ALLOWED_AGREGAR_DESPESAS_FROTA_GROUP_FIELDS:
            raise ValueError(f"agrupar_por nao suportado: {normalized}")
        return normalized

    @field_validator("metrica", mode="before")
    @classmethod
    def _normalize_metrica(cls, value: Any) -> str:
        normalized = clean_text(value) or "soma_total_despesa"
        if normalized not in ALLOWED_AGREGAR_DESPESAS_FROTA_METRICS:
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
    def _validate_aggregation(self) -> AgregarDespesasFrotaParams:
        if self.ordenar_por not in {"metrica", self.agrupar_por}:
            raise ValueError("ordenar_por deve ser 'metrica' ou igual a agrupar_por")
        if self.agrupar_por is None and self.ordenar_por != "metrica":
            raise ValueError("ordenar_por deve ser 'metrica' quando agrupar_por nao for informado")
        return self


class AgregarDespesasFrotaMetadata(SqlToolBaseSchema):
    """Metadados ecoados na resposta."""

    filtros_aplicados: dict[str, Any] = Field(default_factory=dict)
    agrupar_por: str | None = None
    metrica: str
    ordenar_por: str
    ordem: str
    limite: int


class AgregarDespesasFrotaResponse(SqlToolBaseSchema):
    """Formato da resposta publica da tool."""

    total_grupos: int
    resultados: list[dict[str, Any]] = Field(default_factory=list)
    metadata: AgregarDespesasFrotaMetadata
    valor_total: float | int | None = None
    mensagem: str | None = None
    sugestao: str | None = None
