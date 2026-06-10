"""Schemas Pydantic para ingestao de contratos."""

from __future__ import annotations

from datetime import date
from decimal import Decimal
from typing import Any

from pydantic import (
    BaseModel,
    ConfigDict,
    Field,
    field_validator,
    model_validator,
)

from ingestion.schemas.shared import normalize_validated_list
from shared.utils.validation import (
    clean_text,
    parse_date,
    parse_decimal,
    parse_int,
    parse_number,
)


class _ContratosBaseSchema(BaseModel):
    model_config = ConfigDict(extra="ignore")


class ContratoDespesaOrcamentariaInSchema(_ContratosBaseSchema):
    unidade_gestora: str | None = None
    exercicio: int | None = None
    orgao: str | None = None
    unidade: str | None = None
    departamento: str | None = None
    fonte_recurso: str | None = None
    natureza_despesa_rubrica: str | None = None
    descricao_despesa: str | None = None
    valor_despesa: Decimal | None = None

    @field_validator(
        "unidade_gestora",
        "orgao",
        "unidade",
        "departamento",
        "fonte_recurso",
        "natureza_despesa_rubrica",
        "descricao_despesa",
        mode="before",
    )
    @classmethod
    def _normalize_text_fields(cls, value: Any) -> str | None:
        return clean_text(value)

    @field_validator("exercicio", mode="before")
    @classmethod
    def _normalize_exercicio(cls, value: Any) -> int | None:
        if value is None:
            return None
        try:
            return parse_int(value)
        except ValueError as exc:
            raise ValueError("exercicio invalido") from exc

    @field_validator("valor_despesa", mode="before")
    @classmethod
    def _normalize_valor_despesa(cls, value: Any) -> Decimal | None:
        return parse_decimal(value)


class ContratoItemAdquiridoInSchema(_ContratosBaseSchema):
    unidade_gestora: str | None = None
    numero_lote: str | None = None
    numero_item: str | None = None
    identificacao: str | None = None
    quantidade: Decimal | None = None
    valor_unitario: Decimal | None = None
    valor_total: Decimal | None = None

    @field_validator(
        "unidade_gestora",
        "numero_lote",
        "numero_item",
        "identificacao",
        mode="before",
    )
    @classmethod
    def _normalize_text_fields(cls, value: Any) -> str | None:
        return clean_text(value)

    @field_validator("quantidade", mode="before")
    @classmethod
    def _normalize_quantidade(cls, value: Any) -> Decimal | None:
        return parse_number(value)

    @field_validator("valor_unitario", "valor_total", mode="before")
    @classmethod
    def _normalize_monetary_fields(cls, value: Any) -> Decimal | None:
        return parse_decimal(value)


class ContratoInSchema(_ContratosBaseSchema):
    numero: str
    numero_licitatorio: str | None = None
    numero_instrumento: str | None = None
    tipo_instrumento_contratual: str | None = None
    fornecedor: str
    cnpj: str
    valor: Decimal
    data_inicio: date
    data_fim: date | None = None
    categoria: str | None = "nao_informado"
    secretaria: str | None = "nao_informado"
    possui_aditivo: str | None = None
    descricao: str | None = None
    descricao_despesa: str | None = None
    xml_original: str | None = None
    despesas_orcamentarias: list[ContratoDespesaOrcamentariaInSchema] = Field(default_factory=list)
    itens_adquiridos: list[ContratoItemAdquiridoInSchema] = Field(default_factory=list)

    @field_validator(
        "numero",
        "numero_licitatorio",
        "numero_instrumento",
        "tipo_instrumento_contratual",
        "fornecedor",
        "cnpj",
        "categoria",
        "secretaria",
        "possui_aditivo",
        "descricao",
        "descricao_despesa",
        "xml_original",
        mode="before",
    )
    @classmethod
    def _normalize_text_fields(cls, value: Any) -> str | None:
        return clean_text(value)

    @field_validator("valor", mode="before")
    @classmethod
    def _normalize_valor(cls, value: Any) -> Decimal | None:
        return parse_decimal(value)

    @field_validator("data_inicio", "data_fim", mode="before")
    @classmethod
    def _normalize_datas(cls, value: Any) -> date | None:
        return parse_date(value)

    @field_validator("despesas_orcamentarias", mode="before")
    @classmethod
    def _normalize_despesas(
        cls,
        value: Any,
    ) -> list[ContratoDespesaOrcamentariaInSchema]:
        return normalize_validated_list(
            value,
            schema_type=ContratoDespesaOrcamentariaInSchema,
            field_name="despesas_orcamentarias",
        )

    @field_validator("itens_adquiridos", mode="before")
    @classmethod
    def _normalize_itens(
        cls,
        value: Any,
    ) -> list[ContratoItemAdquiridoInSchema]:
        return normalize_validated_list(
            value,
            schema_type=ContratoItemAdquiridoInSchema,
            field_name="itens_adquiridos",
        )

    @model_validator(mode="after")
    def _apply_defaults_and_validate(self) -> "ContratoInSchema":
        if not self.numero:
            raise ValueError("numero e obrigatorio")
        if not self.fornecedor:
            raise ValueError("fornecedor e obrigatorio")
        if not self.cnpj:
            raise ValueError("cnpj e obrigatorio")
        if self.valor is None:
            raise ValueError("valor e obrigatorio")
        if self.data_inicio is None:
            raise ValueError("data_inicio e obrigatoria")

        self.categoria = self.categoria or "nao_informado"
        self.secretaria = self.secretaria or "nao_informado"
        return self
