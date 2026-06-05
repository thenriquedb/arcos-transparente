"""Tool publica para agregacoes do dominio de servidores."""

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
from database.models import FolhaServidor

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
    "secretaria": FolhaServidor.secretaria,
    "cargo": FolhaServidor.cargo,
    "mes_de_referencia": FolhaServidor.competencia_referencia,
}


def _build_metric_expression(metrica: str):
    if metrica == "contagem":
        return func.count(func.distinct(func.lower(FolhaServidor.nome))).label(metrica)
    return func.coalesce(func.sum(FolhaServidor.salario_base), 0).label(metrica)


@register(
    name="agregar_servidores",
    scope=PUBLIC_SCOPE,
    tags=["domain:servidores", "shape:aggregate"],
    routing=routing_metadata(
        examples=[
            "Quantos servidores trabalham na saude?",
            "Qual secretaria tem mais servidores?",
        ],
        hints=[
            "servidor",
            "contagem",
            "ranking",
            "massa salarial",
            "agrupamento",
        ],
    ),
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
    Calcula totais, contagens e rankings sobre servidores.

    Use esta tool quando a pergunta pedir quantos servidores existem, qual grupo tem
    mais pessoas ou qual grupo concentra maior massa salarial.
    NAO use para listar nomes ou detalhes de pessoas; para isso use
    `consultar_servidores`.
    NAO use para historico mensal de pagamento de um servidor com nome informado;
    para isso use `buscar_historico_de_pagamentos_do_servidor`.

    Se `mes_de_referencia` nao for informado, a agregacao usa o mes mais recente com
    dados para evitar misturar snapshots de meses diferentes.

    Args:
        filtros: Objeto com filtros opcionais. Campos aceitos: `nome`, `secretaria`,
            `cargo`, `mes_de_referencia`, `mes_de_referencia_inicio`,
            `mes_de_referencia_fim`, `salario_min` e `salario_max`.
            Datas em `YYYY-MM-DD`.
        agrupar_por: Campo opcional de agrupamento. Aceita `secretaria`, `cargo`
            ou `mes_de_referencia`. Se nao for informado, a tool retorna um
            `valor_total`.
        metrica: Metrica calculada. Aceita `contagem` ou `soma_salario_base`.
        ordenar_por: Aceita `metrica` ou o mesmo valor usado em `agrupar_por`.
        ordem: Direcao da ordenacao: `asc` ou `desc`.
        limite: Quantidade maxima de grupos retornados. Inteiro de 1 a 100.

    Returns:
        dict com:
        - `total_grupos`: total de grupos encontrados.
        - `resultados`: lista de grupos; cada item traz o campo de agrupamento e a
          metrica calculada.
        - `metadata`: filtros aplicados, configuracao da agregacao e o
          `mes_de_referencia_considerado`.
        - `valor_total`: valor agregado quando `agrupar_por` nao for informado.
        - `mensagem`: aviso quando so parte dos grupos for exibida.
        - `sugestao`: dica quando nenhum resultado for encontrado.
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
        schema_type=AgregarServidoresParams,
        on_error=lambda exc: AgregarServidoresResponse(
            total_grupos=0,
            resultados=[],
            metadata=AgregarServidoresMetadata(
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
            total_match, valor_total = execute_statement_total(
                session,
                count_stmt=apply_servidores_filters(
                    select(func.count()),
                    params.filtros,
                    mes_de_referencia_considerado=mes_de_referencia_considerado,
                ),
                value_stmt=apply_servidores_filters(
                    select(metric_expression),
                    params.filtros,
                    mes_de_referencia_considerado=mes_de_referencia_considerado,
                ),
            )
            return build_aggregate_response(
                response_type=AgregarServidoresResponse,
                metadata=metadata,
                execution=AggregateExecutionResult(
                    valor_total=decimal_or_int_to_json(valor_total),
                    suggestion=(
                        "Nenhum servidor encontrado com os filtros informados."
                        if total_match == 0
                        else None
                    ),
                ),
            )

        group_column = GROUP_BY_COLUMNS[params.agrupar_por]
        grouped_stmt = apply_servidores_filters(
            select(group_column.label(params.agrupar_por), metric_expression),
            params.filtros,
            mes_de_referencia_considerado=mes_de_referencia_considerado,
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

    return build_aggregate_response(
        response_type=AgregarServidoresResponse,
        metadata=metadata,
        execution=AggregateExecutionResult(
            total_grupos=total_grupos,
            rows=rows,
            suggestion=(
                "Nenhum servidor encontrado com os filtros informados."
                if not rows
                else None
            ),
        ),
        item_model=AgregacaoServidoresItem,
        agrupar_por=params.agrupar_por,
        metrica=params.metrica,
        serialize_metric=decimal_or_int_to_json,
    )
