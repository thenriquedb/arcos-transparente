"""Tool publica para agregacoes de saldos de estoque."""

from __future__ import annotations

from decimal import Decimal
from typing import Any

from agents.tools.registry import PUBLIC_SCOPE, register, routing_metadata
from agents.tools.sql_tools.shared.aggregate import (
    AggregateExecutionResult,
    build_aggregate_response,
    calculate_collection_metric,
    execute_collection_aggregate,
)
from agents.tools.sql_tools.shared.validation import validate_tool_params
from database import session as session_manager
from database.models import EstoqueMovimentacao

from .agregar_estoques_schema import (
    AgregarEstoquesMetadata,
    AgregarEstoquesParams,
    AgregarEstoquesResponse,
)
from .consultar_estoques_query import load_filtered_estoques
from .consultar_movimentacoes_de_estoque_query import (
    load_filtered_estoque_movimentacoes,
)


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
    "soma_entrada_quantidade": lambda registro: registro.entrada_quantidade or Decimal("0"),
    "soma_entrada_valor": lambda registro: registro.entrada_valor or Decimal("0"),
    "soma_movimentacao_quantidade": lambda registro: (
        (registro.entrada_quantidade or Decimal("0")) + (registro.saida_quantidade or Decimal("0"))
    ),
    "soma_movimentacao_valor": lambda registro: (
        (registro.entrada_valor or Decimal("0")) + (registro.saida_valor or Decimal("0"))
    ),
    "soma_saida_quantidade": lambda registro: registro.saida_quantidade or Decimal("0"),
    "soma_saida_valor": lambda registro: registro.saida_valor or Decimal("0"),
    "soma_saldo_quantidade": lambda registro: registro.saldo_quantidade or Decimal("0"),
    "soma_saldo_valor": lambda registro: registro.saldo_valor or Decimal("0"),
}
MOVEMENT_GROUP_FIELD_GETTERS = {
    "origem": lambda registro: registro.estoque_material.origem,
    "ano": lambda registro: registro.estoque_material.exercicio,
    "unidade_medida": lambda registro: registro.estoque_material.unidade_medida,
    "material": lambda registro: registro.estoque_material.material,
}
COMPANION_METRICS = {
    "soma_entrada_quantidade": "soma_entrada_valor",
    "soma_entrada_valor": "soma_entrada_quantidade",
    "soma_movimentacao_quantidade": "soma_movimentacao_valor",
    "soma_movimentacao_valor": "soma_movimentacao_quantidade",
    "soma_saida_quantidade": "soma_saida_valor",
    "soma_saida_valor": "soma_saida_quantidade",
}


def _abs_decimal(value: Decimal | None) -> Decimal:
    if value is None:
        return Decimal("0")
    return value.copy_abs()


def _is_saida_movimentacao(registro: EstoqueMovimentacao) -> bool:
    tipo = (registro.tipo_movimento or "").strip().lower()
    if tipo in {"requisicao", "aplicacao imediata"}:
        return True
    if registro.valor_total is not None and registro.valor_total < 0:
        return True
    return False


def _is_entrada_movimentacao(registro: EstoqueMovimentacao) -> bool:
    tipo = (registro.tipo_movimento or "").strip().lower()
    if tipo == "nota fiscal de compra":
        return True
    if registro.valor_total is not None and registro.valor_total > 0:
        return True
    return False


MOVEMENT_METRIC_FIELD_GETTERS = {
    "soma_entrada_quantidade": lambda registro: (
        _abs_decimal(registro.quantidade) if _is_entrada_movimentacao(registro) else Decimal("0")
    ),
    "soma_entrada_valor": lambda registro: (
        _abs_decimal(registro.valor_total) if _is_entrada_movimentacao(registro) else Decimal("0")
    ),
    "soma_movimentacao_quantidade": lambda registro: _abs_decimal(registro.quantidade),
    "soma_movimentacao_valor": lambda registro: _abs_decimal(registro.valor_total),
    "soma_saida_quantidade": lambda registro: (
        _abs_decimal(registro.quantidade) if _is_saida_movimentacao(registro) else Decimal("0")
    ),
    "soma_saida_valor": lambda registro: (
        _abs_decimal(registro.valor_total) if _is_saida_movimentacao(registro) else Decimal("0")
    ),
}


