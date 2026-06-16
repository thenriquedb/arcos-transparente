"""Tool publica para agregacoes do dominio de servidores da Camara Municipal."""

from __future__ import annotations

from typing import Any

from sqlalchemy import func, select

from agents.tools.names import ToolName
from agents.tools.registry import PUBLIC_SCOPE, register, routing_metadata
from agents.tools.sql_tools.shared.aggregate import (
    AggregateExecutionResult,
    build_aggregate_response,
    execute_statement_grouped,
    execute_statement_total,
)
from agents.tools.sql_tools.shared.validation import validate_tool_params
from database import session as session_manager
from database.models import ServidorCamara
from shared.utils.decimal_to_float import decimal_or_int_to_json

from .agregar_servidores_camara_schema import (
    AgregacaoServidoresCamaraItem,
    AgregarServidoresCamaraMetadata,
    AgregarServidoresCamaraParams,
    AgregarServidoresCamaraResponse,
)
from .shared.querying import (
    apply_servidores_camara_filters,
    resolve_mes_de_referencia_padrao_camara,
)


_GROUP_BY_COLUMNS = {
    "cargo": ServidorCamara.cargo,
    "lotacao": ServidorCamara.lotacao,
    "situacao_funcional": ServidorCamara.situacao_funcional,
    "mes_de_referencia": ServidorCamara.competencia_referencia,
}


def _build_metric_expression(metrica: str):
    if metrica == "contagem":
        return func.count(func.distinct(func.lower(ServidorCamara.nome))).label(metrica)
    if metrica == "soma_liquido":
        return func.coalesce(func.sum(ServidorCamara.liquido), 0).label(metrica)
    return func.coalesce(func.sum(ServidorCamara.salario_base), 0).label(metrica)


@register(
    name=ToolName.AGREGAR_SERVIDORES_CAMARA,
    scope=PUBLIC_SCOPE,
    tags=["domain:servidores_camara", "shape:aggregate"],
    routing=routing_metadata(
        examples=[
            "Quantos servidores trabalham na Camara Municipal?",
            "Qual cargo tem mais servidores na Camara?",
            "Qual a massa salarial da Camara de Arcos?",
        ],
        hints=[
            "camara municipal",
            "vereador",
            "legislativo",
            "contagem camara",
            "total camara",
        ],
    ),
)
def agregar_servidores_camara(
    filtros: dict[str, Any] | None = None,
    agrupar_por: str | None = None,
    metrica: str = "contagem",
    ordenar_por: str = "metrica",
    ordem: str = "desc",
    limite: int = 10,
) -> dict[str, Any]:
    """
    Calcula totais, contagens e rankings sobre servidores da Camara Municipal.

    Use esta tool para perguntas sobre quantas pessoas trabalham na Camara,
    qual cargo ou lotacao tem mais servidores, qual a massa salarial do Legislativo.
    NAO use para servidores da Prefeitura; para esses use `agregar_servidores`.
    NAO use para listar nomes; para isso use `consultar_servidores_camara`.

    Se `mes_de_referencia` nao for informado, usa o mes mais recente com dados.

    Args:
        filtros: Filtros opcionais. Campos: `nome`, `cargo`, `lotacao`,
            `situacao_funcional`, `vinculo`, `mes_de_referencia`,
            `mes_de_referencia_inicio`, `mes_de_referencia_fim`,
            `salario_min`, `salario_max`. Datas em `YYYY-MM-DD`.
        agrupar_por: Agrupamento opcional. Aceita `cargo`, `lotacao`,
            `situacao_funcional` ou `mes_de_referencia`.
        metrica: `contagem`, `soma_salario_base` ou `soma_liquido`.
        ordenar_por: `metrica` ou o mesmo valor de `agrupar_por`.
        ordem: `asc` ou `desc`.
        limite: Maximo de grupos retornados (1 a 100).

    Returns:
        dict com `total_grupos`, `resultados`, `metadata`, `valor_total`,
        `mensagem`, `sugestao`.
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
        schema_type=AgregarServidoresCamaraParams,
        on_error=lambda exc: AgregarServidoresCamaraResponse(
            total_grupos=0,
            resultados=[],
            metadata=AgregarServidoresCamaraMetadata(
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
        mes_de_referencia_considerado, mes_padrao_aplicado = resolve_mes_de_referencia_padrao_camara(
            session, params.filtros
        )

        metadata = AgregarServidoresCamaraMetadata(
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
                count_stmt=apply_servidores_camara_filters(
                    select(func.count()),
                    params.filtros,
                    mes_de_referencia_considerado=mes_de_referencia_considerado,
                ),
                value_stmt=apply_servidores_camara_filters(
                    select(metric_expression),
                    params.filtros,
                    mes_de_referencia_considerado=mes_de_referencia_considerado,
                ),
            )
            return build_aggregate_response(
                response_type=AgregarServidoresCamaraResponse,
                metadata=metadata,
                execution=AggregateExecutionResult(
                    valor_total=decimal_or_int_to_json(valor_total),
                    source_count=total_match,
                    suggestion=(
                        "Nenhum servidor da Camara encontrado com os filtros informados." if total_match == 0 else None
                    ),
                ),
            )

        group_column = _GROUP_BY_COLUMNS[params.agrupar_por]
        grouped_stmt = apply_servidores_camara_filters(
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
        total_match, valor_total = execute_statement_total(
            session,
            count_stmt=apply_servidores_camara_filters(
                select(func.count()),
                params.filtros,
                mes_de_referencia_considerado=mes_de_referencia_considerado,
            ),
            value_stmt=apply_servidores_camara_filters(
                select(metric_expression),
                params.filtros,
                mes_de_referencia_considerado=mes_de_referencia_considerado,
            ),
        )

    return build_aggregate_response(
        response_type=AgregarServidoresCamaraResponse,
        metadata=metadata,
        execution=AggregateExecutionResult(
            total_grupos=total_grupos,
            rows=rows,
            valor_total=decimal_or_int_to_json(valor_total),
            source_count=total_match,
            suggestion=("Nenhum servidor da Camara encontrado com os filtros informados." if not rows else None),
        ),
        item_model=AgregacaoServidoresCamaraItem,
        agrupar_por=params.agrupar_por,
        metrica=params.metrica,
        serialize_metric=decimal_or_int_to_json,
    )
