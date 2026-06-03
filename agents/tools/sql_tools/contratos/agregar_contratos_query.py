"""Tool publica para agregacoes do dominio de contratos."""

from __future__ import annotations

from typing import Any

from pydantic import ValidationError
from sqlalchemy import func, select

from agents.tools.registry import PUBLIC_SCOPE, register, routing_metadata
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
    build_contract_fallback_message,
    build_descricao_despesa_unavailable_message,
    contratos_supports_descricao_despesa,
    contratos_supports_xml_original,
    get_contratos_available_columns,
    decimal_or_int_to_json,
)


METRIC_EXPRESSIONS = {
    "contagem": func.count(Contrato.id),
    "soma_valor": func.coalesce(func.sum(Contrato.valor), 0),
    "media_valor": func.coalesce(func.avg(Contrato.valor), 0),
}


def _execute_total_sem_grupo(
    session,
    params: AgregarContratosParams,
    *,
    include_descricao_despesa: bool,
    include_xml_original: bool,
    available_columns: set[str],
) -> tuple[int, float | int | None]:
    """Executa agregacao sem agrupamento e devolve contagem real + valor."""

    contagem = session.execute(
        apply_contratos_filters(
            select(func.count(Contrato.id)),
            params.filtros,
            include_descricao_despesa=include_descricao_despesa,
            include_xml_original=include_xml_original,
            available_columns=available_columns,
        )
    ).scalar_one()

    metric_expression = METRIC_EXPRESSIONS[params.metrica].label(params.metrica)
    valor_total = session.execute(
        apply_contratos_filters(
            select(metric_expression),
            params.filtros,
            include_descricao_despesa=include_descricao_despesa,
            include_xml_original=include_xml_original,
            available_columns=available_columns,
        )
    ).scalar_one()
    return contagem, decimal_or_int_to_json(valor_total)