def _project_estoque_group(
    group_value: Any,
    metric_value: Any,
    agrupar_por: str,
    metrica: str,
    *,
    companion_metrics: dict[Any, dict[str, Any]] | None = None,
) -> dict[str, Any]:
    projected = {agrupar_por: group_value, metrica: metric_value}
    if companion_metrics is not None:
        projected.update(companion_metrics.get(group_value, {}))
    return projected


def _normalize_group_value(group_value: Any) -> Any:
    if group_value in (None, ""):
        return "nao_informado"
    return group_value


def _build_companion_metrics(
    registros: list[Any],
    *,
    execution_rows: list[tuple[Any, Any]] | tuple[tuple[Any, Any], ...],
    agrupar_por: str | None,
    metrica: str,
    group_key_getters: dict[str, Any],
    metric_getters: dict[str, Any],
) -> dict[Any, dict[str, Any]]:
    if agrupar_por is None:
        return {}

    companion_metric = COMPANION_METRICS.get(metrica)
    if companion_metric is None:
        return {}

    group_getter = group_key_getters[agrupar_por]
    selected_groups = {_normalize_group_value(group_value) for group_value, _metric in execution_rows}
    grouped_rows: dict[Any, list[Any]] = {}
    for registro in registros:
        group_value = _normalize_group_value(group_getter(registro))
        if group_value not in selected_groups:
            continue
        grouped_rows.setdefault(group_value, []).append(registro)

    return {
        group_value: {
            companion_metric: _metric_to_json(
                calculate_collection_metric(
                    group_rows,
                    metrica=companion_metric,
                    metric_getters=metric_getters,
                )
            )
        }
        for group_value, group_rows in grouped_rows.items()
    }


def _should_use_movimentacoes(params: AgregarEstoquesParams) -> bool:
    if params.metrica in {"soma_movimentacao_quantidade", "soma_movimentacao_valor"}:
        return True
    return params.filtros.has_movement_filters()


@register(
    name="agregar_estoques",
    scope=PUBLIC_SCOPE,
    tags=["domain:estoques", "shape:aggregate"],
    routing=routing_metadata(
        examples=[
            "Qual o saldo total em estoque em 2025?",
            "Quais materiais tem maior saldo em estoque?",
            "Quais materiais tiveram mais saidas em maio de 2025?",
            "Qual e o ranking dos materiais com maior movimentacao?",
        ],
        hints=[
            "estoque",
            "saldo total",
            "ranking de materiais",
            "almoxarifado",
            "entrada",
            "saida por material",
            "movimentacao por periodo",
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
    Calcula totais, contagens e rankings sobre saldos e movimentacoes de estoque.

    Use esta tool quando a pergunta pedir total, contagem, comparacao ou
    ranking de saldos, entradas, saidas ou movimentacao de materiais em estoque.
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

    use_movimentacoes = _should_use_movimentacoes(params)
    with session_manager.get_session() as session:
        if use_movimentacoes:
            registros = load_filtered_estoque_movimentacoes(session, params.filtros)
        else:
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
        group_key_getters=(MOVEMENT_GROUP_FIELD_GETTERS if use_movimentacoes else GROUP_FIELD_GETTERS),
        metric_getters=(MOVEMENT_METRIC_FIELD_GETTERS if use_movimentacoes else METRIC_FIELD_GETTERS),
        serialize_metric=_metric_to_json,
    )
    group_key_getters = MOVEMENT_GROUP_FIELD_GETTERS if use_movimentacoes else GROUP_FIELD_GETTERS
    metric_getters = MOVEMENT_METRIC_FIELD_GETTERS if use_movimentacoes else METRIC_FIELD_GETTERS
    companion_metrics = _build_companion_metrics(
        registros,
        execution_rows=execution.rows,
        agrupar_por=params.agrupar_por,
        metrica=params.metrica,
        group_key_getters=group_key_getters,
        metric_getters=metric_getters,
    )
    suggestion = (
        (
            "Nenhuma movimentacao de estoque encontrada com os filtros."
            if use_movimentacoes
            else "Nenhum material de estoque encontrado com os filtros."
        )
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
        project_group=(
            (
                lambda group_value, metric_value, agrupar_por, metrica: _project_estoque_group(
                    group_value,
                    metric_value,
                    agrupar_por,
                    metrica,
                    companion_metrics=companion_metrics,
                )
            )
            if params.agrupar_por is not None
            else None
        ),
        agrupar_por=params.agrupar_por,
        metrica=params.metrica if params.agrupar_por is not None else None,
    )
