"""Tool publica para agregacoes de frota."""

from __future__ import annotations

from decimal import Decimal
from typing import Any

from agents.tools.names import ToolName
from agents.tools.registry import PUBLIC_SCOPE, register, routing_metadata
from agents.tools.sql_tools.shared.empty_state import resolve_empty_result_suggestion
from agents.tools.sql_tools.shared.aggregate import (
    AggregateExecutionResult,
    build_aggregate_response,
    execute_collection_aggregate,
)
from agents.tools.sql_tools.shared.validation import validate_tool_params
from database import session as session_manager
from database.models import FrotaVeiculo

from .agregar_frota_schema import (
    AgregarFrotaMetadata,
    AgregarFrotaParams,
    AgregarFrotaResponse,
)
from .consultar_frota_query import load_filtered_frota


def _veiculo_total_despesas(veiculo: FrotaVeiculo) -> Decimal:
    return sum(d.total_despesa or Decimal(0) for d in veiculo.despesas)


def _metric_to_json(value: Decimal | int) -> float | int:
    return float(value) if isinstance(value, Decimal) else value


GROUP_FIELD_GETTERS = {
    "unidade_responsavel": lambda r: r.unidade_gestora,
    "tipo_veiculo": lambda r: r.tipo_veiculo,
    "situacao": lambda r: r.situacao_veiculo,
    "localizacao": lambda r: r.localizacao,
    "marca": lambda r: r.marca,
}
METRIC_FIELD_GETTERS = {
    "soma_valor_atual": lambda r: r.valor_atual or Decimal(0),
    "soma_total_despesas": _veiculo_total_despesas,
}


def _project_frota_group(
    group_value: Any,
    metric_value: Any,
    agrupar_por: str,
    metrica: str,
) -> dict[str, Any]:
    return {agrupar_por: group_value, metrica: metric_value}


@register(
    name=ToolName.AGREGAR_FROTA,
    scope=PUBLIC_SCOPE,
    tags=["domain:frotas", "shape:aggregate"],
    routing=routing_metadata(
        examples=[
            "Qual tipo de veiculo tem maior custo de manutencao?",
            "Qual secretaria tem a frota mais cara de manter?",
            "Quais os 10 veiculos com maior gasto total?",
        ],
        hints=[
            "frota",
            "veiculo",
            "ranking",
            "custo manutencao",
            "total despesas frota",
            "tipo de veiculo",
            "valor frota",
        ],
    ),
)
def agregar_frota(
    filtros: dict[str, Any] | None = None,
    agrupar_por: str | None = None,
    metrica: str = "contagem",
    ordenar_por: str = "metrica",
    ordem: str = "desc",
    limite: int = 10,
) -> dict[str, Any]:
    """
    Calcula totais, somas e rankings sobre veiculos da frota municipal.

    Use esta tool quando a pergunta pedir quantos veiculos existem por tipo ou
    secretaria, qual grupo tem maior valor patrimonial ou maior custo de
    manutencao acumulado.
    NAO use para listar veiculos individuais; para isso use `consultar_frota`.
    NAO use para bens patrimoniais em geral; para isso use `agregar_patrimonios`.

    Args:
        filtros: Objeto com filtros opcionais. Campos aceitos:
            `unidade_responsavel`, `placa`, `descricao`, `tipo_veiculo`,
            `marca`, `modelo`, `situacao`, `localizacao`,
            `data_aquisicao_inicio` e `data_aquisicao_fim`.
        agrupar_por: Campo opcional de agrupamento. Aceita
            `unidade_responsavel`, `tipo_veiculo`, `situacao`, `localizacao`
            ou `marca`. Se nao for informado, a tool retorna um `valor_total`.
        metrica: Metrica calculada. Aceita `contagem`, `soma_valor_atual` ou
            `soma_total_despesas`.
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
        - `sugestao`: dica quando nenhum veiculo corresponder aos filtros.
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
        schema_type=AgregarFrotaParams,
        on_error=lambda exc: AgregarFrotaResponse(
            total_grupos=0,
            resultados=[],
            metadata=AgregarFrotaMetadata(
                metrica="contagem",
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

    # Aggregate inside session so lazy-loaded despesas relationship is accessible.
    with session_manager.get_session() as session:
        registros = load_filtered_frota(session, params.filtros)
        empty_suggestion = resolve_empty_result_suggestion(
            session,
            domain_key="frota",
            filters=params.filtros,
            default_suggestion="Nenhum veiculo de frota encontrado com os filtros.",
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

    metadata = AgregarFrotaMetadata(
        filtros_aplicados=params.filtros.to_metadata_dict(),
        agrupar_por=params.agrupar_por,
        metrica=params.metrica,
        ordenar_por=params.ordenar_por,
        ordem=params.ordem,
        limite=params.limite,
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
        response_type=AgregarFrotaResponse,
        metadata=metadata,
        execution=AggregateExecutionResult(
            total_grupos=execution.total_grupos,
            rows=execution.rows,
            valor_total=execution.valor_total,
            source_count=execution.source_count,
            suggestion=suggestion,
        ),
        project_group=(_project_frota_group if params.agrupar_por is not None else None),
        agrupar_por=params.agrupar_por,
        metrica=params.metrica if params.agrupar_por is not None else None,
    )
