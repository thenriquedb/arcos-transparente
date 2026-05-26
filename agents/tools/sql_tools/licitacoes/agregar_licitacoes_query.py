"""Tool publica para agregacoes do dominio de licitacoes."""

from __future__ import annotations

from typing import Any

from pydantic import ValidationError
from sqlalchemy import func, select

from agents.tools.registry import PUBLIC_SCOPE, register
from database import session as session_manager
from database.models import Licitacao
from shared.utils.text import matches_text_query

from .agregar_licitacoes_schema import (
    AgregacaoLicitacoesItem,
    AgregarLicitacoesMetadata,
    AgregarLicitacoesParams,
    AgregarLicitacoesResponse,
)
from .shared.querying import (
    apply_licitacoes_filters,
    decimal_or_int_to_json,
)


GROUP_BY_COLUMNS = {
    "secretaria": Licitacao.secretaria,
    "modalidade": Licitacao.modalidade,
    "situacao": Licitacao.situacao,
    "ano_abertura": func.strftime("%Y", Licitacao.data_abertura),
}


def _build_metric_expression(metrica: str):
    if metrica == "contagem":
        return func.count(Licitacao.id).label(metrica)
    if metrica == "media_valor_estimado":
        return func.coalesce(func.avg(Licitacao.valor_estimado), 0).label(metrica)
    return func.coalesce(func.sum(Licitacao.valor_estimado), 0).label(metrica)


def _calculate_metric_from_rows(rows: list[Licitacao], metrica: str):
    if metrica == "contagem":
        return len(rows)
    total = sum(row.valor_estimado for row in rows)
    if metrica == "media_valor_estimado":
        return total / len(rows) if rows else 0
    return total


def _group_value_from_row(licitacao: Licitacao, agrupar_por: str):
    if agrupar_por == "ano_abertura":
        return str(licitacao.data_abertura.year)
    return getattr(licitacao, agrupar_por)


