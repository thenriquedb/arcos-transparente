"""Resolvedor compartilhado de estado vazio para tools SQL publicas."""

from __future__ import annotations

from collections.abc import Callable, Mapping, Sequence
from dataclasses import dataclass
from typing import Any

from pydantic import BaseModel
from sqlalchemy import func, select

from database.models import (
    Contrato,
    DespesaDocumento,
    DespesaPorFuncao,
    Eleito,
    EmendaParlamentar,
    EstoqueMaterial,
    EstoqueMovimentacao,
    FolhaCargo,
    FolhaLotacao,
    FolhaPagamentoRegistro,
    FolhaServidor,
    FrotaDespesa,
    FrotaVeiculo,
    Licitacao,
    Patrimonio,
    PlanejamentoDespesa,
    QuadroPessoal,
    ReceitaArrecadacao,
    ReceitaLancamento,
    Servidor,
    ServidorCamara,
    TransferenciaFinanceiraMovimento,
)
from ingestion.modules.discovery import discover_files_for_tipo
from shared.runtime_config import get_cli_data_directory
from shared.utils.text import normalize_search_text


ModelSelector = Callable[[Mapping[str, Any]], Sequence[type[Any]]]
TermSelector = Callable[[Mapping[str, Any]], Sequence[str]]
LabelSelector = Callable[[Mapping[str, Any]], str]
ConditionBuilder = Callable[[type[Any], Mapping[str, Any]], Sequence[Any]]


@dataclass(frozen=True, slots=True)
class EmptyStateSpec:
    label: str | LabelSelector
    import_tipo: str
    models: Sequence[type[Any]] | ModelSelector
    file_terms: Sequence[str] | TermSelector = ()
    trigger_fields: Sequence[str] = ("ano", "origem")
    condition_builder: ConditionBuilder | None = None


def _select_receita_models(filters: Mapping[str, Any]) -> Sequence[type[Any]]:
    if filters.get("tipo_de_dado") == "arrecadacao":
        return (ReceitaArrecadacao,)
    if filters.get("tipo_de_dado") == "lancamento":
        return (ReceitaLancamento,)
    return (ReceitaArrecadacao, ReceitaLancamento)


def _select_receita_terms(filters: Mapping[str, Any]) -> Sequence[str]:
    if filters.get("tipo_de_dado") == "arrecadacao":
        return ("arrecadacao",)
    if filters.get("tipo_de_dado") == "lancamento":
        return ("lancamento",)
    return ("arrecadacao", "lancamento")


def _select_receita_label(filters: Mapping[str, Any]) -> str:
    if filters.get("tipo_de_dado") == "arrecadacao":
        return "arrecadacoes"
    if filters.get("tipo_de_dado") == "lancamento":
        return "lancamentos"
    return "receitas"


def _select_transfer_models(filters: Mapping[str, Any]) -> Sequence[type[Any]]:
    tipo_registro = filters.get("tipo_registro")
    if tipo_registro == "emenda":
        return (EmendaParlamentar,)
    if tipo_registro == "movimentacao":
        return (TransferenciaFinanceiraMovimento,)
    return (TransferenciaFinanceiraMovimento, EmendaParlamentar)


def _select_transfer_terms(filters: Mapping[str, Any]) -> Sequence[str]:
    tipo_registro = filters.get("tipo_registro")
    if tipo_registro == "emenda":
        return ("emendas-parlamentares",)
    if tipo_registro == "movimentacao":
        return ("recebimentos",)
    return ("recebimentos", "emendas-parlamentares")


def _select_transfer_label(filters: Mapping[str, Any]) -> str:
    tipo_registro = filters.get("tipo_registro")
    if tipo_registro == "emenda":
        return "emendas parlamentares"
    if tipo_registro == "movimentacao":
        return "transferencias financeiras"
    return "transferencias financeiras e emendas parlamentares"


