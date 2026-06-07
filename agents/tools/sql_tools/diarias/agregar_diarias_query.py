"""Tool publica para agregacoes de diarias."""

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
from database.models import DespesaDocumento

from .agregar_diarias_schema import (
    AgregarDiariasMetadata,
    AgregarDiariasParams,
    AgregarDiariasResponse,
)
from .consultar_diarias_query import load_filtered_diarias


def _decimal_to_json(value: Decimal) -> float:
    return float(value)


def _metric(registros: list[DespesaDocumento], metrica: str) -> Decimal | int:
    if metrica == "contagem":
        return len(registros)
    field_by_metric = {
        "soma_valor_empenhado": "valor_empenhado",
        "soma_valor_liquidado": "valor_liquidado",
        "soma_valor_pago": "valor_pago",
        "soma_valor_anulado": "valor_anulado",
    }
    field = field_by_metric[metrica]
    return sum((getattr(registro, field) or Decimal("0")) for registro in registros)


def _metric_to_json(value: Decimal | int) -> float | int:
    if isinstance(value, Decimal):
        return _decimal_to_json(value)
    return value


GROUP_FIELD_GETTERS = {
    "origem": lambda registro: registro.origem,
    "ano": lambda registro: registro.exercicio,
    "beneficiario": lambda registro: registro.credor,
    "unidade_gestora": lambda registro: registro.unidade_gestora,
}
METRIC_FIELD_GETTERS = {
    "soma_valor_empenhado": lambda registro: registro.valor_empenhado or Decimal("0"),
    "soma_valor_liquidado": lambda registro: registro.valor_liquidado or Decimal("0"),
    "soma_valor_pago": lambda registro: registro.valor_pago or Decimal("0"),
    "soma_valor_anulado": lambda registro: registro.valor_anulado or Decimal("0"),
}


def _project_diaria_group(
    group_value: Any,
    metric_value: Any,
    agrupar_por: str,
    metrica: str,
) -> dict[str, Any]:
    return {agrupar_por: group_value, metrica: metric_value}


@register(
    name="agregar_diarias",
    scope=PUBLIC_SCOPE,
    tags=["domain:diarias", "shape:aggregate"],
    routing=routing_metadata(
        examples=[
            "Quanto foi pago em diarias em 2025?",
            "Quais colaboradores mais gastaram com diarias?",
        ],
        hints=[
            "diaria",
            "total pago",
            "ranking",
            "beneficiario",
            "viagem",
        ],
    ),
)
def agregar_diarias(
    filtros: dict[str, Any] | None = None,
    agrupar_por: str | None = None,
    metrica: str = "soma_valor_pago",
    ordenar_por: str = "metrica",
    ordem: str = "desc",
    limite: int = 10,
) -> dict[str, Any]:
    """
    Calcula totais, contagens e rankings sobre registros consolidados de diarias.

    Use esta tool quando a pergunta pedir total pago, total empenhado,
    quantidade de beneficiarios ou rankings de diarias por beneficiario, origem
    ou unidade gestora.
    Se a pergunta usar linguagem ampla de gasto e houver interesse em ver os
    registros que compoem o valor, consulte primeiro `consultar_diarias` e use
    esta tool apenas como resumo complementar ou quando o usuario pedir
    explicitamente total, ranking, contagem ou comparacao.
    NAO use para listar registros individuais; para isso use
    `consultar_diarias`.
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
        schema_type=AgregarDiariasParams,
        on_error=lambda exc: AgregarDiariasResponse(
            total_grupos=0,
            resultados=[],
            metadata=AgregarDiariasMetadata(
                metrica="soma_valor_pago",
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
        registros = load_filtered_diarias(session, params.filtros)

    metadata = AgregarDiariasMetadata(
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
        "Nenhuma diaria encontrada com os filtros."
        if (
            (params.agrupar_por is None and execution.source_count == 0)
            or (params.agrupar_por is not None and not execution.rows)
        )
        else None
    )
    return build_aggregate_response(
        response_type=AgregarDiariasResponse,
        metadata=metadata,
        execution=AggregateExecutionResult(
            total_grupos=execution.total_grupos,
            rows=execution.rows,
            valor_total=execution.valor_total,
            source_count=execution.source_count,
            suggestion=suggestion,
        ),
        project_group=_project_diaria_group if params.agrupar_por is not None else None,
        agrupar_por=params.agrupar_por,
        metrica=params.metrica if params.agrupar_por is not None else None,
    )
