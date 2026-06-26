"""Tool publica para agregacoes de despesas da frota."""

from __future__ import annotations

from decimal import Decimal
from typing import Any

from agents.tools.names import ToolName
from agents.tools.registry import PUBLIC_SCOPE, register, routing_metadata
from agents.tools.sql_tools.shared.aggregate import (
    AggregateExecutionResult,
    build_aggregate_response,
    execute_collection_aggregate,
)
from agents.tools.sql_tools.shared.empty_state import resolve_empty_result_suggestion
from agents.tools.sql_tools.shared.validation import validate_tool_params
from database import session as session_manager
from database.models import FrotaDespesa

from .agregar_despesas_frota_schema import (
    AgregarDespesasFrotaMetadata,
    AgregarDespesasFrotaParams,
    AgregarDespesasFrotaResponse,
)
from .consultar_despesas_frota_query import load_filtered_despesas_frota


def _metric_to_json(value: Decimal | int) -> float | int:
    return float(value) if isinstance(value, Decimal) else value


GROUP_FIELD_GETTERS = {
    "tipo_despesa": lambda r: r.tipo_despesa,
    "descricao_evento": lambda r: r.descricao_evento,
    "tipo_veiculo": lambda r: r.veiculo.tipo_veiculo if r.veiculo else None,
    "placa_veiculo": lambda r: r.veiculo.placa_veiculo if r.veiculo else None,
    "unidade_responsavel": lambda r: r.veiculo.unidade_gestora if r.veiculo else None,
}
METRIC_FIELD_GETTERS = {
    "soma_total_despesa": lambda r: r.total_despesa or Decimal(0),
    "soma_valor_lancamento": lambda r: r.valor_lancamento or Decimal(0),
}


def _project_group(
    group_value: Any,
    metric_value: Any,
    agrupar_por: str,
    metrica: str,
) -> dict[str, Any]:
    return {agrupar_por: group_value, metrica: metric_value}


@register(
    name=ToolName.AGREGAR_DESPESAS_FROTA,
    scope=PUBLIC_SCOPE,
    tags=["domain:frotas", "shape:aggregate"],
    routing=routing_metadata(
        examples=[
            "Quais os principais gastos dos veiculos da prefeitura?",
            "Qual tipo de despesa mais pesa na frota municipal?",
            "Quanto a frota gastou com manutencao versus combustivel?",
            "Quais despesas aparecem mais na manutencao dos veiculos?",
        ],
        hints=[
            "principais gastos veiculos",
            "tipo de despesa frota",
            "manutencao frota",
            "combustivel frota",
            "ranking despesas veiculos",
            "despesa frota por tipo",
        ],
        exclusions=[
            "Quando a pergunta pedir quais veiculos mais gastaram, quais placas lideram o gasto ou ranking por tipo de veiculo, use `agregar_frota`.",
        ],
    ),
)
def agregar_despesas_frota(
    filtros: dict[str, Any] | None = None,
    agrupar_por: str | None = "tipo_despesa",
    metrica: str = "soma_total_despesa",
    ordenar_por: str = "metrica",
    ordem: str = "desc",
    limite: int = 10,
) -> dict[str, Any]:
    """
    Calcula totais, contagens e rankings sobre as despesas da frota municipal.

    Use esta tool quando a pergunta pedir principais gastos, tipos de despesa
    mais frequentes, comparacao entre manutencao e combustivel, ou ranking de
    despesas da frota.
    NAO use para ranking dos veiculos que mais gastaram; para isso use
    `agregar_frota`.
    NAO use para listar eventos individuais de despesa; para isso use
    `consultar_despesas_frota`.

    Args:
        filtros: Objeto com filtros opcionais. Campos aceitos: `placa`,
            `tipo_veiculo`, `tipo_despesa`, `descricao`, `data_evento_inicio` e
            `data_evento_fim`.
        agrupar_por: Campo opcional de agrupamento. Aceita `tipo_despesa`,
            `descricao_evento`, `tipo_veiculo`, `placa_veiculo` ou
            `unidade_responsavel`. Por padrao, agrupa por `tipo_despesa`.
            Quando `None`, a tool retorna apenas `valor_total`.
        metrica: Metrica calculada. Aceita `contagem`, `soma_total_despesa` ou
            `soma_valor_lancamento`.
        ordenar_por: Aceita `metrica` ou o mesmo valor usado em `agrupar_por`.
        ordem: Direcao da ordenacao: `asc` ou `desc`.
        limite: Quantidade maxima de grupos retornados. Inteiro de 1 a 100.

    Returns:
        dict com:
        - `total_grupos`: total de grupos encontrados.
        - `resultados`: lista de grupos com o campo de agrupamento e a metrica.
        - `metadata`: filtros aplicados e configuracao da agregacao.
        - `valor_total`: valor agregado quando `agrupar_por` nao for informado.
        - `mensagem`: aviso quando so parte dos grupos for exibida.
        - `sugestao`: dica quando nenhuma despesa corresponder aos filtros.
    """
    validated = validate_tool_params(
        {
            "filtros": filtros,
            "agrupar_por": agrupar_por,
            "metrica": metrica,
            "ordenar_por": ordenar_por,
            "ordem": ordem,
            "limite": limite,
        },
        schema_type=AgregarDespesasFrotaParams,
        on_error=lambda exc: AgregarDespesasFrotaResponse(
            total_grupos=0,
            resultados=[],
            metadata=AgregarDespesasFrotaMetadata(
                agrupar_por="tipo_despesa",
                metrica="soma_total_despesa",
                ordenar_por="metrica",
                ordem="desc",
                limite=10,
            ),
            mensagem=f"Parametros invalidos: {exc}",
        ).model_dump(mode="json"),
    )
    if isinstance(validated, dict):
        return validated
    params = validated

    with session_manager.get_session() as session:
        registros = load_filtered_despesas_frota(session, params.filtros)
        empty_suggestion = resolve_empty_result_suggestion(
            session,
            domain_key="frota_despesas",
            filters=params.filtros,
            default_suggestion="Nenhuma despesa de frota encontrada com os filtros.",
        )

    metadata = AgregarDespesasFrotaMetadata(
        filtros_aplicados=params.filtros.to_metadata_dict(),
        agrupar_por=params.agrupar_por,
        metrica=params.metrica,
        ordenar_por=params.ordenar_por,
        ordem=params.ordem,
        limite=params.limite,
    )

    execution = execute_collection_aggregate(
        registros,
        agrupar_por=params.agrupar_por,
        metrica=params.metrica,
        ordenar_por=params.ordenar_por,
        ordem=params.ordem,
        limite=params.limite,
        group_key_getters=GROUP_FIELD_GETTERS,
        metric_getters=METRIC_FIELD_GETTERS,
        serialize_metric=_metric_to_json,
    )
    suggestion = (
        empty_suggestion
        if (
            (params.agrupar_por is None and execution.source_count == 0)
            or (params.agrupar_por is not None and not execution.rows)
        )
        else None
    )
    return build_aggregate_response(
        response_type=AgregarDespesasFrotaResponse,
        metadata=metadata,
        execution=AggregateExecutionResult(
            total_grupos=execution.total_grupos,
            rows=execution.rows,
            valor_total=execution.valor_total,
            source_count=execution.source_count,
            suggestion=suggestion,
        ),
        project_group=_project_group if params.agrupar_por is not None else None,
        agrupar_por=params.agrupar_por,
        metrica=params.metrica if params.agrupar_por is not None else None,
    )
