"""Tool publica para agregacoes de planejamento."""

from __future__ import annotations

from typing import Any

from agents.tools.registry import PUBLIC_SCOPE, register, routing_metadata
from agents.tools.sql_tools.shared.aggregate import (
    AggregateExecutionResult,
    build_aggregate_response,
    execute_collection_aggregate,
)
from agents.tools.sql_tools.shared.validation import validate_tool_params
from database import session as session_manager

from .agregar_planejamento_schema import (
    AgregacaoPlanejamentoItem,
    AgregarPlanejamentoMetadata,
    AgregarPlanejamentoParams,
    AgregarPlanejamentoResponse,
)
from .shared.querying import (
    GROUP_FIELD_GETTERS,
    load_filtered_planejamentos,
    METRIC_FIELD_GETTERS,
    metric_to_json,
)


@register(
    name="agregar_planejamento",
    scope=PUBLIC_SCOPE,
    tags=["domain:planejamento", "shape:aggregate"],
    routing=routing_metadata(
        examples=[
            "Quanto foi investido na saude em 2026?",
            "Quais acoes tiveram maior orcamento em 2025?",
        ],
        hints=[
            "planejamento",
            "orcamento",
            "valor pago",
            "ranking",
            "acao",
        ],
    ),
)
def agregar_planejamento(
    filtros: dict[str, Any] | None = None,
    agrupar_por: str | None = None,
    metrica: str = "soma_orcamento_atualizado",
    ordenar_por: str = "metrica",
    ordem: str = "desc",
    limite: int = 10,
) -> dict[str, Any]:
    """
    Calcula totais, comparacoes e rankings sobre dados de planejamento.

    Use esta tool quando a pergunta pedir quanto foi orcado, comprometido,
    confirmado, pago ou cancelado dentro do planejamento, ou quando pedir
    comparacoes por area, programa, acao, grupo de gasto ou fonte de recurso.
    NAO use para o relatorio agregado `despesas-por-funcao`; para isso use
    `agregar_despesas_por_funcao`.
    NAO use para listar linhas individuais do planejamento; para isso use
    `consultar_planejamento`.
    NAO use para somar documentos de despesa efetivamente emitidos; para isso use
    `agregar_despesas`.

    O filtro `origem` suporta ao menos `saude` e `prefeitura`.
    Se `origem` nao for informado, o padrao continua sendo `saude`.

    Args:
        filtros: Objeto com filtros opcionais. Campos aceitos: `origem`, `ano`,
            `mes`, `mes_inicio`, `mes_fim`, `entidade`, `area`, `subarea`,
            `programa`, `acao`, `grupo_de_gasto`, `categoria_de_gasto`,
            `fonte_recurso`, `valor_pago_min` e `valor_pago_max`. `mes`,
            `mes_inicio` e `mes_fim` aceitam numero de 1 a 12 ou nome do mes.
        agrupar_por: Campo opcional de agrupamento. Aceita `mes`, `area`,
            `subarea`, `programa`, `acao`, `grupo_de_gasto`,
            `categoria_de_gasto` ou `fonte_recurso`. Se nao for informado,
            a tool retorna um `valor_total`.
        metrica: Metrica calculada. Aceita `contagem`, `soma_orcamento_inicial`,
            `soma_orcamento_atualizado`, `soma_valor_comprometido`,
            `soma_valor_confirmado`, `soma_valor_pago` ou
            `soma_valor_cancelado`.
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
        schema_type=AgregarPlanejamentoParams,
        on_error=lambda exc: AgregarPlanejamentoResponse(
            total_grupos=0,
            resultados=[],
            metadata=AgregarPlanejamentoMetadata(
                metrica="soma_orcamento_atualizado",
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
        registros = load_filtered_planejamentos(session, params.filtros)

    metadata = AgregarPlanejamentoMetadata(
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
        serialize_metric=metric_to_json,
    )
    suggestion = (
        "Nenhum registro de planejamento encontrado com os filtros."
        if (
            (params.agrupar_por is None and execution.source_count == 0)
            or (params.agrupar_por is not None and not execution.rows)
        )
        else None
    )
    return build_aggregate_response(
        response_type=AgregarPlanejamentoResponse,
        metadata=metadata,
        execution=AggregateExecutionResult(
            total_grupos=execution.total_grupos,
            rows=execution.rows,
            valor_total=execution.valor_total,
            source_count=execution.source_count,
            suggestion=suggestion,
        ),
        item_model=(AgregacaoPlanejamentoItem if params.agrupar_por is not None else None),
        agrupar_por=params.agrupar_por,
        metrica=params.metrica if params.agrupar_por is not None else None,
    )
