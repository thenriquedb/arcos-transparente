"""Tool publica para agregacoes de receitas."""

from __future__ import annotations

from typing import Any

from pydantic import ValidationError

from agents.tools.registry import PUBLIC_SCOPE, register
from database import session as session_manager

from .agregar_receitas_schema import (
    AgregacaoReceitasItem,
    AgregarReceitasMetadata,
    AgregarReceitasParams,
    AgregarReceitasResponse,
)
from .shared.querying import (
    GROUP_FIELD_GETTERS,
    calculate_metric,
    load_filtered_receitas,
)


@register(
    name="agregar_receitas",
    scope=PUBLIC_SCOPE,
    tags=["domain:receitas", "shape:aggregate"],
)
def agregar_receitas(
    filtros: dict[str, Any] | None = None,
    agrupar_por: str | None = None,
    metrica: str = "soma_valor_recebido",
    ordenar_por: str = "metrica",
    ordem: str = "desc",
    limite: int = 10,
) -> dict[str, Any]:
    """
    Calcula totais, contagens e rankings sobre receitas.

    Use esta tool quando a pergunta pedir quanto foi arrecadado, quanto foi
    lancado ou qual categoria, tributo ou unidade responsavel mais arrecadou.
    NAO use para listar registros individuais; para isso use `consultar_receitas`.
    NAO use para planejamento orcamentario ou despesas; para isso use
    `agregar_planejamento` ou `agregar_despesas`.

    O padrao usa arrecadacao efetiva. Para valores apenas lancados, informe
    `tipo_de_dado='lancamento'`.

    Args:
        filtros: Objeto com filtros opcionais. Campos aceitos: `tipo_de_dado`,
            `ano`, `mes`, `mes_inicio`, `mes_fim`, `unidade_responsavel`,
            `categoria`, `categoria_codigo`, `tipo`, `tributo`,
            `origem_do_recurso`, `tema`, `valor_min` e `valor_max`. `mes`,
            `mes_inicio` e `mes_fim` aceitam numero de 1 a 12 ou nome do mes.
        agrupar_por: Campo opcional de agrupamento. Aceita `mes`,
            `unidade_responsavel`, `categoria`, `tipo`, `tributo` ou
            `origem_do_recurso`. Se nao for informado, a tool retorna um
            `valor_total`.
        metrica: Metrica calculada. Aceita `contagem`, `soma_valor_previsto`,
            `soma_valor_recebido`, `soma_valor_lancado`,
            `soma_valor_em_divida_ativa` ou
            `soma_valor_em_cobranca_judicial`.
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
        params = AgregarReceitasParams.model_validate(
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
        fallback_metadata = AgregarReceitasMetadata(
            metrica="soma_valor_recebido",
            ordenar_por="metrica",
            ordem="desc",
            limite=10,
        )
        return AgregarReceitasResponse(
            total_grupos=0,
            resultados=[],
            metadata=fallback_metadata,
            mensagem=f"Parametros invalidos: {exc}",
        ).model_dump(mode="json")

    with session_manager.get_session() as session:
        registros = load_filtered_receitas(session, params.filtros)

    metadata = AgregarReceitasMetadata(
        filtros_aplicados=params.filtros.to_metadata_dict(),
        agrupar_por=params.agrupar_por,
        metrica=params.metrica,
        ordenar_por=params.ordenar_por,
        ordem=params.ordem,
        limite=params.limite,
    )

    if params.agrupar_por is None:
        valor_total = calculate_metric(registros, params.metrica)
        return AgregarReceitasResponse(
            total_grupos=0,
            resultados=[],
            metadata=metadata,
            valor_total=valor_total,
            sugestao=(
                "Nenhum registro de receitas encontrado com os filtros."
                if not valor_total
                else None
            ),
        ).model_dump(mode="json")

    grouped_rows: dict[str, list[dict[str, object]]] = {}
    group_getter = GROUP_FIELD_GETTERS[params.agrupar_por]
    for registro in registros:
        group_value = group_getter(registro) or "nao_informado"
        grouped_rows.setdefault(str(group_value), []).append(registro)

    resultados = []
    for group_value, group_rows in grouped_rows.items():
        metric_value = calculate_metric(group_rows, params.metrica)
        item_payload = {
            params.agrupar_por: group_value,
            params.metrica: metric_value,
        }
        resultados.append(
            AgregacaoReceitasItem.model_validate(item_payload).model_dump(
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

    return AgregarReceitasResponse(
        total_grupos=total_grupos,
        resultados=resultados,
        metadata=metadata,
        mensagem=mensagem,
        sugestao=(
            "Nenhum registro de receitas encontrado com os filtros."
            if not resultados
            else None
        ),
    ).model_dump(mode="json")