def _tipo_origem_condition(tipo_origem: str) -> ConditionBuilder:
    def _builder(model: type[Any], _filters: Mapping[str, Any]) -> Sequence[Any]:
        if hasattr(model, "tipo_origem"):
            return (getattr(model, "tipo_origem") == tipo_origem,)
        return ()

    return _builder


EMPTY_STATE_SPECS: dict[str, EmptyStateSpec] = {
    "contratos": EmptyStateSpec("contratos", "contratos", (Contrato,)),
    "despesas": EmptyStateSpec(
        "despesas",
        "despesas",
        (DespesaDocumento,),
        file_terms=("empenhos", "restos-a-pagar", "documentos-extras"),
    ),
    "despesas_por_funcao": EmptyStateSpec(
        "despesas por funcao",
        "despesas",
        (DespesaPorFuncao,),
        file_terms=("despesas-por-funcao",),
    ),
    "diarias": EmptyStateSpec(
        "diarias",
        "despesas",
        (DespesaDocumento,),
        file_terms=("diarias",),
        condition_builder=_tipo_origem_condition("diaria"),
    ),
    "eleitos": EmptyStateSpec("politicos eleitos", "eleitos", (Eleito,)),
    "estoques": EmptyStateSpec("estoques", "estoques", (EstoqueMaterial,)),
    "estoques_movimentacoes": EmptyStateSpec(
        "movimentacoes de estoque",
        "estoques",
        (EstoqueMovimentacao,),
    ),
    "folha_cargos": EmptyStateSpec("folha por cargo", "folha_pagamento", (FolhaCargo,)),
    "folha_lotacoes": EmptyStateSpec("folha por lotacao", "folha_pagamento", (FolhaLotacao,)),
    "folha_pagamentos": EmptyStateSpec("folha de pagamento", "folha_pagamento", (FolhaPagamentoRegistro,)),
    "frota": EmptyStateSpec("frota", "frotas", (FrotaVeiculo,)),
    "frota_despesas": EmptyStateSpec("despesas de frota", "frotas", (FrotaDespesa,)),
    "licitacoes": EmptyStateSpec("licitacoes", "licitacoes", (Licitacao,)),
    "passagens": EmptyStateSpec(
        "passagens",
        "despesas",
        (DespesaDocumento,),
        file_terms=("passagens",),
        condition_builder=_tipo_origem_condition("passagem"),
    ),
    "patrimonios": EmptyStateSpec("bens patrimoniais", "patrimonios", (Patrimonio,)),
    "planejamento": EmptyStateSpec("planejamento", "planejamentos", (PlanejamentoDespesa,)),
    "quadro_pessoal": EmptyStateSpec("quadro de pessoal", "quadro_pessoal", (QuadroPessoal,)),
    "receitas": EmptyStateSpec(
        _select_receita_label,
        "receitas",
        _select_receita_models,
        file_terms=_select_receita_terms,
        trigger_fields=("ano", "tipo_de_dado"),
    ),
    "servidores": EmptyStateSpec("servidores", "folha_pagamento", (FolhaServidor,)),
    "servidores_funcional": EmptyStateSpec("servidores", "servidores", (Servidor,)),
    "servidores_camara": EmptyStateSpec("servidores da camara", "servidores_camara", (ServidorCamara,)),
    "transferencias_financeiras": EmptyStateSpec(
        _select_transfer_label,
        "transferencias_financeiras",
        _select_transfer_models,
        file_terms=_select_transfer_terms,
        trigger_fields=("ano", "origem", "tipo_registro"),
    ),
}


def _filters_to_mapping(filters: BaseModel | Mapping[str, Any] | None) -> dict[str, Any]:
    if filters is None:
        return {}
    if isinstance(filters, BaseModel):
        return filters.model_dump(mode="python", exclude_none=True)
    if isinstance(filters, Mapping):
        return {key: value for key, value in filters.items() if value is not None}
    return {}


