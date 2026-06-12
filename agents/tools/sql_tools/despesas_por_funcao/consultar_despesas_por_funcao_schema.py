"""Schemas da tool publica consultar_despesas_por_funcao."""

from __future__ import annotations

from datetime import date
from decimal import Decimal
from typing import Any

from pydantic import Field, field_validator, model_validator

from agents.tools.sql_tools.shared.base import SqlToolBaseSchema
from agents.tools.sql_tools.shared.normalization import (
    normalize_model_input,
    normalize_selected_fields,
)
from shared.utils.validation import (
    clean_text,
    parse_date,
    parse_decimal,
    parse_int,
    validate_date_period,
)


DEFAULT_DESPESAS_POR_FUNCAO_FIELDS = (
    "origem",
    "ano",
    "periodo_inicio",
    "periodo_fim",
    "unidade_gestora",
    "funcao",
    "dotacao_inicial",
    "creditos_adicionais",
    "dotacao_atualizada",
    "valor_empenhado",
    "valor_em_liquidacao",
    "valor_liquidado",
    "valor_pago",
)
ALLOWED_DESPESAS_POR_FUNCAO_FIELDS = set(DEFAULT_DESPESAS_POR_FUNCAO_FIELDS)
DESPESAS_POR_FUNCAO_FIELD_EXPLANATIONS = {
    "origem": "Origem do arquivo importado que gerou a linha, como prefeitura ou saude.",
    "ano": "Exercicio orcamentario ao qual a linha pertence.",
    "periodo_inicio": "Data inicial do periodo consolidado no relatorio.",
    "periodo_fim": "Data final do periodo consolidado no relatorio.",
    "unidade_gestora": "Unidade gestora responsavel pela execucao orcamentaria.",
    "funcao": "Funcao de governo padronizada nacionalmente, como saude ou educacao.",
    "dotacao_inicial": "Valor aprovado no orcamento inicial para a funcao no periodo.",
    "creditos_adicionais": "Ajustes feitos no orcamento ao longo do exercicio.",
    "dotacao_atualizada": "Dotacao inicial somada aos creditos adicionais.",
    "valor_empenhado": "Valor ja comprometido oficialmente pela administracao.",
    "valor_em_liquidacao": "Valor que esta em fase de conferencia antes da liquidacao.",
    "valor_liquidado": "Valor com entrega ou servico reconhecido pela administracao.",
    "valor_pago": "Valor efetivamente pago no periodo.",
}
DESPESAS_POR_FUNCAO_FINANCIAL_STAGE_FIELDS = (
    "valor_empenhado",
    "valor_em_liquidacao",
    "valor_liquidado",
    "valor_pago",
)
DESPESAS_POR_FUNCAO_BROAD_SPEND_GUIDANCE = (
    "Em perguntas amplas sobre gasto por funcao, nao resuma a resposta em apenas "
    "um total. Mostre e diferencie valor_empenhado, valor_em_liquidacao, "
    "valor_liquidado e valor_pago."
)
ALLOWED_DESPESAS_POR_FUNCAO_SORT_FIELDS = {
    "periodo_fim",
    "funcao",
    "dotacao_atualizada",
    "valor_empenhado",
    "valor_liquidado",
    "valor_pago",
}
ALLOWED_ORDER_VALUES = {"asc", "desc"}


class DespesasPorFuncaoFiltroSchema(SqlToolBaseSchema):
    """Filtros publicos aceitos pela tool deste dominio."""

    origem: str | None = None
    ano: int | None = None
    periodo_inicio: date | None = None
    periodo_fim: date | None = None
    unidade_gestora: str | None = None
    funcao: str | None = None
    valor_pago_min: Decimal | None = None
    valor_pago_max: Decimal | None = None

    @field_validator("origem", "unidade_gestora", "funcao", mode="before")
    @classmethod
    def _normalize_text(cls, value: Any) -> str | None:
        return clean_text(value)

    @field_validator("ano", mode="before")
    @classmethod
    def _normalize_ano(cls, value: Any) -> int | None:
        return parse_int(value)

    @field_validator("periodo_inicio", "periodo_fim", mode="before")
    @classmethod
    def _normalize_dates(cls, value: Any) -> date | None:
        return parse_date(value)

    @field_validator("valor_pago_min", "valor_pago_max", mode="before")
    @classmethod
    def _normalize_decimal(cls, value: Any) -> Decimal | None:
        return parse_decimal(value)

    @model_validator(mode="after")
    def _validate_period_and_range(self) -> DespesasPorFuncaoFiltroSchema:
        if self.periodo_inicio and self.periodo_fim:
            validate_date_period(self.periodo_inicio, self.periodo_fim)
        if (
            self.valor_pago_min is not None
            and self.valor_pago_max is not None
            and self.valor_pago_min > self.valor_pago_max
        ):
            raise ValueError("valor_pago_min deve ser menor ou igual a valor_pago_max")
        return self


class ConsultarDespesasPorFuncaoParams(SqlToolBaseSchema):
    """Parametros validados da chamada da tool."""

    filtros: DespesasPorFuncaoFiltroSchema = Field(default_factory=DespesasPorFuncaoFiltroSchema)
    ordenar_por: str = "periodo_fim"
    ordem: str = "desc"
    limite: int = 10
    offset: int = 0
    campos: list[str] = Field(default_factory=list)

    @field_validator("filtros", mode="before")
    @classmethod
    def _normalize_filtros(cls, value: Any) -> DespesasPorFuncaoFiltroSchema:
        return normalize_model_input(
            value,
            schema_type=DespesasPorFuncaoFiltroSchema,
            field_name="filtros",
        )

    @field_validator("ordenar_por", mode="before")
    @classmethod
    def _normalize_ordenar_por(cls, value: Any) -> str:
        normalized = clean_text(value) or "periodo_fim"
        if normalized not in ALLOWED_DESPESAS_POR_FUNCAO_SORT_FIELDS:
            raise ValueError(f"ordenar_por nao suportado: {normalized}")
        return normalized

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
        if value is None:
            return 10
        return max(1, min(int(value), 100))

    @field_validator("offset", mode="before")
    @classmethod
    def _normalize_offset(cls, value: Any) -> int:
        if value is None:
            return 0
        return max(0, int(value))

    @field_validator("campos", mode="before")
    @classmethod
    def _normalize_campos(cls, value: Any) -> list[str]:
        return normalize_selected_fields(
            value,
            allowed_fields=ALLOWED_DESPESAS_POR_FUNCAO_FIELDS,
            require_list=False,
            error_style="campos",
        )


class ConsultarDespesasPorFuncaoMetadata(SqlToolBaseSchema):
    """Metadados ecoados na resposta (filtros, ordenacao, paginacao)."""

    filtros_aplicados: dict[str, Any] = Field(default_factory=dict)
    ordenar_por: str
    ordem: str
    limite: int
    offset: int
    campos: list[str] = Field(default_factory=lambda: list(DEFAULT_DESPESAS_POR_FUNCAO_FIELDS))
    explicacao_campos: dict[str, str] = Field(default_factory=dict)
    campos_financeiros_prioritarios: list[str] = Field(default_factory=list)
    explicacao_estagios_despesa: dict[str, str] = Field(default_factory=dict)
    orientacao_gasto_amplo: str | None = None


class ConsultarDespesasPorFuncaoResponse(SqlToolBaseSchema):
    """Formato da resposta publica da tool."""

    total: int
    resultados: list[dict[str, Any]] = Field(default_factory=list)
    metadata: ConsultarDespesasPorFuncaoMetadata
    mensagem: str | None = None
    sugestao: str | None = None
