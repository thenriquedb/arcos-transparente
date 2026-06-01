"""Schemas e helpers compartilhados de filtros de receitas."""

from __future__ import annotations

from decimal import Decimal
from typing import Any

from pydantic import Field, field_validator, model_validator

from agents.tools.sql_tools.shared.normalization import normalize_selected_fields
from shared.utils.validation import clean_text, parse_decimal, parse_month

from .base import ReceitasToolBaseSchema


ALLOWED_RECEITA_FIELDS = (
    "id",
    "tipo_de_dado",
    "ano",
    "mes",
    "mes_num",
    "data",
    "unidade_responsavel",
    "categoria_codigo",
    "categoria",
    "tipo",
    "tributo",
    "origem_do_recurso",
    "valor_previsto",
    "valor_recebido",
    "valor_previsto_bruto",
    "valor_recebido_bruto",
    "descontos_previstos",
    "descontos_realizados",
    "valor_lancado",
    "valor_em_divida_ativa",
    "valor_em_cobranca_judicial",
)

ALLOWED_RECEITA_SORT_FIELDS = (
    "ano",
    "mes_num",
    "data",
    "unidade_responsavel",
    "categoria",
    "tipo",
    "tributo",
    "valor_previsto",
    "valor_recebido",
    "valor_lancado",
    "valor_em_divida_ativa",
    "valor_em_cobranca_judicial",
)

ALLOWED_GROUP_FIELDS = (
    "mes",
    "unidade_responsavel",
    "categoria",
    "tipo",
    "tributo",
    "origem_do_recurso",
)

ALLOWED_METRICS = (
    "contagem",
    "soma_valor_previsto",
    "soma_valor_recebido",
    "soma_valor_lancado",
    "soma_valor_em_divida_ativa",
    "soma_valor_em_cobranca_judicial",
)

ALLOWED_ORDER_VALUES = ("asc", "desc")
ALLOWED_RECEITA_TYPES = ("arrecadacao", "lancamento")


class ReceitaFiltroSchema(ReceitasToolBaseSchema):
    tipo_de_dado: str = "arrecadacao"
    ano: int | None = None
    mes: int | None = None
    mes_inicio: int | None = None
    mes_fim: int | None = None
    unidade_responsavel: str | None = None
    categoria: str | None = None
    categoria_codigo: str | None = None
    tipo: str | None = None
    tributo: str | None = None
    origem_do_recurso: str | None = None
    tema: str | None = None
    valor_min: Decimal | None = None
    valor_max: Decimal | None = None

    @field_validator(
        "tipo_de_dado",
        "unidade_responsavel",
        "categoria",
        "categoria_codigo",
        "tipo",
        "tributo",
        "origem_do_recurso",
        "tema",
        mode="before",
    )
    @classmethod
    def _normalize_text_filters(cls, value: Any) -> str | None:
        return clean_text(value)

    @field_validator("tipo_de_dado")
    @classmethod
    def _validate_tipo_de_dado(cls, value: str) -> str:
        normalized = value.lower()
        if normalized not in ALLOWED_RECEITA_TYPES:
            raise ValueError(f"tipo_de_dado nao suportado: {normalized}")
        return normalized

    @field_validator("ano", mode="before")
    @classmethod
    def _normalize_ano(cls, value: Any) -> int | None:
        if value is None:
            return None
        return int(value)

    @field_validator("mes", "mes_inicio", "mes_fim", mode="before")
    @classmethod
    def _normalize_mes(cls, value: Any) -> int | None:
        month = parse_month(value)
        if month is not None and not 1 <= month <= 12:
            raise ValueError("mes deve estar entre 1 e 12")
        return month

    @field_validator("valor_min", "valor_max", mode="before")
    @classmethod
    def _normalize_decimal(cls, value: Any) -> Decimal | None:
        return parse_decimal(value)

    @model_validator(mode="after")
    def _validate_ranges(self) -> "ReceitaFiltroSchema":
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
            self.valor_min is not None
            and self.valor_max is not None
            and self.valor_min > self.valor_max
        ):
            raise ValueError("valor_min deve ser menor ou igual a valor_max")
        return self


class CamposReceitaSchema(ReceitasToolBaseSchema):
    campos: list[str] = Field(default_factory=list)

    @field_validator("campos", mode="before")
    @classmethod
    def _normalize_campos(cls, value: Any) -> list[str]:
        return normalize_selected_fields(
            value,
            allowed_fields=ALLOWED_RECEITA_FIELDS,
            require_list=True,
            error_style="campo",
        )
