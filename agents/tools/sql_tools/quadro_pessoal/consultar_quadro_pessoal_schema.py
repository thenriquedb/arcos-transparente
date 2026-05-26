"""Schemas da tool publica consultar_quadro_pessoal."""

from __future__ import annotations

from typing import Any

from pydantic import BaseModel, ConfigDict, Field, field_validator

from shared.utils.validation import clean_text, normalize_limit


ALLOWED_QUADRO_FIELDS = {
    "origem",
    "mes_de_referencia",
    "regime",
    "vagas_criadas",
    "vagas_preenchidas",
    "saldo_vagas",
}
ALLOWED_QUADRO_SORT_FIELDS = {
    "mes_de_referencia",
    "origem",
    "regime",
    "vagas_criadas",
    "vagas_preenchidas",
    "saldo_vagas",
}
ALLOWED_ORDER_VALUES = {"asc", "desc"}


class QuadroPessoalToolBaseSchema(BaseModel):
    model_config = ConfigDict(extra="ignore")


class QuadroPessoalFiltroSchema(QuadroPessoalToolBaseSchema):
    origem: str | None = None
    ano: int | None = None
    mes: int | None = None
    regime: str | None = None

    @field_validator("origem", "regime", mode="before")
    @classmethod
    def _normalize_text(cls, value: Any) -> str | None:
        return clean_text(value)

    @field_validator("ano", "mes", mode="before")
    @classmethod
    def _normalize_int(cls, value: Any) -> int | None:
        if value is None:
            return None
        text = clean_text(value)
        return int(text) if text is not None else None

    def to_metadata_dict(self) -> dict[str, Any]:
        return self.model_dump(mode="json", exclude_none=True)


class ConsultarQuadroPessoalParams(QuadroPessoalToolBaseSchema):
    filtros: QuadroPessoalFiltroSchema = Field(
        default_factory=QuadroPessoalFiltroSchema
    )
    ordenar_por: str = "mes_de_referencia"
    ordem: str = "asc"
    limite: int = 10
    offset: int = 0
    campos: list[str] = Field(default_factory=list)

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

    @field_validator("ordenar_por", mode="before")
    @classmethod
    def _normalize_ordenar_por(cls, value: Any) -> str:
        normalized = clean_text(value) or "mes_de_referencia"
        if normalized not in ALLOWED_QUADRO_SORT_FIELDS:
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
        if value is None:
            return []
        campos = [clean_text(item) for item in value]
        invalidos = [item for item in campos if item not in ALLOWED_QUADRO_FIELDS]
        if invalidos:
            raise ValueError(f"campos nao suportados: {invalidos}")
        return [item for item in campos if item is not None]


class ConsultarQuadroPessoalMetadata(QuadroPessoalToolBaseSchema):
    filtros_aplicados: dict[str, Any] = Field(default_factory=dict)
    ordenar_por: str
    ordem: str
    limite: int
    offset: int
    campos: list[str] = Field(default_factory=lambda: list(ALLOWED_QUADRO_FIELDS))


class ConsultarQuadroPessoalResponse(QuadroPessoalToolBaseSchema):
    total: int
    resultados: list[dict[str, Any]] = Field(default_factory=list)
    metadata: ConsultarQuadroPessoalMetadata
    mensagem: str | None = None
    sugestao: str | None = None
