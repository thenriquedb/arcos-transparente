"""Tool publica para agregacoes do relatorio `despesas-por-funcao`."""

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
from database.models import DespesaPorFuncao

from .agregar_despesas_por_funcao_schema import (
    AgregarDespesasPorFuncaoMetadata,
    AgregarDespesasPorFuncaoParams,
    AgregarDespesasPorFuncaoResponse,
)
from .consultar_despesas_por_funcao_query import load_filtered_despesas_por_funcao


def _metric(registros: list[DespesaPorFuncao], metrica: str) -> Decimal | int:
    if metrica == "contagem":
        return len(registros)
    field_by_metric = {
        "soma_dotacao_inicial": "dotacao_inicial",
        "soma_creditos_adicionais": "creditos_adicionais",
        "soma_dotacao_atualizada": "dotacao_atualizada",
        "soma_valor_empenhado": "valor_empenhado",
        "soma_valor_em_liquidacao": "valor_em_liquidacao",
        "soma_valor_liquidado": "valor_liquidado",
        "soma_valor_pago": "valor_pago",
    }
    field = field_by_metric[metrica]
    return sum((getattr(registro, field) or Decimal("0")) for registro in registros)


def _metric_to_json(value: Decimal | int) -> float | int:
    if isinstance(value, Decimal):
        return float(value)
    return value


GROUP_FIELD_GETTERS = {
    "origem": lambda registro: registro.origem,
    "ano": lambda registro: registro.exercicio,
    "unidade_gestora": lambda registro: registro.unidade_gestora,
    "funcao": lambda registro: registro.funcao,
}
METRIC_FIELD_GETTERS = {
    "soma_dotacao_inicial": lambda registro: registro.dotacao_inicial or Decimal("0"),
    "soma_creditos_adicionais": lambda registro: registro.creditos_adicionais or Decimal("0"),
    "soma_dotacao_atualizada": lambda registro: registro.dotacao_atualizada or Decimal("0"),
    "soma_valor_empenhado": lambda registro: registro.valor_empenhado or Decimal("0"),
    "soma_valor_em_liquidacao": lambda registro: registro.valor_em_liquidacao or Decimal("0"),
    "soma_valor_liquidado": lambda registro: registro.valor_liquidado or Decimal("0"),
    "soma_valor_pago": lambda registro: registro.valor_pago or Decimal("0"),
}


def _project_despesas_por_funcao_group(
    group_value: Any,
    metric_value: Any,
    agrupar_por: str,
    metrica: str,
) -> dict[str, Any]:
    return {agrupar_por: group_value, metrica: metric_value}


@register(
    name="agregar_despesas_por_funcao",
    scope=PUBLIC_SCOPE,
    tags=["domain:despesas_por_funcao", "shape:aggregate"],
    routing=routing_metadata(
        examples=[
            "Qual foi o total pago no relatorio de despesas por funcao em 2025?",
            "Quais funcoes tiveram maior valor pago no relatorio de despesas por funcao?",
            "Qual foi o total investido em obras e pavimentacao em 2025?",
        ],
        hints=[
            "despesas por funcao",
            "ranking por funcao",
            "dotacao atualizada",
            "creditos adicionais",
            "valor pago",
            "urbanismo",
        ],
    ),
)
def agregar_despesas_por_funcao(
    filtros: dict[str, Any] | None = None,
    agrupar_por: str | None = None,
    metrica: str = "soma_valor_pago",
    ordenar_por: str = "metrica",
    ordem: str = "desc",
    limite: int = 10,
) -> dict[str, Any]:
    """
    Calcula totais, comparacoes e rankings sobre o relatorio `despesas-por-funcao`.

    Use esta tool quando a pergunta pedir total, comparacao, contagem ou ranking
    sobre as linhas agregadas do relatorio `despesas-por-funcao`.
    NAO use para perguntas amplas como "qual foi o gasto com saude em 2025?"
    quando o usuario nao pediu explicitamente apenas um total. Nesses casos,
    use `consultar_despesas_por_funcao` e mostre os estagios
    `valor_empenhado`, `valor_em_liquidacao`, `valor_liquidado` e `valor_pago`.
    Se o usuario ja informar um ano, como "em 2025", esse recorte ja basta;
    nao peca dia e mes para responder.
    NAO use para listar linhas individuais do relatorio; para isso use
    `consultar_despesas_por_funcao`.
    NAO use para planejamento mensal por programa ou acao; para isso use
    `agregar_planejamento`.
    NAO use para somar documentos de despesa efetivamente emitidos; para isso use
    `agregar_despesas`.
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
        schema_type=AgregarDespesasPorFuncaoParams,
        on_error=lambda exc: AgregarDespesasPorFuncaoResponse(
            total_grupos=0,
            resultados=[],
            metadata=AgregarDespesasPorFuncaoMetadata(
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
        registros = load_filtered_despesas_por_funcao(session, params.filtros)

    metadata = AgregarDespesasPorFuncaoMetadata(
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
        "Nenhum registro de despesas por funcao encontrado com os filtros."
        if (
            (params.agrupar_por is None and execution.source_count == 0)
            or (params.agrupar_por is not None and not execution.rows)
        )
        else None
    )
    return build_aggregate_response(
        response_type=AgregarDespesasPorFuncaoResponse,
        metadata=metadata,
        execution=AggregateExecutionResult(
            total_grupos=execution.total_grupos,
            rows=execution.rows,
            valor_total=execution.valor_total,
            source_count=execution.source_count,
            suggestion=suggestion,
        ),
        project_group=(_project_despesas_por_funcao_group if params.agrupar_por is not None else None),
        agrupar_por=params.agrupar_por,
        metrica=params.metrica if params.agrupar_por is not None else None,
    )
