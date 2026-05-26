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
    Agrega receitas para responder totais, contagens e rankings.

    O padrao usa arrecadacao efetiva. Para impostos apenas lancados,
    informe `tipo_de_dado='lancamento'`.
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
