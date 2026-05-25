"""Schemas e helpers compartilhados de filtros de planejamento."""

from __future__ import annotations

from decimal import Decimal
from typing import Any

from pydantic import Field, field_validator, model_validator

from shared.utils.text import normalize_search_text
from shared.utils.validation import clean_text, parse_decimal

from .base import PlanejamentoToolBaseSchema


ALLOWED_PLANNING_FIELDS = (
    "id",
    "origem",
    "ano",
    "mes",
    "mes_num",
    "unidade_gestora",
    "orgao",
    "unidade",
    "area",
    "subarea",
    "programa",
    "tipo_acao",
    "acao",
    "fonte_recurso",
    "esfera",
    "categoria_de_gasto",
    "grupo_de_gasto",
    "orcamento_inicial",
    "reforcos_no_orcamento",
    "orcamento_atualizado",
    "valor_comprometido",
    "valor_confirmado",
    "valor_pago",
    "valor_cancelado",
)

ALLOWED_PLANNING_SORT_FIELDS = (
    "ano",
    "mes_num",
    "area",
    "subarea",
    "programa",
    "acao",
    "grupo_de_gasto",
    "orcamento_inicial",
    "orcamento_atualizado",
    "valor_comprometido",
    "valor_confirmado",
    "valor_pago",
    "valor_cancelado",
)

ALLOWED_GROUP_FIELDS = (
    "mes",
    "area",
    "subarea",
    "programa",
    "acao",
    "grupo_de_gasto",
    "categoria_de_gasto",
    "fonte_recurso",
)

ALLOWED_METRICS = (
    "contagem",
    "soma_orcamento_inicial",
    "soma_orcamento_atualizado",
    "soma_valor_comprometido",
    "soma_valor_confirmado",
    "soma_valor_pago",
    "soma_valor_cancelado",
)

ALLOWED_ORDER_VALUES = ("asc", "desc")

MESES_NUMERO = {
    "janeiro": 1,
    "fevereiro": 2,
    "marco": 3,
    "abril": 4,
    "maio": 5,
    "junho": 6,
    "julho": 7,
    "agosto": 8,
    "setembro": 9,
    "outubro": 10,
    "novembro": 11,
    "dezembro": 12,
}


def parse_mes(value: Any) -> int | None:
    if value is None:
        return None
    if isinstance(value, int):
        return value

    text = clean_text(value)
    if text is None:
        return None
    if text.isdigit():
        return int(text)
    return MESES_NUMERO.get(normalize_search_text(text))


class PlanejamentoFiltroSchema(PlanejamentoToolBaseSchema):
    origem: str | None = "saude"
    ano: int | None = None
    mes: int | None = None
    mes_inicio: int | None = None
    mes_fim: int | None = None
    entidade: str | None = None
    area: str | None = None
    subarea: str | None = None
    programa: str | None = None
    acao: str | None = None
    grupo_de_gasto: str | None = None
    categoria_de_gasto: str | None = None
    fonte_recurso: str | None = None
    valor_pago_min: Decimal | None = None
    valor_pago_max: Decimal | None = None

    @field_validator(
        "origem",
        "entidade",
        "area",
        "subarea",
        "programa",
        "acao",
        "grupo_de_gasto",
        "categoria_de_gasto",
        "fonte_recurso",
        mode="before",
    )
    @classmethod
    def _normalize_text_filters(cls, value: Any) -> str | None:
        return clean_text(value)

    @field_validator("ano", mode="before")
    @classmethod
    def _normalize_ano(cls, value: Any) -> int | None:
        if value is None:
            return None
        return int(value)

    @field_validator("mes", "mes_inicio", "mes_fim", mode="before")
    @classmethod
    def _normalize_mes(cls, value: Any) -> int | None:
        month = parse_mes(value)
        if month is not None and not 1 <= month <= 12:
            raise ValueError("mes deve estar entre 1 e 12")
        return month

    @field_validator("valor_pago_min", "valor_pago_max", mode="before")
    @classmethod
    def _normalize_value_filters(cls, value: Any) -> Decimal | None:
        return parse_decimal(value)

    @model_validator(mode="after")
    def _validate_ranges(self) -> "PlanejamentoFiltroSchema":
        if self.mes is not None and (
            self.mes_inicio is not None or self.mes_fim is not None
        ):
            raise ValueError("mes nao pode ser usado junto com mes_inicio/mes_fim")
        if self.mes_inicio is not None or self.mes_fim is not None:
            if self.mes_inicio is None or self.mes_fim is None:
                raise ValueError("mes_inicio e mes_fim devem ser informados juntos")
            if self.mes_inicio > self.mes_fim:
                raise ValueError("mes_inicio deve ser menor ou igual a mes_fim")
        if (
            self.valor_pago_min is not None
            and self.valor_pago_max is not None
            and self.valor_pago_min > self.valor_pago_max
        ):
            raise ValueError("valor_pago_min deve ser menor ou igual a valor_pago_max")
        return self

    def to_metadata_dict(self) -> dict[str, Any]:
        return self.model_dump(mode="json", exclude_none=True)


class CamposPlanejamentoSchema(PlanejamentoToolBaseSchema):
    campos: list[str] = Field(default_factory=list)

    @field_validator("campos", mode="before")
    @classmethod
    def _normalize_campos(cls, value: Any) -> list[str]:
        if value is None:
            return []
        if not isinstance(value, list):
            raise ValueError("campos deve ser uma lista")

        normalized_fields: list[str] = []
        for item in value:
            field_name = clean_text(item)
            if field_name is None:
                continue
            if field_name not in ALLOWED_PLANNING_FIELDS:
                raise ValueError(f"campo nao suportado: {field_name}")
            normalized_fields.append(field_name)
        return normalized_fields
