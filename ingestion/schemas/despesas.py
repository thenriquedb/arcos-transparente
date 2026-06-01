"""Schemas Pydantic para ingestao de documentos de despesa."""

from __future__ import annotations

from datetime import date
from decimal import Decimal
from typing import Any

from pydantic import BaseModel, ConfigDict, field_validator

from shared.utils.validation import (
    clean_text,
    parse_date,
    parse_decimal,
    parse_int,
    parse_number,
)


class DespesaDocumentoItemInSchema(BaseModel):
    """Item declarado dentro de um documento de despesa."""

    model_config = ConfigDict(extra="ignore")

    ordem: int
    numero_item: str | None = None
    descricao_item: str | None = None
    quantidade: Decimal | None = None
    valor_unitario: Decimal | None = None
    valor_total: Decimal | None = None

    @field_validator("ordem", mode="before")
    @classmethod
    def _normalize_ordem(cls, value: Any) -> int:
        parsed = parse_int(value)
        if parsed is None:
            raise ValueError("ordem obrigatoria")
        return parsed

    @field_validator("numero_item", "descricao_item", mode="before")
    @classmethod
    def _normalize_text_fields(cls, value: Any) -> str | None:
        return clean_text(value)

    @field_validator("quantidade", mode="before")
    @classmethod
    def _normalize_quantidade(cls, value: Any) -> Decimal | None:
        return parse_number(value)

    @field_validator("valor_unitario", "valor_total", mode="before")
    @classmethod
    def _normalize_values(cls, value: Any) -> Decimal | None:
        return parse_decimal(value)


class DespesaDocumentoComprobatorioInSchema(BaseModel):
    """Documento comprobatorio vinculado ao documento de despesa."""

    model_config = ConfigDict(extra="ignore")

    ordem: int
    data_liquidacao: date | None = None
    codigo_tipo_documento: str | None = None
    descricao_tipo_documento: str | None = None
    numero_documento: str | None = None
    serie_modelo_nota_fiscal: str | None = None
    descricao_serie: str | None = None
    chave_acesso: str | None = None
    data_emissao_documento: date | None = None
    valor_documento: Decimal | None = None
    numero_empenho: str | None = None
    codigo_unidade_gestora: str | None = None
    numero_sequencia: str | None = None

    @field_validator("ordem", mode="before")
    @classmethod
    def _normalize_ordem(cls, value: Any) -> int:
        parsed = parse_int(value)
        if parsed is None:
            raise ValueError("ordem obrigatoria")
        return parsed

    @field_validator(
        "codigo_tipo_documento",
        "descricao_tipo_documento",
        "numero_documento",
        "serie_modelo_nota_fiscal",
        "descricao_serie",
        "chave_acesso",
        "numero_empenho",
        "codigo_unidade_gestora",
        "numero_sequencia",
        mode="before",
    )
    @classmethod
    def _normalize_text_fields(cls, value: Any) -> str | None:
        return clean_text(value)

    @field_validator("data_liquidacao", "data_emissao_documento", mode="before")
    @classmethod
    def _normalize_dates(cls, value: Any) -> date | None:
        return parse_date(value)

    @field_validator("valor_documento", mode="before")
    @classmethod
    def _normalize_values(cls, value: Any) -> Decimal | None:
        return parse_decimal(value)


