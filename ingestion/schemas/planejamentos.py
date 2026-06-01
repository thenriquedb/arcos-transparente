"""Schemas Pydantic para ingestao de planejamentos orcamentarios."""

from __future__ import annotations

from decimal import Decimal
from typing import Any

from pydantic import BaseModel, ConfigDict, field_validator, model_validator

from shared.utils.validation import clean_text, parse_decimal, parse_month


class _PlanejamentoBaseSchema(BaseModel):
    """Base compartilhada de saneamento para schemas de planejamento."""

    model_config = ConfigDict(extra="ignore")


class PlanejamentoDespesaInSchema(_PlanejamentoBaseSchema):
    """Schema principal de uma linha mensal de planejamento de despesa."""

    origem: str = "saude"
    exercicio: int
    mes: str
    mes_num: int | None = None
    unidade_gestora: str
    orgao: str | None = None
    unidade: str | None = None
    departamento: str | None = None
    funcao: str
    subfuncao: str | None = None
    programa: str | None = None
    tipo_acao: str | None = None
    descricao_acao: str
    fonte_recurso_identificacao: str | None = None
    fonte_recurso_descricao: str | None = None
    esfera_administrativa: str | None = None
    categoria_economica_identificacao: str | None = None
    categoria_economica_descricao: str | None = None
    grupo_despesa_identificacao: str | None = None
    grupo_despesa_descricao: str | None = None
    elemento_despesa_identificacao: str | None = None
    elemento_despesa_descricao: str | None = None
    modalidade_aplicacao_identificacao: str | None = None
    modalidade_aplicacao_descricao: str | None = None
    dotacao_inicial: Decimal | None = None
    creditos_adicionais: Decimal | None = None
    dotacao_atualizada: Decimal | None = None
    valor_empenhado: Decimal | None = None
    valor_liquidacao: Decimal | None = None
    valor_liquidado: Decimal | None = None
    valor_pago: Decimal | None = None
    valor_anulado: Decimal | None = None

    @field_validator("exercicio", mode="before")
    @classmethod
    def _normalize_exercicio(cls, value: Any) -> int:
        if value is None:
            raise ValueError("exercicio obrigatorio")
        return int(value)

    @field_validator("mes_num", mode="before")
    @classmethod
    def _normalize_mes_num(cls, value: Any) -> int | None:
        if value is None:
            return None
        return int(value)

    @field_validator(
        "origem",
        "mes",
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
        "categoria_economica_identificacao",
        "categoria_economica_descricao",
        "grupo_despesa_identificacao",
        "grupo_despesa_descricao",
        "elemento_despesa_identificacao",
        "elemento_despesa_descricao",
        "modalidade_aplicacao_identificacao",
        "modalidade_aplicacao_descricao",
        mode="before",
    )
    @classmethod
    def _normalize_text_fields(cls, value: Any) -> str | None:
        return clean_text(value)

    @field_validator(
        "dotacao_inicial",
        "creditos_adicionais",
        "dotacao_atualizada",
        "valor_empenhado",
        "valor_liquidacao",
        "valor_liquidado",
        "valor_pago",
        "valor_anulado",
        mode="before",
    )
    @classmethod
    def _normalize_decimal_fields(cls, value: Any) -> Decimal | None:
        return parse_decimal(value)

    @model_validator(mode="after")
    def _apply_defaults(self) -> "PlanejamentoDespesaInSchema":
        if not self.origem:
            self.origem = "saude"
        if self.mes_num is None:
            self.mes_num = parse_month(self.mes)
        if self.mes_num is None:
            raise ValueError("mes invalido")
        self.mes = self.mes.upper()
        return self
