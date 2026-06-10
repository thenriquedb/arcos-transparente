"""Tool publica para agregacoes de transferencias financeiras."""

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

from .agregar_transferencias_financeiras_schema import (
    AgregarTransferenciasFinanceirasMetadata,
    AgregarTransferenciasFinanceirasParams,
    AgregarTransferenciasFinanceirasResponse,
)
from .consultar_transferencias_financeiras_query import (
    load_filtered_transferencias_financeiras,
)


def _metric(registros: list[dict[str, Any]], metrica: str) -> Decimal | int:
    if metrica == "contagem":
        return len(registros)
    if metrica == "soma_programacao_inicial":
        return sum(Decimal(str(registro.get("programacao_inicial") or 0)) for registro in registros)
    return sum(Decimal(str(registro.get("valor") or 0)) for registro in registros)


def _metric_to_json(value: Decimal | int) -> float | int:
    if isinstance(value, Decimal):
        return float(value)
    return value


GROUP_FIELD_GETTERS = {
    "tipo_registro": lambda registro: registro.get("tipo_registro"),
    "ano": lambda registro: registro.get("ano"),
    "unidade_concessora": lambda registro: registro.get("unidade_concessora"),
    "unidade_recebedora": lambda registro: registro.get("unidade_recebedora"),
    "tipo_movimento": lambda registro: registro.get("tipo_movimento"),
    "finalidade": lambda registro: registro.get("finalidade"),
    "fonte_recurso": lambda registro: registro.get("fonte_recurso"),
    "autor": lambda registro: registro.get("autor"),
    "funcao": lambda registro: registro.get("funcao"),
    "tipo_emenda": lambda registro: registro.get("tipo_emenda"),
}
METRIC_FIELD_GETTERS = {
    "soma_valor": lambda registro: Decimal(str(registro.get("valor") or 0)),
    "soma_programacao_inicial": lambda registro: Decimal(str(registro.get("programacao_inicial") or 0)),
}


def _project_transferencia_financeira_group(
    group_value: Any,
    metric_value: Any,
    agrupar_por: str,
    metrica: str,
) -> dict[str, Any]:
    return {agrupar_por: group_value, metrica: metric_value}


@register(
    name="agregar_transferencias_financeiras",
    scope=PUBLIC_SCOPE,
    tags=["domain:transferencias_financeiras", "shape:aggregate"],
    routing=routing_metadata(
        examples=[
            "Qual o total recebido em emendas parlamentares?",
            "Qual unidade recebeu mais transferencias?",
            "Quantas emendas foram do Nikolas Ferreira em 2025?",
            "Quanto o Cleitinho enviou de emendas para a prefeitura em 2025?",
        ],
        hints=[
            "transferencia financeira",
            "repasse",
            "emenda parlamentar",
            "ranking",
            "total",
            "contagem por autor",
            "contagem por funcao",
            "total por ano",
            "valor por autor",
        ],
    ),
)
def agregar_transferencias_financeiras(
    filtros: dict[str, Any] | None = None,
    agrupar_por: str | None = None,
    metrica: str = "soma_valor",
    ordenar_por: str = "metrica",
    ordem: str = "desc",
    limite: int = 10,
) -> dict[str, Any]:
    """
    Calcula totais, contagens e rankings sobre transferencias e emendas.

    Use esta tool quando a pergunta pedir total transferido, total recebido,
    quantidade de registros ou rankings por unidade, tipo de movimento, autor,
    funcao, ano ou tipo de emenda.
    Para perguntas como "quantas emendas foram do autor X?" ou
    "quanto o Cleitinho enviou de emendas em 2025?", preserve o filtro de
    `autor` e, quando houver ano na pergunta, preserve tambem `ano`.
    Se o autor estiver claro e nao houver ano explicito, a consulta pode cobrir
    todos os anos disponiveis sem pedir recorte temporal adicional.
    NAO use para listar registros individuais; para isso use
    `consultar_transferencias_financeiras`.
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
        schema_type=AgregarTransferenciasFinanceirasParams,
        on_error=lambda exc: AgregarTransferenciasFinanceirasResponse(
            total_grupos=0,
            resultados=[],
            metadata=AgregarTransferenciasFinanceirasMetadata(
                metrica="soma_valor",
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
        registros = load_filtered_transferencias_financeiras(session, params.filtros)

    metadata = AgregarTransferenciasFinanceirasMetadata(
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
        "Nenhum registro de transferencias financeiras encontrado com os filtros."
        if (
            (params.agrupar_por is None and execution.source_count == 0)
            or (params.agrupar_por is not None and not execution.rows)
        )
        else None
    )
    return build_aggregate_response(
        response_type=AgregarTransferenciasFinanceirasResponse,
        metadata=metadata,
        execution=AggregateExecutionResult(
            total_grupos=execution.total_grupos,
            rows=execution.rows,
            valor_total=execution.valor_total,
            source_count=execution.source_count,
            suggestion=suggestion,
        ),
        project_group=(_project_transferencia_financeira_group if params.agrupar_por is not None else None),
        agrupar_por=params.agrupar_por,
        metrica=params.metrica if params.agrupar_por is not None else None,
    )
