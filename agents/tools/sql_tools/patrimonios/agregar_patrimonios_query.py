"""Tool publica para agregacoes de patrimonio."""

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
from database.models import Patrimonio

from .agregar_patrimonios_schema import (
    AgregarPatrimoniosMetadata,
    AgregarPatrimoniosParams,
    AgregarPatrimoniosResponse,
)
from .consultar_patrimonios_query import load_filtered_patrimonios


def _metric(registros: list[Patrimonio], metrica: str) -> Decimal | int:
    if metrica == "contagem":
        return len(registros)
    field = {
        "soma_valor_atualizado": "valor_atualizado",
        "soma_valor_ingresso": "valor_ingresso",
    }[metrica]
    return sum((getattr(registro, field) or Decimal(0)) for registro in registros)


def _metric_to_json(value: Decimal | int) -> float | int:
    return float(value) if isinstance(value, Decimal) else value


GROUP_FIELD_GETTERS = {
    "unidade_responsavel": lambda registro: registro.unidade_gestora,
    "localizacao": lambda registro: registro.localizacao,
    "status": lambda registro: registro.status,
    "situacao": lambda registro: registro.situacao_bem,
    "tipo_ingresso": lambda registro: registro.tipo_ingresso,
    "classificacao": lambda registro: registro.classificacao,
}
METRIC_FIELD_GETTERS = {
    "soma_valor_atualizado": lambda registro: registro.valor_atualizado or Decimal(0),
    "soma_valor_ingresso": lambda registro: registro.valor_ingresso or Decimal(0),
}


def _project_patrimonio_group(
    group_value: Any,
    metric_value: Any,
    agrupar_por: str,
    metrica: str,
) -> dict[str, Any]:
    return {agrupar_por: group_value, metrica: metric_value}


@register(
    name=ToolName.AGREGAR_PATRIMONIOS,
    scope=PUBLIC_SCOPE,
    tags=["domain:patrimonios", "shape:aggregate"],
    routing=routing_metadata(
        examples=[
            "Qual o valor total do patrimonio em 2025?",
            "Qual localizacao concentra mais bens?",
        ],
        hints=[
            "patrimonio",
            "valor total",
            "contagem",
            "ranking",
            "localizacao",
        ],
    ),
)
def agregar_patrimonios(
    filtros: dict[str, Any] | None = None,
    agrupar_por: str | None = None,
    metrica: str = "contagem",
    ordenar_por: str = "metrica",
    ordem: str = "desc",
    limite: int = 10,
) -> dict[str, Any]:
    """
    Calcula totais, somas e rankings sobre bens patrimoniais.

    Use esta tool quando a pergunta pedir quantos bens existem, qual localizacao
    concentra mais itens ou qual o valor total de ingresso ou atualizado do
    patrimonio.
    NAO use para listar bens individuais; para isso use `consultar_patrimonios`.
    NAO use para contratos ou licitacoes de aquisicao; para isso use
    `agregar_contratos` ou `agregar_licitacoes`.

    Args:
        filtros: Objeto com filtros opcionais. Campos aceitos:
            `unidade_responsavel`, `placa`, `descricao`, `classificacao`,
            `localizacao`, `status`, `situacao`, `tipo_ingresso`,
            `data_aquisicao_inicio` e `data_aquisicao_fim`. Datas em
            `YYYY-MM-DD`.
        agrupar_por: Campo opcional de agrupamento. Aceita
            `unidade_responsavel`, `localizacao`, `status`, `situacao`,
            `tipo_ingresso` ou `classificacao`. Se nao for informado, a tool
            retorna um `valor_total`.
        metrica: Metrica calculada. Aceita `contagem`, `soma_valor_atualizado`
            ou `soma_valor_ingresso`.
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
        - `sugestao`: dica quando nenhum bem corresponder aos filtros.
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
        schema_type=AgregarPatrimoniosParams,
        on_error=lambda exc: AgregarPatrimoniosResponse(
            total_grupos=0,
            resultados=[],
            metadata=AgregarPatrimoniosMetadata(
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

    with session_manager.get_session() as session:
        registros = load_filtered_patrimonios(session, params.filtros)
        empty_suggestion = resolve_empty_result_suggestion(
            session,
            domain_key="patrimonios",
            filters=params.filtros,
            default_suggestion="Nenhum bem patrimonial encontrado com os filtros.",
        )

    metadata = AgregarPatrimoniosMetadata(
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
        response_type=AgregarPatrimoniosResponse,
        metadata=metadata,
        execution=AggregateExecutionResult(
            total_grupos=execution.total_grupos,
            rows=execution.rows,
            valor_total=execution.valor_total,
            source_count=execution.source_count,
            suggestion=suggestion,
        ),
        project_group=(_project_patrimonio_group if params.agrupar_por is not None else None),
        agrupar_por=params.agrupar_por,
        metrica=params.metrica if params.agrupar_por is not None else None,
    )
