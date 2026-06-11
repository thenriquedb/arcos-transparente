"""Tool publica para consultas amplas de planejamento."""

from __future__ import annotations

from typing import Any

from agents.tools.names import ToolName
from agents.tools.registry import PUBLIC_SCOPE, register, routing_metadata
from agents.tools.sql_tools.shared.lookup import (
    LookupExecutionResult,
    build_lookup_response,
    execute_collection_lookup,
)
from agents.tools.sql_tools.shared.validation import validate_tool_params
from database import session as session_manager

from .consultar_planejamento_schema import (
    ConsultarPlanejamentoMetadata,
    ConsultarPlanejamentoParams,
    ConsultarPlanejamentoResponse,
)
from .shared.filters import ALLOWED_PLANNING_FIELDS
from .shared.querying import (
    SORT_FIELD_GETTERS,
    load_filtered_planejamentos,
)
from .shared.runtime import project_planejamento_fields


@register(
    name=ToolName.CONSULTAR_PLANEJAMENTO,
    scope=PUBLIC_SCOPE,
    tags=["domain:planejamento", "shape:lookup"],
    routing=routing_metadata(
        examples=[
            "Liste o planejamento da saude em 2025.",
            "Quais programas tiveram valor pago na prefeitura?",
        ],
        hints=[
            "planejamento",
            "orcamento",
            "programa",
            "acao",
            "valor pago",
        ],
    ),
)
def consultar_planejamento(
    filtros: dict[str, Any] | None = None,
    ordenar_por: str = "mes_num",
    ordem: str = "asc",
    limite: int = 10,
    offset: int = 0,
    campos: list[str] | None = None,
) -> dict[str, Any]:
    """
    Lista linhas do planejamento orcamentario por origem, area, programa, acao e mes.

    Use esta tool quando a pergunta pedir o planejamento, o orcamento ou os valores
    previstos, comprometidos, confirmados, pagos ou cancelados dentro da estrutura
    orcamentaria.
    NAO use para o relatorio agregado `despesas-por-funcao`; para isso use
    `consultar_despesas_por_funcao`.
    NAO use para empenhos, restos a pagar ou documentos de despesa efetivamente
    emitidos; para isso use `consultar_despesas`.
    NAO use para totais, comparacoes ou rankings agregados; para isso use
    `agregar_planejamento`.

    O filtro `origem` suporta ao menos `saude` e `prefeitura`.
    Se `origem` nao for informado, o será ambos.

    Args:
        filtros: Objeto com filtros opcionais. Campos aceitos: `origem`, `ano`,
            `mes`, `mes_inicio`, `mes_fim`, `entidade`, `area`, `subarea`,
            `programa`, `acao`, `grupo_de_gasto`, `categoria_de_gasto`,
            `fonte_recurso`, `valor_pago_min` e `valor_pago_max`. `mes`,
            `mes_inicio` e `mes_fim` aceitam numero de 1 a 12 ou nome do mes.
        ordenar_por: Campo de ordenacao. Aceita `ano`, `mes_num`, `area`,
            `subarea`, `programa`, `acao`, `grupo_de_gasto`,
            `orcamento_inicial`, `orcamento_atualizado`, `valor_comprometido`,
            `valor_confirmado`, `valor_pago` ou `valor_cancelado`.
        ordem: Direcao da ordenacao: `asc` ou `desc`.
        limite: Tamanho da pagina. Inteiro de 1 a 100.
        offset: Deslocamento da pagina. Inteiro maior ou igual a 0.
        campos: Lista opcional com qualquer subconjunto dos campos publicos de
            planejamento retornados em cada item.

    Returns:
        dict com:
        - `total`: total de linhas encontradas antes da paginacao.
        - `resultados`: lista de linhas de planejamento; cada item pode incluir
          `id`, `origem`, `ano`, `mes`, `mes_num`, `unidade_gestora`, `orgao`,
          `unidade`, `area`, `subarea`, `programa`, `tipo_acao`, `acao`,
          `fonte_recurso`, `esfera`, `categoria_de_gasto`, `grupo_de_gasto`,
          `orcamento_inicial`, `reforcos_no_orcamento`, `orcamento_atualizado`,
          `valor_comprometido`, `valor_confirmado`, `valor_pago` e
          `valor_cancelado`.
        - `metadata`: filtros aplicados, ordenacao, paginacao e campos pedidos.
        - `mensagem`: aviso quando a resposta estiver paginada.
        - `sugestao`: dica quando nenhum registro for encontrado.
    """
    validated = validate_tool_params(
        {
            "filtros": filtros,
            "ordenar_por": ordenar_por,
            "ordem": ordem,
            "limite": limite,
            "offset": offset,
            "campos": campos,
        },
        schema_type=ConsultarPlanejamentoParams,
        on_error=lambda exc: ConsultarPlanejamentoResponse(
            total=0,
            resultados=[],
            metadata=ConsultarPlanejamentoMetadata(
                ordenar_por="mes_num",
                ordem="asc",
                limite=10,
                offset=0,
            ),
            mensagem=f"Parametros invalidos: {exc}",
        ).model_dump(mode="json"),
    )
    if isinstance(validated, dict):
        return validated
    params = validated

    with session_manager.get_session() as session:
        registros = load_filtered_planejamentos(session, params.filtros)
        total, pagina = execute_collection_lookup(
            registros,
            ordenar_por=params.ordenar_por,
            ordem=params.ordem,
            offset=params.offset,
            limite=params.limite,
            sort_key_getters=SORT_FIELD_GETTERS,
            tie_breaker_getters=(lambda row: row.id,),
        )

    metadata = ConsultarPlanejamentoMetadata(
        filtros_aplicados=params.filtros.to_metadata_dict(),
        ordenar_por=params.ordenar_por,
        ordem=params.ordem,
        limite=params.limite,
        offset=params.offset,
        campos=params.campos or list(ALLOWED_PLANNING_FIELDS),
    )

    execution = LookupExecutionResult(
        total=total,
        rows=pagina,
        suggestion=("Nenhum registro de planejamento encontrado com os filtros." if not pagina else None),
    )
    return build_lookup_response(
        response_type=ConsultarPlanejamentoResponse,
        metadata=metadata,
        execution=execution,
        project_row=project_planejamento_fields,
        campos=params.campos,
    )
