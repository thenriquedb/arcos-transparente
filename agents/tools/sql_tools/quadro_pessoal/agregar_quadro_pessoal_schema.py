"""Schemas da tool publica agregar_quadro_pessoal."""

from __future__ import annotations

from typing import Any

from pydantic import Field, field_validator, model_validator

from shared.utils.validation import clean_text, normalize_limit

from .consultar_quadro_pessoal_schema import (
    ALLOWED_ORDER_VALUES,
    QuadroPessoalFiltroSchema,
    QuadroPessoalToolBaseSchema,
)


ALLOWED_QUADRO_GROUP_FIELDS = {"origem", "regime", "mes"}
ALLOWED_QUADRO_METRICS = {
    "contagem",
    "soma_vagas_criadas",
    "soma_vagas_preenchidas",
    "saldo_vagas",
}


class AgregarQuadroPessoalParams(QuadroPessoalToolBaseSchema):
    filtros: QuadroPessoalFiltroSchema = Field(
        default_factory=QuadroPessoalFiltroSchema
    )
    agrupar_por: str | None = None
    metrica: str = "soma_vagas_preenchidas"
    ordenar_por: str = "metrica"
    ordem: str = "desc"
    limite: int = 10

    @field_validator("filtros", mode="before")
    @classmethod
    def _normalize_filtros(cls, value: Any) -> QuadroPessoalFiltroSchema:
        if value is None:
            return QuadroPessoalFiltroSchema()
        if isinstance(value, QuadroPessoalFiltroSchema):
            return value
        if not isinstance(value, dict):
            raise ValueError("filtros deve ser um objeto")
        return QuadroPessoalFiltroSchema.model_validate(value)

    @field_validator("agrupar_por", mode="before")
    @classmethod
    def _normalize_agrupar_por(cls, value: Any) -> str | None:
        normalized = clean_text(value)
        if normalized is None:
            return None
        if normalized not in ALLOWED_QUADRO_GROUP_FIELDS:
            raise ValueError(f"agrupar_por nao suportado: {normalized}")
        return normalized

    @field_validator("metrica", mode="before")
    @classmethod
    def _normalize_metrica(cls, value: Any) -> str:
        normalized = clean_text(value) or "soma_vagas_preenchidas"
        if normalized not in ALLOWED_QUADRO_METRICS:
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
    def _validate_aggregation(self) -> "AgregarQuadroPessoalParams":
        if self.ordenar_por not in {"metrica", self.agrupar_por}:
            raise ValueError("ordenar_por deve ser 'metrica' ou igual a agrupar_por")
        if self.agrupar_por is None and self.ordenar_por != "metrica":
            raise ValueError(
                "ordenar_por deve ser 'metrica' quando agrupar_por nao for informado"
            )
        return self


class AgregarQuadroPessoalMetadata(QuadroPessoalToolBaseSchema):
    filtros_aplicados: dict[str, Any] = Field(default_factory=dict)
    agrupar_por: str | None = None
    metrica: str
    ordenar_por: str
    ordem: str
    limite: int


class AgregarQuadroPessoalResponse(QuadroPessoalToolBaseSchema):
    total_grupos: int
    resultados: list[dict[str, Any]] = Field(default_factory=list)
    metadata: AgregarQuadroPessoalMetadata
    valor_total: int | None = None
    mensagem: str | None = None
    sugestao: str | None = None
