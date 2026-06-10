"""Schemas e helpers compartilhados de filtros do dominio de contratos."""

from __future__ import annotations

from datetime import date
from decimal import Decimal
from typing import Any

from pydantic import Field, field_validator, model_validator

from agents.tools.sql_tools.shared.base import SqlToolBaseSchema
from agents.tools.sql_tools.shared.normalization import normalize_selected_fields
from shared.utils.validation import (
    clean_text,
    parse_date,
    parse_decimal,
    validate_date_period,
)

ALLOWED_CONTRACT_FIELDS = (
    "id",
    "numero",
    "fornecedor",
    "documento_fornecedor",
    "valor",
    "data_inicio",
    "data_fim",
    "categoria",
    "secretaria",
    "descricao",
    "classificacao_da_despesa",
)

ALLOWED_CONTRACT_SORT_FIELDS = (
    "numero",
    "fornecedor",
    "valor",
    "data_inicio",
    "data_fim",
    "categoria",
    "secretaria",
)

ALLOWED_GROUP_FIELDS = ("secretaria", "categoria", "fornecedor", "ano_inicio")
ALLOWED_METRICS = ("contagem", "soma_valor", "media_valor")
ALLOWED_ORDER_VALUES = ("asc", "desc")
TEXT_FALLBACK_TARGETS = {
    "fornecedor": ("descricao", "categoria", "secretaria"),
    "descricao": ("fornecedor", "categoria", "secretaria"),
    "categoria": ("descricao", "fornecedor", "secretaria"),
    "secretaria": ("descricao", "categoria", "fornecedor"),
}


class ContratosFiltroSchema(SqlToolBaseSchema):
    """Filtros publicos aceitos pela tool deste dominio."""

    numero: str | None = None
    fornecedor: str | None = None
    documento_fornecedor: str | None = None
    categoria: str | None = None
    secretaria: str | None = None
    descricao: str | None = None
    data_inicio: date | None = None
    data_inicio_inicio: date | None = None
    data_inicio_fim: date | None = None
    data_fim: date | None = None
    data_fim_inicio: date | None = None
    data_fim_fim: date | None = None
    vigente_em: date | None = None
    valor_min: Decimal | None = None
    valor_max: Decimal | None = None

    @field_validator(
        "numero",
        "fornecedor",
        "documento_fornecedor",
        "categoria",
        "secretaria",
        "descricao",
        mode="before",
    )
    @classmethod
    def _normalize_text_filters(cls, value: Any) -> str | None:
        return clean_text(value)

    @field_validator(
        "data_inicio",
        "data_inicio_inicio",
        "data_inicio_fim",
        "data_fim",
        "data_fim_inicio",
        "data_fim_fim",
        "vigente_em",
        mode="before",
    )
    @classmethod
    def _normalize_date_filters(cls, value: Any) -> date | None:
        return parse_date(value)

    @field_validator("valor_min", "valor_max", mode="before")
    @classmethod
    def _normalize_value_filters(cls, value: Any) -> Decimal | None:
        return parse_decimal(value)

    @model_validator(mode="after")
    def _validate_ranges(self) -> "ContratosFiltroSchema":
        if self.data_inicio is not None and (self.data_inicio_inicio is not None or self.data_inicio_fim is not None):
            raise ValueError("data_inicio nao pode ser usada junto com data_inicio_inicio ou data_inicio_fim")

        if self.data_inicio_inicio is not None or self.data_inicio_fim is not None:
            if self.data_inicio_inicio is None or self.data_inicio_fim is None:
                raise ValueError("data_inicio_inicio e data_inicio_fim devem ser informadas juntas")
            validate_date_period(self.data_inicio_inicio, self.data_inicio_fim)

        if self.data_fim is not None and (self.data_fim_inicio is not None or self.data_fim_fim is not None):
            raise ValueError("data_fim nao pode ser usada junto com data_fim_inicio ou data_fim_fim")

        if self.data_fim_inicio is not None or self.data_fim_fim is not None:
            if self.data_fim_inicio is None or self.data_fim_fim is None:
                raise ValueError("data_fim_inicio e data_fim_fim devem ser informadas juntas")
            validate_date_period(self.data_fim_inicio, self.data_fim_fim)

        if self.valor_min is not None and self.valor_max is not None and self.valor_min > self.valor_max:
            raise ValueError("valor_min deve ser menor ou igual a valor_max")
        return self

    def build_text_fallback_candidates(
        self,
    ) -> list[tuple[str, "ContratosFiltroSchema"]]:
        """
        Monta filtros alternativos para um unico termo textual sem match.

        A ideia aqui e ser conservador: so tentamos fallback quando ha um unico
        filtro textual principal ativo. Isso evita combinar varios campos
        alternativos ao mesmo tempo e devolver resultados confusos.
        """

        active_fields = [field_name for field_name in TEXT_FALLBACK_TARGETS if getattr(self, field_name) is not None]
        if len(active_fields) != 1:
            return []

        source_field = active_fields[0]
        source_value = getattr(self, source_field)
        if source_value is None:
            return []

        candidates: list[tuple[str, ContratosFiltroSchema]] = []
        for target_field in TEXT_FALLBACK_TARGETS[source_field]:
            candidates.append(
                (
                    target_field,
                    self.model_copy(
                        update={
                            source_field: None,
                            target_field: source_value,
                        }
                    ),
                )
            )
        return candidates


class CamposContratoSchema(SqlToolBaseSchema):
    campos: list[str] = Field(default_factory=list)

    @field_validator("campos", mode="before")
    @classmethod
    def _normalize_campos(cls, value: Any) -> list[str]:
        return normalize_selected_fields(
            value,
            allowed_fields=ALLOWED_CONTRACT_FIELDS,
            require_list=True,
            error_style="campo",
        )
