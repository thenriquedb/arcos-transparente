"""Tool publica para agregacoes do quadro de pessoal."""

from __future__ import annotations

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
from database.models import QuadroPessoal

from .agregar_quadro_pessoal_schema import (
    AgregarQuadroPessoalMetadata,
    AgregarQuadroPessoalParams,
    AgregarQuadroPessoalResponse,
)
from .consultar_quadro_pessoal_query import load_filtered_quadro_pessoal


def _metric(registros: list[QuadroPessoal], metrica: str) -> int:
    if metrica == "contagem":
        return len(registros)
    if metrica == "soma_vagas_criadas":
        return sum(registro.vagas_criadas or 0 for registro in registros)
    if metrica == "soma_vagas_preenchidas":
        return sum(registro.vagas_preenchidas or 0 for registro in registros)
    return sum((registro.vagas_criadas or 0) - (registro.vagas_preenchidas or 0) for registro in registros)


GROUP_FIELD_GETTERS = {
    "origem": lambda registro: registro.origem,
    "regime": lambda registro: registro.regime_contratacao,
    "mes": lambda registro: registro.competencia_referencia.month,
}
METRIC_FIELD_GETTERS = {
    "soma_vagas_criadas": lambda registro: registro.vagas_criadas or 0,
    "soma_vagas_preenchidas": lambda registro: registro.vagas_preenchidas or 0,
    "saldo_vagas": lambda registro: (registro.vagas_criadas or 0) - (registro.vagas_preenchidas or 0),
}


def _project_quadro_pessoal_group(
    group_value: Any,
    metric_value: Any,
    agrupar_por: str,
    metrica: str,
) -> dict[str, Any]:
    return {agrupar_por: group_value, metrica: metric_value}


@register(
    name=ToolName.AGREGAR_QUADRO_PESSOAL,
    scope=PUBLIC_SCOPE,
    tags=["domain:quadro_pessoal", "shape:aggregate"],
    routing=routing_metadata(
        examples=[
            "Quantas vagas preenchidas por regime no quadro pessoal?",
            "Qual origem tem mais vagas ocupadas?",
        ],
        hints=[
            "quadro de pessoal",
            "vaga",
            "regime",
            "contagem",
            "ranking",
        ],
    ),
)
def agregar_quadro_pessoal(
    filtros: dict[str, Any] | None = None,
    agrupar_por: str | None = None,
    metrica: str = "soma_vagas_preenchidas",
    ordenar_por: str = "metrica",
    ordem: str = "desc",
    limite: int = 10,
) -> dict[str, Any]:
    """
    Calcula totais e rankings sobre vagas do quadro de pessoal.

    Use esta tool quando a pergunta pedir quantas vagas existem, quantas foram
    preenchidas ou qual regime, origem ou mes concentra mais vagas.
    NAO use para listar registros individuais do quadro de pessoal; para isso use
    `consultar_quadro_pessoal`.
    NAO use para contar pessoas da folha ou listar servidores; para isso use
    `agregar_servidores` ou `consultar_servidores`.

    Args:
        filtros: Objeto com filtros opcionais. Campos aceitos: `origem`, `ano`,
            `mes` e `regime`.
        agrupar_por: Campo opcional de agrupamento. Aceita `origem`, `regime`
            ou `mes`. Se nao for informado, a tool retorna um `valor_total`.
        metrica: Metrica calculada. Aceita `contagem`, `soma_vagas_criadas`,
            `soma_vagas_preenchidas` ou `saldo_vagas`.
        ordenar_por: Aceita `metrica` ou o mesmo valor usado em `agrupar_por`.
        ordem: Direcao da ordenacao: `asc` ou `desc`.
        limite: Quantidade maxima de grupos retornados. Inteiro de 1 a 100.

    Returns:
        dict com:
        - `total_grupos`: total de grupos encontrados.
        - `resultados`: lista de grupos; cada item traz o campo de agrupamento e a
          metrica calculada.
        - `metadata`: filtros aplicados e configuracao da agregacao.
        - `valor_total`: valor agregado quando `agrupar_por` nao for informado.
        - `mensagem`: aviso quando so parte dos grupos for exibida.
        - `sugestao`: dica quando nenhum registro corresponder aos filtros.
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
        schema_type=AgregarQuadroPessoalParams,
        on_error=lambda exc: AgregarQuadroPessoalResponse(
            total_grupos=0,
            resultados=[],
            metadata=AgregarQuadroPessoalMetadata(
                metrica="soma_vagas_preenchidas",
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
        registros = load_filtered_quadro_pessoal(session, params.filtros)
        empty_suggestion = resolve_empty_result_suggestion(
            session,
            domain_key="quadro_pessoal",
            filters=params.filtros,
            default_suggestion="Nenhum registro de quadro de pessoal encontrado.",
        )

    metadata = AgregarQuadroPessoalMetadata(
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
        serialize_metric=lambda value: value,
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
        response_type=AgregarQuadroPessoalResponse,
        metadata=metadata,
        execution=AggregateExecutionResult(
            total_grupos=execution.total_grupos,
            rows=execution.rows,
            valor_total=execution.valor_total,
            source_count=execution.source_count,
            suggestion=suggestion,
        ),
        project_group=(_project_quadro_pessoal_group if params.agrupar_por is not None else None),
        agrupar_por=params.agrupar_por,
        metrica=params.metrica if params.agrupar_por is not None else None,
    )
