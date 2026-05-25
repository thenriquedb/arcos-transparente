"""Tool publica para agregacoes do dominio de servidores."""

from __future__ import annotations

from typing import Any

from pydantic import ValidationError
from sqlalchemy import func, select

from agents.tools.registry import PUBLIC_SCOPE, register
from database import session as session_manager
from database.models import Servidor

from .agregar_servidores_schema import (
    AgregacaoServidoresItem,
    AgregarServidoresMetadata,
    AgregarServidoresParams,
    AgregarServidoresResponse,
)
from .shared.querying import (
    apply_servidores_filters,
    decimal_or_int_to_json,
    resolve_mes_de_referencia_padrao,
)


GROUP_BY_COLUMNS = {
    "secretaria": Servidor.secretaria,
    "cargo": Servidor.cargo,
    "mes_de_referencia": Servidor.competencia_referencia,
}


def _build_metric_expression(metrica: str):
    if metrica == "contagem":
        return func.count(func.distinct(func.lower(Servidor.nome))).label(metrica)
    return func.coalesce(func.sum(Servidor.salario_base), 0).label(metrica)


@register(
    name="agregar_servidores",
    scope=PUBLIC_SCOPE,
    tags=["domain:servidores", "shape:aggregate"],
)
def agregar_servidores(
    filtros: dict[str, Any] | None = None,
    agrupar_por: str | None = None,
    metrica: str = "contagem",
    ordenar_por: str = "metrica",
    ordem: str = "desc",
    limite: int = 10,
) -> dict[str, Any]:
    """
    Agrega servidores para responder totais, rankings e somatorios.

    Use para perguntas como:
    - 'quantas pessoas trabalham na saude?'
    - 'qual secretaria com mais funcionarios?'
    - 'quais cargos concentram maior massa salarial?'

    Quando `mes_de_referencia` nao e informado nos filtros, a agregacao usa por padrao
    o mes mais recente com dados para evitar misturar snapshots de meses diferentes.
    """
    try:
        params = AgregarServidoresParams.model_validate(
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
        fallback_metadata = AgregarServidoresMetadata(
            metrica="contagem",
            ordenar_por="metrica",
            ordem="desc",
            limite=10,
        )
        return AgregarServidoresResponse(
            total_grupos=0,
            resultados=[],
            metadata=fallback_metadata,
            mensagem=f"Parametros invalidos: {exc}",
        ).model_dump(mode="json")

    with session_manager.get_session() as session:
        mes_de_referencia_considerado, mes_padrao_aplicado = (
            resolve_mes_de_referencia_padrao(
                session,
                params.filtros,
            )
        )

        metadata = AgregarServidoresMetadata(
            filtros_aplicados=params.filtros.to_metadata_dict(),
            agrupar_por=params.agrupar_por,
            metrica=params.metrica,
            ordenar_por=params.ordenar_por,
            ordem=params.ordem,
            limite=params.limite,
            mes_de_referencia_considerado=mes_de_referencia_considerado,
            mes_de_referencia_padrao_aplicado=mes_padrao_aplicado,
        )

        metric_expression = _build_metric_expression(params.metrica)

        if params.agrupar_por is None:
            valor_total = session.execute(
                apply_servidores_filters(
                    select(metric_expression),
                    params.filtros,
                    mes_de_referencia_considerado=mes_de_referencia_considerado,
                )
            ).scalar_one()
            valor_total_json = decimal_or_int_to_json(valor_total)
            return AgregarServidoresResponse(
                total_grupos=0,
                resultados=[],
                metadata=metadata,
                valor_total=valor_total_json,
                sugestao=(
                    "Nenhum servidor encontrado com os filtros informados."
                    if not valor_total_json
                    else None
                ),
            ).model_dump(mode="json")

        group_column = GROUP_BY_COLUMNS[params.agrupar_por]
        grouped_stmt = apply_servidores_filters(
            select(group_column.label(params.agrupar_por), metric_expression),
            params.filtros,
            mes_de_referencia_considerado=mes_de_referencia_considerado,
        ).group_by(group_column)

        total_grupos = session.execute(
            select(func.count()).select_from(grouped_stmt.order_by(None).subquery())
        ).scalar_one()

        if params.ordenar_por == "metrica":
            order_column = metric_expression
        else:
            order_column = group_column
        grouped_stmt = grouped_stmt.order_by(
            order_column.desc() if params.ordem == "desc" else order_column.asc()
        ).limit(params.limite)

        rows = session.execute(grouped_stmt).all()

    if not rows:
        return AgregarServidoresResponse(
            total_grupos=0,
            resultados=[],
            metadata=metadata,
            sugestao="Nenhum servidor encontrado com os filtros informados.",
        ).model_dump(mode="json")

    resultados = []
    for group_value, metric_value in rows:
        item_payload = {
            params.agrupar_por: group_value,
            params.metrica: decimal_or_int_to_json(metric_value),
        }
        resultados.append(
            AgregacaoServidoresItem.model_validate(item_payload).model_dump(
                mode="json",
                exclude_none=True,
            )
        )

    mensagem = None
    if total_grupos > len(resultados):
        mensagem = f"Mostrando {len(resultados)} de {total_grupos} grupos encontrados."

    return AgregarServidoresResponse(
        total_grupos=total_grupos,
        resultados=resultados,
        metadata=metadata,
        mensagem=mensagem,
    ).model_dump(mode="json")
