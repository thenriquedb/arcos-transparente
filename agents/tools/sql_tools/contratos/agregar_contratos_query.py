"""Tool publica para agregacoes do dominio de contratos."""

from __future__ import annotations

from typing import Any

from pydantic import ValidationError
from sqlalchemy import func, select

from agents.tools.registry import PUBLIC_SCOPE, register
from database import session as session_manager
from database.models import Contrato

from .agregar_contratos_schema import (
    AgregacaoContratosItem,
    AgregarContratosMetadata,
    AgregarContratosParams,
    AgregarContratosResponse,
)
from .shared.querying import (
    GROUP_BY_COLUMNS,
    apply_contratos_filters,
    build_descricao_despesa_unavailable_message,
    contratos_supports_descricao_despesa,
    decimal_or_int_to_json,
)


METRIC_EXPRESSIONS = {
    "contagem": func.count(Contrato.id),
    "soma_valor": func.coalesce(func.sum(Contrato.valor), 0),
    "media_valor": func.coalesce(func.avg(Contrato.valor), 0),
}


@register(
    name="agregar_contratos",
    scope=PUBLIC_SCOPE,
    tags=["domain:contratos", "shape:aggregate"],
)
def agregar_contratos(
    filtros: dict[str, Any] | None = None,
    agrupar_por: str | None = None,
    metrica: str = "contagem",
    ordenar_por: str = "metrica",
    ordem: str = "desc",
    limite: int = 10,
) -> dict[str, Any]:
    """
    Agrega contratos para responder totais, rankings e somatorios.

    Use para perguntas como:
    - 'qual o total contratado pela educacao?'
    - 'qual secretaria tem mais contratos?'
    - 'quais categorias concentram maior valor contratado?'
    """
    try:
        params = AgregarContratosParams.model_validate(
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
        fallback_metadata = AgregarContratosMetadata(
            metrica="contagem",
            ordenar_por="metrica",
            ordem="desc",
            limite=10,
        )
        return AgregarContratosResponse(
            total_grupos=0,
            resultados=[],
            metadata=fallback_metadata,
            mensagem=f"Parametros invalidos: {exc}",
        ).model_dump(mode="json")

    with session_manager.get_session() as session:
        include_descricao_despesa = contratos_supports_descricao_despesa(session)
        metadata = AgregarContratosMetadata(
            filtros_aplicados=params.filtros.to_metadata_dict(),
            agrupar_por=params.agrupar_por,
            metrica=params.metrica,
            ordenar_por=params.ordenar_por,
            ordem=params.ordem,
            limite=params.limite,
        )

        metric_expression = METRIC_EXPRESSIONS[params.metrica].label(params.metrica)

        if params.agrupar_por is None:
            valor_total = session.execute(
                apply_contratos_filters(
                    select(metric_expression),
                    params.filtros,
                    include_descricao_despesa=include_descricao_despesa,
                )
            ).scalar_one()
            valor_total_json = decimal_or_int_to_json(valor_total)
            return AgregarContratosResponse(
                total_grupos=0,
                resultados=[],
                metadata=metadata,
                valor_total=valor_total_json,
                mensagem=(
                    build_descricao_despesa_unavailable_message(params.filtros)
                    if not include_descricao_despesa and valor_total_json
                    else None
                ),
                sugestao=(
                    build_descricao_despesa_unavailable_message(params.filtros)
                    if not valor_total_json and not include_descricao_despesa
                    else (
                        "Nenhum contrato encontrado com os filtros informados."
                        if not valor_total_json
                        else None
                    )
                ),
            ).model_dump(mode="json")

        group_column = GROUP_BY_COLUMNS[params.agrupar_por]
        grouped_stmt = apply_contratos_filters(
            select(group_column.label(params.agrupar_por), metric_expression),
            params.filtros,
            include_descricao_despesa=include_descricao_despesa,
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
        return AgregarContratosResponse(
            total_grupos=0,
            resultados=[],
            metadata=metadata,
            sugestao=(
                build_descricao_despesa_unavailable_message(params.filtros)
                if not include_descricao_despesa
                else "Nenhum contrato encontrado com os filtros informados."
            ),
        ).model_dump(mode="json")

    resultados = []
    for group_value, metric_value in rows:
        if params.agrupar_por == "ano_inicio" and group_value is not None:
            group_value = int(group_value)
        item_payload = {
            params.agrupar_por: group_value,
            params.metrica: decimal_or_int_to_json(metric_value),
        }
        resultados.append(
            AgregacaoContratosItem.model_validate(item_payload).model_dump(
                mode="json",
                exclude_none=True,
            )
        )

    mensagens: list[str] = []
    if not include_descricao_despesa:
        warning = build_descricao_despesa_unavailable_message(params.filtros)
        if warning is not None:
            mensagens.append(warning)
    if total_grupos > len(resultados):
        mensagens.append(
            f"Mostrando {len(resultados)} de {total_grupos} grupos encontrados."
        )
    mensagem = " ".join(mensagens) or None

    return AgregarContratosResponse(
        total_grupos=total_grupos,
        resultados=resultados,
        metadata=metadata,
        mensagem=mensagem,
    ).model_dump(mode="json")