@register(
    name="agregar_licitacoes",
    scope=PUBLIC_SCOPE,
    tags=["domain:licitacoes", "shape:aggregate"],
)
def agregar_licitacoes(
    filtros: dict[str, Any] | None = None,
    agrupar_por: str | None = None,
    metrica: str = "contagem",
    ordenar_por: str = "metrica",
    ordem: str = "desc",
    limite: int = 10,
) -> dict[str, Any]:
    """
    Calcula totais, medias e rankings sobre licitacoes.

    Use esta tool quando a pergunta pedir quantas licitacoes existem, qual grupo
    concentra maior valor estimado ou quais modalidades aparecem mais.
    NAO use para listar licitacoes individuais; para isso use
    `consultar_licitacoes`.
    NAO use para valores de contratos assinados; para isso use
    `agregar_contratos`.

    Args:
        filtros: Objeto com filtros opcionais. Campos aceitos: `numero`,
            `modalidade`, `objeto`, `secretaria`, `situacao`, `fornecedor`,
            `cnpj_cpf`, `data_abertura`, `data_abertura_inicio`,
            `data_abertura_fim`, `valor_estimado_min` e `valor_estimado_max`.
            Datas em `YYYY-MM-DD`.
        agrupar_por: Campo opcional de agrupamento. Aceita `secretaria`,
            `modalidade`, `situacao` ou `ano_abertura`. Se nao for informado,
            a tool retorna um `valor_total`.
        metrica: Metrica calculada. Aceita `contagem`, `soma_valor_estimado`
            ou `media_valor_estimado`.
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
        - `sugestao`: dica quando nenhuma licitacao corresponder aos filtros.
    """
    try:
        params = AgregarLicitacoesParams.model_validate(
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
        fallback_metadata = AgregarLicitacoesMetadata(
            metrica="contagem",
            ordenar_por="metrica",
            ordem="desc",
            limite=10,
        )
        return AgregarLicitacoesResponse(
            total_grupos=0,
            resultados=[],
            metadata=fallback_metadata,
            mensagem=f"Parametros invalidos: {exc}",
        ).model_dump(mode="json")

    with session_manager.get_session() as session:
        metadata = AgregarLicitacoesMetadata(
            filtros_aplicados=params.filtros.to_metadata_dict(),
            agrupar_por=params.agrupar_por,
            metrica=params.metrica,
            ordenar_por=params.ordenar_por,
            ordem=params.ordem,
            limite=params.limite,
        )

        metric_expression = _build_metric_expression(params.metrica)

        if params.filtros.objeto:
            licitacoes = [
                licitacao
                for licitacao in session.execute(
                    apply_licitacoes_filters(select(Licitacao), params.filtros)
                )
                .scalars()
                .all()
                if matches_text_query(licitacao.objeto, params.filtros.objeto)
            ]

            if params.agrupar_por is None:
                valor_total_json = decimal_or_int_to_json(
                    _calculate_metric_from_rows(licitacoes, params.metrica)
                )
                return AgregarLicitacoesResponse(
                    total_grupos=0,
                    resultados=[],
                    metadata=metadata,
                    valor_total=valor_total_json,
                    sugestao=(
                        "Nenhuma licitacao encontrada com os filtros informados."
                        if not valor_total_json
                        else None
                    ),
                ).model_dump(mode="json")

            grouped_rows: dict[str, list[Licitacao]] = {}
            for licitacao in licitacoes:
                group_value = _group_value_from_row(licitacao, params.agrupar_por)
                grouped_rows.setdefault(str(group_value), []).append(licitacao)

            resultados = []
            for group_value, group_rows in grouped_rows.items():
                item_payload = {
                    params.agrupar_por: group_value,
                    params.metrica: decimal_or_int_to_json(
                        _calculate_metric_from_rows(group_rows, params.metrica)
                    ),
                }
                resultados.append(
                    AgregacaoLicitacoesItem.model_validate(item_payload).model_dump(
                        mode="json",
                        exclude_none=True,
                    )
                )

            reverse = params.ordem == "desc"
            if params.ordenar_por == "metrica":
                resultados.sort(key=lambda item: item[params.metrica], reverse=reverse)
            else:
                resultados.sort(
                    key=lambda item: item[params.agrupar_por],
                    reverse=reverse,
                )

            total_grupos = len(resultados)
            resultados = resultados[: params.limite]
            mensagem = None
            if total_grupos > len(resultados):
                mensagem = (
                    f"Mostrando {len(resultados)} de {total_grupos} grupos encontrados."
                )
            return AgregarLicitacoesResponse(
                total_grupos=total_grupos,
                resultados=resultados,
                metadata=metadata,
                mensagem=mensagem,
                sugestao=(
                    "Nenhuma licitacao encontrada com os filtros informados."
                    if not resultados
                    else None
                ),
            ).model_dump(mode="json")

        if params.agrupar_por is None:
            valor_total = session.execute(
                apply_licitacoes_filters(
                    select(metric_expression),
                    params.filtros,
                )
            ).scalar_one()
            valor_total_json = decimal_or_int_to_json(valor_total)
            return AgregarLicitacoesResponse(
                total_grupos=0,
                resultados=[],
                metadata=metadata,
                valor_total=valor_total_json,
                sugestao=(
                    "Nenhuma licitacao encontrada com os filtros informados."
                    if not valor_total_json
                    else None
                ),
            ).model_dump(mode="json")

        group_column = GROUP_BY_COLUMNS[params.agrupar_por]
        grouped_stmt = apply_licitacoes_filters(
            select(group_column.label(params.agrupar_por), metric_expression),
            params.filtros,
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
        return AgregarLicitacoesResponse(
            total_grupos=0,
            resultados=[],
            metadata=metadata,
            sugestao="Nenhuma licitacao encontrada com os filtros informados.",
        ).model_dump(mode="json")

    resultados = []
    for group_value, metric_value in rows:
        item_payload = {
            params.agrupar_por: group_value,
            params.metrica: decimal_or_int_to_json(metric_value),
        }
        resultados.append(
            AgregacaoLicitacoesItem.model_validate(item_payload).model_dump(
                mode="json",
                exclude_none=True,
            )
        )

    mensagem = None
    if total_grupos > len(resultados):
        mensagem = f"Mostrando {len(resultados)} de {total_grupos} grupos encontrados."

    return AgregarLicitacoesResponse(
        total_grupos=total_grupos,
        resultados=resultados,
        metadata=metadata,
        mensagem=mensagem,
    ).model_dump(mode="json")
