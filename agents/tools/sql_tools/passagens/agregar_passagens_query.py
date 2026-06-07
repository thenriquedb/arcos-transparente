"""Tool publica para agregacoes de passagens."""

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

from .agregar_passagens_schema import (
    AgregarPassagensMetadata,
    AgregarPassagensParams,
    AgregarPassagensResponse,
)
from .consultar_passagens_query import load_filtered_passagens


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
    "categoria": lambda registro: registro.categoria_documento,
}
METRIC_FIELD_GETTERS = {
    "soma_valor_empenhado": lambda registro: registro.valor_empenhado or Decimal("0"),
    "soma_valor_liquidado": lambda registro: registro.valor_liquidado or Decimal("0"),
    "soma_valor_pago": lambda registro: registro.valor_pago or Decimal("0"),
    "soma_valor_anulado": lambda registro: registro.valor_anulado or Decimal("0"),
}


def _project_passagem_group(
    group_value: Any,
    metric_value: Any,
    agrupar_por: str,
    metrica: str,
) -> dict[str, Any]:
    return {agrupar_por: group_value, metrica: metric_value}


@register(
    name="agregar_passagens",
    scope=PUBLIC_SCOPE,
    tags=["domain:passagens", "shape:aggregate"],
    routing=routing_metadata(
        examples=[
            "Quanto foi pago em passagens em 2026?",
            "Quais beneficiarios receberam mais passagens?",
        ],
        hints=[
            "passagem",
            "total pago",
            "ranking",
            "beneficiario",
            "locomocao",
        ],
    ),
)
def agregar_passagens(
    filtros: dict[str, Any] | None = None,
    agrupar_por: str | None = None,
    metrica: str = "soma_valor_pago",
    ordenar_por: str = "metrica",
    ordem: str = "desc",
    limite: int = 10,
) -> dict[str, Any]:
    """
    Calcula totais, contagens e rankings sobre registros consolidados de passagens.

    Use esta tool quando a pergunta pedir total pago, total empenhado,
    quantidade de beneficiarios ou rankings de passagens por beneficiario,
    origem, unidade gestora ou categoria.
    Se a pergunta usar linguagem ampla de gasto e houver interesse em ver os
    registros que compoem o valor, consulte primeiro `consultar_passagens` e
    use esta tool apenas como resumo complementar ou quando o usuario pedir
    explicitamente total, ranking, contagem ou comparacao.
    NAO use para listar registros individuais; para isso use
    `consultar_passagens`.
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
        schema_type=AgregarPassagensParams,
        on_error=lambda exc: AgregarPassagensResponse(
            total_grupos=0,
            resultados=[],
            metadata=AgregarPassagensMetadata(
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
        registros = load_filtered_passagens(session, params.filtros)

    metadata = AgregarPassagensMetadata(
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
        "Nenhuma passagem encontrada com os filtros."
        if (
            (params.agrupar_por is None and execution.source_count == 0)
            or (params.agrupar_por is not None and not execution.rows)
        )
        else None
    )
    return build_aggregate_response(
        response_type=AgregarPassagensResponse,
        metadata=metadata,
        execution=AggregateExecutionResult(
            total_grupos=execution.total_grupos,
            rows=execution.rows,
            valor_total=execution.valor_total,
            source_count=execution.source_count,
            suggestion=suggestion,
        ),
        project_group=(
            _project_passagem_group if params.agrupar_por is not None else None
        ),
        agrupar_por=params.agrupar_por,
        metrica=params.metrica if params.agrupar_por is not None else None,
    )
