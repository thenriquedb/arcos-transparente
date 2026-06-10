"""Schemas da tool publica agregar_estoques."""

from __future__ import annotations

from datetime import date
from typing import Any

from pydantic import Field, field_validator, model_validator

from agents.tools.sql_tools.shared.base import SqlToolBaseSchema
from agents.tools.sql_tools.shared.normalization import normalize_model_input
from shared.utils.validation import (
    clean_text,
    normalize_limit,
    parse_date,
    validate_date_period,
)

from .consultar_estoques_schema import ALLOWED_ORDER_VALUES, EstoqueFiltroSchema


ALLOWED_ESTOQUES_GROUP_FIELDS = {
    "origem",
    "ano",
    "unidade_medida",
    "material",
}
ESTOQUES_GROUP_FIELD_ALIASES = {
    "descricao": "material",
    "descricao do material": "material",
    "descricao_material": "material",
    "descricao do item": "material",
    "nome": "material",
    "nome do material": "material",
    "nome_material": "material",
    "item": "material",
    "itens": "material",
    "tipo": "material",
    "tipo de item": "material",
    "tipo de material": "material",
    "tipo_material": "material",
    "categoria": "material",
    "produto": "material",
    "produtos": "material",
}
ALLOWED_ESTOQUES_METRICS = {
    "contagem",
    "soma_entrada_quantidade",
    "soma_entrada_valor",
    "soma_movimentacao_quantidade",
    "soma_movimentacao_valor",
    "soma_saida_quantidade",
    "soma_saida_valor",
    "soma_saldo_quantidade",
    "soma_saldo_valor",
}
ESTOQUES_METRIC_ALIASES = {
    "movimentacao": "soma_movimentacao_quantidade",
    "movimentacao_total": "soma_movimentacao_quantidade",
    "soma_movimentacao": "soma_movimentacao_quantidade",
}
_DYNAMIC_METRIC_ALIASES = {
    "quantidade",
    "quantidade_total",
    "soma_quantidade",
    "total_quantidade",
    "valor",
    "soma_valor",
    "total_valor",
}
_MOVEMENT_FILTER_FIELDS = (
    "data_movimento_inicio",
    "data_movimento_fim",
    "tipo_movimento",
    "unidade_gestora",
    "almoxarifado",
    "localizacao",
    "classificacao",
)
_MOVEMENT_METRICS = {
    "contagem",
    "soma_entrada_quantidade",
    "soma_entrada_valor",
    "soma_movimentacao_quantidade",
    "soma_movimentacao_valor",
    "soma_saida_quantidade",
    "soma_saida_valor",
}


class AgregarEstoquesFiltroSchema(EstoqueFiltroSchema):
    """Filtros publicos aceitos pela tool deste dominio."""

    data_movimento_inicio: date | None = None
    data_movimento_fim: date | None = None
    tipo_movimento: str | None = None
    unidade_gestora: str | None = None
    almoxarifado: str | None = None
    localizacao: str | None = None
    classificacao: str | None = None

    @field_validator(
        "tipo_movimento",
        "unidade_gestora",
        "almoxarifado",
        "localizacao",
        "classificacao",
        mode="before",
    )
    @classmethod
    def _normalize_movement_text(cls, value: Any) -> str | None:
        return clean_text(value)

    @field_validator("data_movimento_inicio", "data_movimento_fim", mode="before")
    @classmethod
    def _normalize_movement_dates(cls, value: Any) -> date | None:
        return parse_date(value)

    @model_validator(mode="after")
    def _validate_movement_dates(self) -> "AgregarEstoquesFiltroSchema":
        if self.data_movimento_inicio and self.data_movimento_fim:
            validate_date_period(self.data_movimento_inicio, self.data_movimento_fim)
        return self

    def has_movement_filters(self) -> bool:
        return any(getattr(self, field_name) is not None for field_name in _MOVEMENT_FILTER_FIELDS)


class AgregarEstoquesParams(SqlToolBaseSchema):
    """Parametros validados da chamada da tool."""

    filtros: AgregarEstoquesFiltroSchema = Field(default_factory=AgregarEstoquesFiltroSchema)
    agrupar_por: str | None = None
    metrica: str = "soma_saldo_valor"
    ordenar_por: str = "metrica"
    ordem: str = "desc"
    limite: int = 10

    @field_validator("filtros", mode="before")
    @classmethod
    def _normalize_filtros(cls, value: Any) -> AgregarEstoquesFiltroSchema:
        return normalize_model_input(
            value,
            schema_type=AgregarEstoquesFiltroSchema,
            field_name="filtros",
        )

    @field_validator("agrupar_por", mode="before")
    @classmethod
    def _normalize_agrupar_por(cls, value: Any) -> str | None:
        normalized = clean_text(value)
        if normalized is None:
            return None
        normalized = ESTOQUES_GROUP_FIELD_ALIASES.get(normalized, normalized)
        if normalized not in ALLOWED_ESTOQUES_GROUP_FIELDS:
            raise ValueError(f"agrupar_por nao suportado: {normalized}")
        return normalized

    @field_validator("metrica", mode="before")
    @classmethod
    def _normalize_metrica(cls, value: Any) -> str:
        normalized = clean_text(value) or "soma_saldo_valor"
        normalized = ESTOQUES_METRIC_ALIASES.get(normalized, normalized)
        if normalized not in ALLOWED_ESTOQUES_METRICS and normalized not in _DYNAMIC_METRIC_ALIASES:
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
    def _validate_aggregation(self) -> "AgregarEstoquesParams":
        if self.metrica in {
            "quantidade",
            "quantidade_total",
            "soma_quantidade",
            "total_quantidade",
        }:
            self.metrica = (
                "soma_movimentacao_quantidade" if self.filtros.has_movement_filters() else "soma_saldo_quantidade"
            )
        elif self.metrica in {"valor", "soma_valor", "total_valor"}:
            self.metrica = "soma_movimentacao_valor" if self.filtros.has_movement_filters() else "soma_saldo_valor"
        if self.ordenar_por not in {"metrica", self.agrupar_por}:
            raise ValueError("ordenar_por deve ser 'metrica' ou igual a agrupar_por")
        if self.agrupar_por is None and self.ordenar_por != "metrica":
            raise ValueError("ordenar_por deve ser 'metrica' quando agrupar_por nao for informado")
        if self.filtros.has_movement_filters() and self.metrica not in _MOVEMENT_METRICS:
            raise ValueError("filtros de movimentacao exigem metricas de entrada, saida, contagem ou movimentacao")
        return self


class AgregarEstoquesMetadata(SqlToolBaseSchema):
    """Metadados ecoados na resposta (filtros, ordenacao, paginacao)."""

    filtros_aplicados: dict[str, Any] = Field(default_factory=dict)
    agrupar_por: str | None = None
    metrica: str
    ordenar_por: str
    ordem: str
    limite: int


class AgregarEstoquesResponse(SqlToolBaseSchema):
    """Formato da resposta publica da tool."""

    total_grupos: int
    resultados: list[dict[str, Any]] = Field(default_factory=list)
    metadata: AgregarEstoquesMetadata
    valor_total: float | int | None = None
    mensagem: str | None = None
    sugestao: str | None = None
