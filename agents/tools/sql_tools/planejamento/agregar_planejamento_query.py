"""Tool publica para agregacoes de planejamento."""

from __future__ import annotations

from typing import Any

from pydantic import ValidationError

from agents.tools.registry import PUBLIC_SCOPE, register
from database import session as session_manager

from .agregar_planejamento_schema import (
    AgregacaoPlanejamentoItem,
    AgregarPlanejamentoMetadata,
    AgregarPlanejamentoParams,
    AgregarPlanejamentoResponse,
)
from .shared.querying import (
    GROUP_FIELD_GETTERS,
    calculate_metric,
    load_filtered_planejamentos,
    metric_to_json,
)


@register(
    name="agregar_planejamento",
    scope=PUBLIC_SCOPE,
    tags=["domain:planejamento", "shape:aggregate"],
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
    try:
        params = AgregarPlanejamentoParams.model_validate(
            {
                "filtros": filtros,
                "agrupar_por": agrupar_por,
                "metrica": metrica,
                "ordenar_por": ordenar_por,
                "ordem": ordem,
                "limite": limite,
            }
        )
    except ValidationError as exc:
        fallback_metadata = AgregarPlanejamentoMetadata(
            metrica="soma_orcamento_atualizado",
            ordenar_por="metrica",
            ordem="desc",
            limite=10,
        )
        return AgregarPlanejamentoResponse(
            total_grupos=0,
            resultados=[],
            metadata=fallback_metadata,
            mensagem=f"Parametros invalidos: {exc}",
        ).model_dump(mode="json")

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

    if params.agrupar_por is None:
        valor_total = metric_to_json(calculate_metric(registros, params.metrica))
        return AgregarPlanejamentoResponse(
            total_grupos=0,
            resultados=[],
            metadata=metadata,
            valor_total=valor_total,
            sugestao=(
                "Nenhum registro de planejamento encontrado com os filtros."
                if not valor_total
                else None
            ),
        ).model_dump(mode="json")

    grouped_rows: dict[str, list[Any]] = {}
    group_getter = GROUP_FIELD_GETTERS[params.agrupar_por]
    for registro in registros:
        group_value = group_getter(registro) or "nao_informado"
        grouped_rows.setdefault(str(group_value), []).append(registro)

    resultados = []
    for group_value, group_rows in grouped_rows.items():
        metric_value = metric_to_json(calculate_metric(group_rows, params.metrica))
        item_payload = {
            params.agrupar_por: group_value,
            params.metrica: metric_value,
        }
        resultados.append(
            AgregacaoPlanejamentoItem.model_validate(item_payload).model_dump(
                mode="json",
                exclude_none=True,
            )
        )

    reverse = params.ordem == "desc"
    if params.ordenar_por == "metrica":
        resultados.sort(key=lambda item: item[params.metrica], reverse=reverse)
    else:
        resultados.sort(key=lambda item: item[params.agrupar_por], reverse=reverse)

    total_grupos = len(resultados)
    resultados = resultados[: params.limite]
    mensagem = None
    if total_grupos > len(resultados):
        mensagem = f"Mostrando {len(resultados)} de {total_grupos} grupos encontrados."

    return AgregarPlanejamentoResponse(
        total_grupos=total_grupos,
        resultados=resultados,
        metadata=metadata,
        mensagem=mensagem,
        sugestao=(
            "Nenhum registro de planejamento encontrado com os filtros."
            if not resultados
            else None
        ),
    ).model_dump(mode="json")
