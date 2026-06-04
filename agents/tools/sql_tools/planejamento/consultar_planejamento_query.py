"""Tool publica para consultas amplas de planejamento."""

from __future__ import annotations

from typing import Any

from pydantic import ValidationError

from agents.tools.registry import PUBLIC_SCOPE, register, routing_metadata
from database import session as session_manager

from .consultar_planejamento_schema import (
    ConsultarPlanejamentoMetadata,
    ConsultarPlanejamentoParams,
    ConsultarPlanejamentoResponse,
)
from .shared.filters import ALLOWED_PLANNING_FIELDS
from .shared.querying import (
    load_filtered_planejamentos,
    project_rows,
    sort_planejamentos,
)


@register(
    name="consultar_planejamento",
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
    try:
        params = ConsultarPlanejamentoParams.model_validate(
            {
                "filtros": filtros,
                "ordenar_por": ordenar_por,
                "ordem": ordem,
                "limite": limite,
                "offset": offset,
                "campos": campos,
            }
        )
    except ValidationError as exc:
        fallback_metadata = ConsultarPlanejamentoMetadata(
            ordenar_por="mes_num",
            ordem="asc",
            limite=10,
            offset=0,
        )
        return ConsultarPlanejamentoResponse(
            total=0,
            resultados=[],
            metadata=fallback_metadata,
            mensagem=f"Parametros invalidos: {exc}",
        ).model_dump(mode="json")

    with session_manager.get_session() as session:
        registros = load_filtered_planejamentos(session, params.filtros)
        total = len(registros)
        ordenados = sort_planejamentos(registros, params.ordenar_por, params.ordem)
        pagina = ordenados[params.offset : params.offset + params.limite]

    metadata = ConsultarPlanejamentoMetadata(
        filtros_aplicados=params.filtros.to_metadata_dict(),
        ordenar_por=params.ordenar_por,
        ordem=params.ordem,
        limite=params.limite,
        offset=params.offset,
        campos=params.campos or list(ALLOWED_PLANNING_FIELDS),
    )

    if not pagina:
        return ConsultarPlanejamentoResponse(
            total=0,
            resultados=[],
            metadata=metadata,
            sugestao="Nenhum registro de planejamento encontrado com os filtros.",
        ).model_dump(mode="json")

    resultados = project_rows(pagina, params.campos)
    mensagem = None
    if total > len(resultados):
        mensagem = f"Mostrando {len(resultados)} de {total} registros encontrados."

    return ConsultarPlanejamentoResponse(
        total=total,
        resultados=resultados,
        metadata=metadata,
        mensagem=mensagem,
    ).model_dump(mode="json")