def _execute_grupo(
    session,
    params: AgregarContratosParams,
    *,
    include_descricao_despesa: bool,
    include_xml_original: bool,
    available_columns: set[str],
) -> tuple[int, list[tuple[Any, Any]]]:
    """Executa agregacao agrupada e devolve total de grupos + linhas."""

    metric_expression = METRIC_EXPRESSIONS[params.metrica].label(params.metrica)
    group_column = GROUP_BY_COLUMNS[params.agrupar_por]
    grouped_stmt = apply_contratos_filters(
        select(group_column.label(params.agrupar_por), metric_expression),
        params.filtros,
        include_descricao_despesa=include_descricao_despesa,
        include_xml_original=include_xml_original,
        available_columns=available_columns,
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
    return total_grupos, rows


def _execute_fallback_aggregate(
    session,
    params: AgregarContratosParams,
    *,
    include_descricao_despesa: bool,
    include_xml_original: bool,
    available_columns: set[str],
) -> tuple[Any, str, str] | None:
    """Tenta novamente a agregacao trocando o campo textual principal."""

    source_field = next(
        (
            field_name
            for field_name in ("fornecedor", "descricao", "categoria", "secretaria")
            if getattr(params.filtros, field_name) is not None
        ),
        "",
    )
    for (
        target_field,
        fallback_filters,
    ) in params.filtros.build_text_fallback_candidates():
        fallback_params = params.model_copy(update={"filtros": fallback_filters})
        if params.agrupar_por is None:
            total_match, valor_total = _execute_total_sem_grupo(
                session,
                fallback_params,
                include_descricao_despesa=include_descricao_despesa,
                include_xml_original=include_xml_original,
                available_columns=available_columns,
            )
            if total_match > 0:
                return (
                    (fallback_filters, total_match, valor_total),
                    source_field,
                    target_field,
                )
            continue

        total_grupos, rows = _execute_grupo(
            session,
            fallback_params,
            include_descricao_despesa=include_descricao_despesa,
            include_xml_original=include_xml_original,
            available_columns=available_columns,
        )
        if total_grupos > 0:
            return (
                (fallback_filters, total_grupos, rows),
                source_field,
                target_field,
            )
    return None


@register(
    name="agregar_contratos",
    scope=PUBLIC_SCOPE,
    tags=["domain:contratos", "shape:aggregate"],
    routing=routing_metadata(
        examples=[
            "Qual o total contratado pela educacao?",
            "Quais fornecedores concentram maior valor contratado?",
        ],
        hints=[
            "contrato",
            "total contratado",
            "ranking",
            "fornecedor",
            "media",
        ],
    ),
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
    Calcula totais, medias e rankings sobre contratos.

    Use esta tool quando a pergunta pedir valor total contratado, media de valor
    ou comparacao entre secretarias, categorias, fornecedores e anos de inicio.
    NAO use para listar contratos individuais; para isso use `consultar_contratos`.
    NAO use para somar ou contar licitacoes; para isso use `agregar_licitacoes`.

    Args:
        filtros: Objeto com filtros opcionais. Campos aceitos: `numero`,
            `fornecedor`, `documento_fornecedor`, `categoria`, `secretaria`,
            `descricao`, `data_inicio`, `data_inicio_inicio`, `data_inicio_fim`,
            `valor_min` e `valor_max`. Datas em `YYYY-MM-DD`.
        agrupar_por: Campo opcional de agrupamento. Aceita `secretaria`,
            `categoria`, `fornecedor` ou `ano_inicio`. Se nao for informado,
            a tool retorna um `valor_total`.
        metrica: Metrica calculada. Aceita `contagem`, `soma_valor`
            ou `media_valor`.
        ordenar_por: Aceita `metrica` ou o mesmo valor usado em `agrupar_por`.
        ordem: Direcao da ordenacao: `asc` ou `desc`.
        limite: Quantidade maxima de grupos retornados. Inteiro de 1 a 100.

    Returns:
        dict com:
        - `total_grupos`: total de grupos encontrados.
        - `resultados`: lista de grupos; cada item traz o campo de agrupamento e a
          metrica calculada.
        - `metadata`: filtros aplicados, possiveis filtros de fallback e
          configuracao da agregacao.
        - `valor_total`: valor agregado quando `agrupar_por` nao for informado.
        - `mensagem`: aviso quando so parte dos grupos for exibida.
        - `sugestao`: dica quando nenhum contrato corresponder aos filtros.
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
        include_xml_original = contratos_supports_xml_original(session)
        available_columns = get_contratos_available_columns(session)
        metadata = AgregarContratosMetadata(
            filtros_aplicados=params.filtros.to_metadata_dict(),
            agrupar_por=params.agrupar_por,
            metrica=params.metrica,
            ordenar_por=params.ordenar_por,
            ordem=params.ordem,
            limite=params.limite,
        )
        fallback_aplicado = False
        fallback_source_field = ""
        fallback_target_field = ""

        if params.agrupar_por is None:
            total_match, valor_total_json = _execute_total_sem_grupo(
                session,
                params,
                include_descricao_despesa=include_descricao_despesa,
                include_xml_original=include_xml_original,
                available_columns=available_columns,
            )
            filtros_execucao = params.filtros
            if total_match == 0:
                fallback_result = _execute_fallback_aggregate(
                    session,
                    params,
                    include_descricao_despesa=include_descricao_despesa,
                    include_xml_original=include_xml_original,
                    available_columns=available_columns,
                )
                if fallback_result is not None:
                    (
                        (filtros_execucao, total_match, valor_total_json),
                        fallback_source_field,
                        fallback_target_field,
                    ) = fallback_result
                    fallback_aplicado = True
                    metadata = metadata.model_copy(
                        update={
                            "filtros_fallback_aplicados": filtros_execucao.to_metadata_dict()
                        }
                    )
            return AgregarContratosResponse(
                total_grupos=0,
                resultados=[],
                metadata=metadata,
                valor_total=valor_total_json,
                mensagem=(
                    " ".join(
                        mensagem
                        for mensagem in [
                            (
                                build_descricao_despesa_unavailable_message(
                                    params.filtros
                                )
                                if not include_descricao_despesa and total_match > 0
                                else None
                            ),
                            (
                                build_contract_fallback_message(
                                    fallback_source_field,
                                    fallback_target_field,
                                )
                                if fallback_aplicado
                                else None
                            ),
                        ]
                        if mensagem
                    )
                    or None
                ),
                sugestao=(
                    build_descricao_despesa_unavailable_message(params.filtros)
                    if total_match == 0 and not include_descricao_despesa
                    else (
                        "Nenhum contrato encontrado com os filtros informados."
                        if total_match == 0
                        else None
                    )
                ),
            ).model_dump(mode="json")
        total_grupos, rows = _execute_grupo(
            session,
            params,
            include_descricao_despesa=include_descricao_despesa,
            include_xml_original=include_xml_original,
            available_columns=available_columns,
        )
        filtros_execucao = params.filtros
        if total_grupos == 0:
            fallback_result = _execute_fallback_aggregate(
                session,
                params,
                include_descricao_despesa=include_descricao_despesa,
                include_xml_original=include_xml_original,
                available_columns=available_columns,
            )
            if fallback_result is not None:
                (
                    (filtros_execucao, total_grupos, rows),
                    fallback_source_field,
                    fallback_target_field,
                ) = fallback_result
                fallback_aplicado = True
                metadata = metadata.model_copy(
                    update={
                        "filtros_fallback_aplicados": filtros_execucao.to_metadata_dict()
                    }
                )

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
    if fallback_aplicado:
        mensagens.append(
            build_contract_fallback_message(
                fallback_source_field,
                fallback_target_field,
            )
        )
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
