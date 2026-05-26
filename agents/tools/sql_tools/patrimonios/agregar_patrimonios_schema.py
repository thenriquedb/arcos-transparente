"""Schemas da tool publica agregar_patrimonios."""

from __future__ import annotations

from typing import Any

from pydantic import Field, field_validator, model_validator

from shared.utils.validation import clean_text, normalize_limit

from .consultar_patrimonios_schema import (
    ALLOWED_ORDER_VALUES,
    PatrimonioFiltroSchema,
    PatrimonioToolBaseSchema,
)


ALLOWED_PATRIMONIO_GROUP_FIELDS = {
    "unidade_responsavel",
    "localizacao",
    "status",
    "situacao",
    "tipo_ingresso",
    "classificacao",
}
ALLOWED_PATRIMONIO_METRICS = {
    "contagem",
    "soma_valor_atualizado",
    "soma_valor_ingresso",
}


class AgregarPatrimoniosParams(PatrimonioToolBaseSchema):
    filtros: PatrimonioFiltroSchema = Field(default_factory=PatrimonioFiltroSchema)
    agrupar_por: str | None = None
    metrica: str = "contagem"
    ordenar_por: str = "metrica"
    ordem: str = "desc"
    limite: int = 10

    @field_validator("filtros", mode="before")
    @classmethod
    def _normalize_filtros(cls, value: Any) -> PatrimonioFiltroSchema:
        if value is None:
            return PatrimonioFiltroSchema()
        if isinstance(value, PatrimonioFiltroSchema):
            return value
        if not isinstance(value, dict):
            raise ValueError("filtros deve ser um objeto")
        return PatrimonioFiltroSchema.model_validate(value)

    @field_validator("agrupar_por", mode="before")
    @classmethod
    def _normalize_agrupar_por(cls, value: Any) -> str | None:
        normalized = clean_text(value)
        if normalized is None:
            return None
        if normalized not in ALLOWED_PATRIMONIO_GROUP_FIELDS:
            raise ValueError(f"agrupar_por nao suportado: {normalized}")
        return normalized

    @field_validator("metrica", mode="before")
    @classmethod
    def _normalize_metrica(cls, value: Any) -> str:
        normalized = clean_text(value) or "contagem"
        if normalized not in ALLOWED_PATRIMONIO_METRICS:
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
    def _validate_aggregation(self) -> "AgregarPatrimoniosParams":
        if self.ordenar_por not in {"metrica", self.agrupar_por}:
            raise ValueError("ordenar_por deve ser 'metrica' ou igual a agrupar_por")
        if self.agrupar_por is None and self.ordenar_por != "metrica":
            raise ValueError(
                "ordenar_por deve ser 'metrica' quando agrupar_por nao for informado"
            )
        return self


class AgregarPatrimoniosMetadata(PatrimonioToolBaseSchema):
    filtros_aplicados: dict[str, Any] = Field(default_factory=dict)
    agrupar_por: str | None = None
    metrica: str
    ordenar_por: str
    ordem: str
    limite: int


class AgregarPatrimoniosResponse(PatrimonioToolBaseSchema):
    total_grupos: int
    resultados: list[dict[str, Any]] = Field(default_factory=list)
    metadata: AgregarPatrimoniosMetadata
    valor_total: float | int | None = None
    mensagem: str | None = None
    sugestao: str | None = None