def _resolve_label(spec: EmptyStateSpec, filters: Mapping[str, Any]) -> str:
    if callable(spec.label):
        return spec.label(filters)
    return spec.label


def _resolve_models(spec: EmptyStateSpec, filters: Mapping[str, Any]) -> Sequence[type[Any]]:
    if callable(spec.models):
        return spec.models(filters)
    return spec.models


def _resolve_terms(spec: EmptyStateSpec, filters: Mapping[str, Any]) -> Sequence[str]:
    if callable(spec.file_terms):
        return spec.file_terms(filters)
    return spec.file_terms


def _build_conditions(
    model: type[Any],
    filters: Mapping[str, Any],
    *,
    extra_builder: ConditionBuilder | None,
) -> list[Any]:
    conditions: list[Any] = []

    if extra_builder is not None:
        conditions.extend(extra_builder(model, filters))

    year_value = filters.get("ano")
    if year_value is not None:
        if hasattr(model, "exercicio"):
            conditions.append(getattr(model, "exercicio") == year_value)
        elif hasattr(model, "ano"):
            conditions.append(getattr(model, "ano") == year_value)

    origem = filters.get("origem")
    if origem is not None and hasattr(model, "origem"):
        conditions.append(func.lower(getattr(model, "origem")) == normalize_search_text(origem))

    return conditions


def _count_rows_for_scope(
    session,
    spec: EmptyStateSpec,
    filters: Mapping[str, Any],
) -> int:
    total = 0
    for model in _resolve_models(spec, filters):
        stmt = select(func.count()).select_from(model)
        conditions = _build_conditions(model, filters, extra_builder=spec.condition_builder)
        if conditions:
            stmt = stmt.where(*conditions)
        total += session.execute(stmt).scalar_one()
    return total


def _matching_source_files(
    spec: EmptyStateSpec,
    filters: Mapping[str, Any],
) -> list[Any]:
    year_value = filters.get("ano")
    arquivos = discover_files_for_tipo(get_cli_data_directory(), spec.import_tipo, year_value)
    terms = tuple(normalize_search_text(term) for term in _resolve_terms(spec, filters))
    if terms:
        arquivos = [
            arquivo for arquivo in arquivos if any(term in normalize_search_text(arquivo.name) for term in terms)
        ]

    origem = filters.get("origem")
    if origem is not None:
        origem_norm = normalize_search_text(origem)
        arquivos = [arquivo for arquivo in arquivos if origem_norm in normalize_search_text(arquivo.name)]

    return arquivos


def _has_trigger_context(
    spec: EmptyStateSpec,
    filters: Mapping[str, Any],
) -> bool:
    return any(filters.get(field_name) is not None for field_name in spec.trigger_fields)


def _build_context(filters: Mapping[str, Any]) -> str:
    recorte: list[str] = []
    if filters.get("ano") is not None:
        recorte.append(str(filters["ano"]))
    if filters.get("origem"):
        recorte.append(f"origem {filters['origem']}")
    return f" para {' e '.join(recorte)}" if recorte else ""


def resolve_empty_result_suggestion(
    session,
    *,
    domain_key: str,
    filters: BaseModel | Mapping[str, Any] | None,
    default_suggestion: str,
) -> str:
    spec = EMPTY_STATE_SPECS.get(domain_key)
    if spec is None:
        return default_suggestion

    filters_map = _filters_to_mapping(filters)
    if not _has_trigger_context(spec, filters_map):
        return default_suggestion
    if _count_rows_for_scope(session, spec, filters_map) > 0:
        return default_suggestion

    if not _matching_source_files(spec, filters_map):
        return default_suggestion

    label = _resolve_label(spec, filters_map)
    context = _build_context(filters_map)
    return (
        f"Os arquivos-fonte de {label}{context} existem no ambiente, mas esse dominio ainda nao foi importado "
        "no banco local. Reimporte a base SQLite antes de responder essa pergunta."
    )
