"""Tool publica para agregacoes de saldos de estoque."""

from __future__ import annotations

from decimal import Decimal
from typing import Any

from agents.tools.registry import PUBLIC_SCOPE, register, routing_metadata
from agents.tools.sql_tools.shared.aggregate import (
    AggregateExecutionResult,
    build_aggregate_response,
    execute_collection_aggregate,
)
from agents.tools.sql_tools.shared.validation import validate_tool_params
from database import session as session_manager
from database.models import EstoqueMaterial

from .agregar_estoques_schema import (
    AgregarEstoquesMetadata,
    AgregarEstoquesParams,
    AgregarEstoquesResponse,
)
from .consultar_estoques_query import load_filtered_estoques


def _metric_to_json(value: Decimal | int) -> float | int:
    if isinstance(value, Decimal):
        return float(value)
    return value


GROUP_FIELD_GETTERS = {
    "origem": lambda registro: registro.origem,
    "ano": lambda registro: registro.exercicio,
    "unidade_medida": lambda registro: registro.unidade_medida,
    "material": lambda registro: registro.material,
}
METRIC_FIELD_GETTERS = {
    "soma_entrada_quantidade": lambda registro: registro.entrada_quantidade
    or Decimal("0"),
    "soma_entrada_valor": lambda registro: registro.entrada_valor or Decimal("0"),
    "soma_saida_quantidade": lambda registro: registro.saida_quantidade
    or Decimal("0"),
    "soma_saida_valor": lambda registro: registro.saida_valor or Decimal("0"),
    "soma_saldo_quantidade": lambda registro: registro.saldo_quantidade
    or Decimal("0"),
    "soma_saldo_valor": lambda registro: registro.saldo_valor or Decimal("0"),
}


def _project_estoque_group(
    group_value: Any,
    metric_value: Any,
    agrupar_por: str,
    metrica: str,
) -> dict[str, Any]:
    return {agrupar_por: group_value, metrica: metric_value}


@register(
    name="agregar_estoques",
    scope=PUBLIC_SCOPE,
    tags=["domain:estoques", "shape:aggregate"],
    routing=routing_metadata(
        examples=[
            "Qual o saldo total em estoque em 2025?",
            "Quais materiais tem maior saldo em estoque?",
        ],
        hints=[
            "estoque",
            "saldo total",
            "ranking de materiais",
            "almoxarifado",
            "entrada",
        ],
    ),
)
def agregar_estoques(
    filtros: dict[str, Any] | None = None,
    agrupar_por: str | None = None,
    metrica: str = "soma_saldo_valor",
    ordenar_por: str = "metrica",
    ordem: str = "desc",
    limite: int = 10,
) -> dict[str, Any]:
    """
    Calcula totais, contagens e rankings sobre os saldos sumarizados de estoque.

    Use esta tool quando a pergunta pedir total, contagem, comparacao ou
    ranking de saldos, entradas ou saidas de materiais em estoque.
    NAO use para listar materiais individualmente; para isso use
    `consultar_estoques`.
    NAO use para historico diario de requisicoes, compras ou aplicacoes
    imediatas; para isso use `consultar_movimentacoes_de_estoque`.
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
        schema_type=AgregarEstoquesParams,
        on_error=lambda exc: AgregarEstoquesResponse(
            total_grupos=0,
            resultados=[],
            metadata=AgregarEstoquesMetadata(
                metrica="soma_saldo_valor",
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
        registros = load_filtered_estoques(session, params.filtros)

    metadata = AgregarEstoquesMetadata(
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
        "Nenhum material de estoque encontrado com os filtros."
        if (
            (params.agrupar_por is None and execution.source_count == 0)
            or (params.agrupar_por is not None and not execution.rows)
        )
        else None
    )
    return build_aggregate_response(
        response_type=AgregarEstoquesResponse,
        metadata=metadata,
        execution=AggregateExecutionResult(
            total_grupos=execution.total_grupos,
            rows=execution.rows,
            valor_total=execution.valor_total,
            source_count=execution.source_count,
            suggestion=suggestion,
        ),
        project_group=(_project_estoque_group if params.agrupar_por is not None else None),
        agrupar_por=params.agrupar_por,
        metrica=params.metrica if params.agrupar_por is not None else None,
    )