class DespesaDocumentoInSchema(BaseModel):
    """Documento principal de despesa importado de empenhos, restos ou extras."""

    model_config = ConfigDict(extra="ignore")

    tipo_origem: str
    arquivo_origem: str
    sequencia_origem: int
    origem: str
    exercicio: int
    unidade_gestora: str
    orgao: str | None = None
    unidade: str | None = None
    departamento: str | None = None
    funcao: str | None = None
    subfuncao: str | None = None
    programa: str | None = None
    tipo_acao: str | None = None
    descricao_acao: str | None = None
    fonte_recurso_identificacao: str | None = None
    fonte_recurso_descricao: str | None = None
    esfera_administrativa: str | None = None
    modalidade_aplicacao_identificacao: str | None = None
    modalidade_aplicacao_descricao: str | None = None
    categoria_economica_identificacao: str | None = None
    categoria_economica_descricao: str | None = None
    grupo_despesa_identificacao: str | None = None
    grupo_despesa_descricao: str | None = None
    elemento_despesa_identificacao: str | None = None
    elemento_despesa_descricao: str | None = None
    desdobramento_despesa_identificacao: str | None = None
    desdobramento_despesa_descricao: str | None = None
    conta_extra_identificacao: str | None = None
    conta_extra_descricao: str | None = None

    numero_documento: str
    data_documento: date
    categoria_documento: str | None = None
    credor: str | None = None
    cpf_cnpj: str | None = None
    modalidade_licitacao: str | None = None
    numero_licitacao: str | None = None
    ano_licitacao: int | None = None
    data_homologacao: date | None = None
    processo_compra: str | None = None
    numero_contrato: str | None = None
    numero_convenio: str | None = None

    valor_documento: Decimal | None = None
    valor_empenhado: Decimal | None = None
    valor_liquidacao: Decimal | None = None
    valor_liquidado: Decimal | None = None
    valor_pago: Decimal | None = None
    valor_anulado: Decimal | None = None

    objetivo_viagem: str | None = None
    legislacao_associada: str | None = None
    ato_legal: str | None = None
    destino: str | None = None
    data_inicial_viagem: date | None = None
    data_final_viagem: date | None = None
    quantidade_dias_diarias: Decimal | None = None
    valor_diaria: Decimal | None = None
    valor_total: Decimal | None = None

    itens: list[DespesaDocumentoItemInSchema] = []
    documentos_comprobatorios: list[DespesaDocumentoComprobatorioInSchema] = []

    @field_validator("exercicio", "sequencia_origem", mode="before")
    @classmethod
    def _normalize_required_int(cls, value: Any) -> int:
        parsed = parse_int(value)
        if parsed is None:
            raise ValueError("inteiro obrigatorio")
        return parsed

    @field_validator("ano_licitacao", mode="before")
    @classmethod
    def _normalize_optional_int(cls, value: Any) -> int | None:
        return parse_int(value)

    @field_validator(
        "tipo_origem",
        "arquivo_origem",
        "origem",
        "unidade_gestora",
        "orgao",
        "unidade",
        "departamento",
        "funcao",
        "subfuncao",
        "programa",
        "tipo_acao",
        "descricao_acao",
        "fonte_recurso_identificacao",
        "fonte_recurso_descricao",
        "esfera_administrativa",
        "modalidade_aplicacao_identificacao",
        "modalidade_aplicacao_descricao",
        "categoria_economica_identificacao",
        "categoria_economica_descricao",
        "grupo_despesa_identificacao",
        "grupo_despesa_descricao",
        "elemento_despesa_identificacao",
        "elemento_despesa_descricao",
        "desdobramento_despesa_identificacao",
        "desdobramento_despesa_descricao",
        "conta_extra_identificacao",
        "conta_extra_descricao",
        "numero_documento",
        "categoria_documento",
        "credor",
        "cpf_cnpj",
        "modalidade_licitacao",
        "numero_licitacao",
        "processo_compra",
        "numero_contrato",
        "numero_convenio",
        "objetivo_viagem",
        "legislacao_associada",
        "ato_legal",
        "destino",
        mode="before",
    )
    @classmethod
    def _normalize_text_fields(cls, value: Any) -> str | None:
        return clean_text(value)

    @field_validator(
        "data_documento",
        "data_homologacao",
        "data_inicial_viagem",
        "data_final_viagem",
        mode="before",
    )
    @classmethod
    def _normalize_dates(cls, value: Any) -> date | None:
        return parse_date(value)

    @field_validator(
        "valor_documento",
        "valor_empenhado",
        "valor_liquidacao",
        "valor_liquidado",
        "valor_pago",
        "valor_anulado",
        "valor_diaria",
        "valor_total",
        mode="before",
    )
    @classmethod
    def _normalize_values(cls, value: Any) -> Decimal | None:
        return parse_decimal(value)

    @field_validator("quantidade_dias_diarias", mode="before")
    @classmethod
    def _normalize_quantity(cls, value: Any) -> Decimal | None:
        return parse_number(value)
