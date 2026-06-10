"""Tool publica para agregacoes do dominio de licitacoes."""

from __future__ import annotations

from typing import Any

from sqlalchemy import func, select

from agents.tools.registry import PUBLIC_SCOPE, register, routing_metadata
from agents.tools.sql_tools.shared.aggregate import (
    AggregateExecutionResult,
    build_aggregate_response,
    execute_statement_grouped,
    execute_statement_total,
)
from agents.tools.sql_tools.shared.validation import validate_tool_params
from database import session as session_manager
from database.models import Licitacao
from shared.utils.text import matches_text_query

from .agregar_licitacoes_schema import (
    AgregacaoLicitacoesItem,
    AgregarLicitacoesMetadata,
    AgregarLicitacoesParams,
    AgregarLicitacoesResponse,
)
from shared.utils.decimal_to_float import decimal_or_int_to_json

from .shared.querying import apply_licitacoes_filters


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


def _build_object_filter_execution(
    licitacoes: list[Licitacao],
    *,
    agrupar_por: str | None,
    metrica: str,
    ordenar_por: str,
    ordem: str,
    limite: int,
) -> AggregateExecutionResult:
    if agrupar_por is None:
        return AggregateExecutionResult(
            valor_total=_calculate_metric_from_rows(licitacoes, metrica),
            source_count=len(licitacoes),
        )

    grouped_rows: dict[str, list[Licitacao]] = {}
    for licitacao in licitacoes:
        group_value = _group_value_from_row(licitacao, agrupar_por)
        grouped_rows.setdefault(str(group_value), []).append(licitacao)

    resultados = [
        (
            group_value,
            _calculate_metric_from_rows(group_rows, metrica),
        )
        for group_value, group_rows in grouped_rows.items()
    ]
    reverse = ordem == "desc"
    if ordenar_por == "metrica":
        resultados.sort(key=lambda item: item[1], reverse=reverse)
    else:
        resultados.sort(key=lambda item: item[0], reverse=reverse)
    total_grupos = len(resultados)
    return AggregateExecutionResult(
        total_grupos=total_grupos,
        rows=resultados[:limite],
        source_count=len(licitacoes),
    )


@register(
    name="agregar_licitacoes",
    scope=PUBLIC_SCOPE,
    tags=["domain:licitacoes", "shape:aggregate"],
    routing=routing_metadata(
        examples=[
            "Quantas licitacoes existem na saude?",
            "Qual modalidade teve maior valor estimado?",
        ],
        hints=[
            "licitacao",
            "contagem",
            "valor estimado",
            "ranking",
            "modalidade",
        ],
    ),
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
    validated = validate_tool_params(
        {
            "filtros": filtros,
            "agrupar_por": agrupar_por,
            "metrica": metrica,
            "ordenar_por": ordenar_por,
            "ordem": ordem,
            "limite": limite,
        },
        schema_type=AgregarLicitacoesParams,
        on_error=lambda exc: AgregarLicitacoesResponse(
            total_grupos=0,
            resultados=[],
            metadata=AgregarLicitacoesMetadata(
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

    metadata = AgregarLicitacoesMetadata(
        filtros_aplicados=params.filtros.to_metadata_dict(),
        agrupar_por=params.agrupar_por,
        metrica=params.metrica,
        ordenar_por=params.ordenar_por,
        ordem=params.ordem,
        limite=params.limite,
    )

    with session_manager.get_session() as session:
        metric_expression = _build_metric_expression(params.metrica)

        if params.filtros.objeto:
            licitacoes = [
                licitacao
                for licitacao in session.execute(apply_licitacoes_filters(select(Licitacao), params.filtros))
                .scalars()
                .all()
                if matches_text_query(licitacao.objeto, params.filtros.objeto)
            ]
            execution = _build_object_filter_execution(
                licitacoes,
                agrupar_por=params.agrupar_por,
                metrica=params.metrica,
                ordenar_por=params.ordenar_por,
                ordem=params.ordem,
                limite=params.limite,
            )
        elif params.agrupar_por is None:
            total_match, valor_total = execute_statement_total(
                session,
                count_stmt=apply_licitacoes_filters(
                    select(func.count(Licitacao.id)),
                    params.filtros,
                ),
                value_stmt=apply_licitacoes_filters(
                    select(metric_expression),
                    params.filtros,
                ),
            )
            execution = AggregateExecutionResult(
                valor_total=valor_total,
                source_count=total_match,
            )
        else:
            group_column = GROUP_BY_COLUMNS[params.agrupar_por]
            grouped_stmt = apply_licitacoes_filters(
                select(group_column.label(params.agrupar_por), metric_expression),
                params.filtros,
            ).group_by(group_column)
            total_grupos, rows = execute_statement_grouped(
                session,
                grouped_stmt=grouped_stmt,
                ordenar_por=params.ordenar_por,
                ordem=params.ordem,
                limite=params.limite,
                group_column=group_column,
                metric_expression=metric_expression,
            )
            execution = AggregateExecutionResult(
                total_grupos=total_grupos,
                rows=rows,
            )

    suggestion = (
        "Nenhuma licitacao encontrada com os filtros informados."
        if (
            (params.agrupar_por is None and execution.source_count == 0)
            or (params.agrupar_por is not None and not execution.rows)
        )
        else None
    )
    return build_aggregate_response(
        response_type=AgregarLicitacoesResponse,
        metadata=metadata,
        execution=AggregateExecutionResult(
            total_grupos=execution.total_grupos,
            rows=execution.rows,
            valor_total=execution.valor_total,
            source_count=execution.source_count,
            suggestion=suggestion,
        ),
        item_model=AgregacaoLicitacoesItem if params.agrupar_por is not None else None,
        agrupar_por=params.agrupar_por,
        metrica=params.metrica if params.agrupar_por is not None else None,
        serialize_metric=decimal_or_int_to_json,
    )
