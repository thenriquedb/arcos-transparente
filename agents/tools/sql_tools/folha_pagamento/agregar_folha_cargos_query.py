"""Tool publica para agregacoes de folha de pagamento por cargo."""

from __future__ import annotations

from typing import Any

from sqlalchemy import func, select

from agents.tools.names import ToolName
from agents.tools.registry import PUBLIC_SCOPE, register, routing_metadata
from agents.tools.sql_tools.shared.empty_state import resolve_empty_result_suggestion
from agents.tools.sql_tools.shared.aggregate import (
    AggregateExecutionResult,
    build_aggregate_response,
    execute_statement_grouped,
    execute_statement_total,
)
from agents.tools.sql_tools.shared.validation import validate_tool_params
from database import session as session_manager
from database.models import FolhaCargo, FolhaPagamentoRegistro
from database.session import _normalizar_texto
from shared.utils.decimal_to_float import decimal_or_int_to_json

from .agregar_folha_cargos_schema import (
    AgregacaoFolhaCargosItem,
    AgregarFolhaCargosMetadata,
    AgregarFolhaCargosParams,
    AgregarFolhaCargosResponse,
)


def _apply_filters(stmt, filtros):
    if filtros.ano is not None:
        stmt = stmt.where(FolhaPagamentoRegistro.competencia_ano == filtros.ano)
    if filtros.mes is not None:
        stmt = stmt.where(FolhaPagamentoRegistro.competencia_mes_num == filtros.mes)
    if filtros.cargo:
        normalized = _normalizar_texto(filtros.cargo) or ""
        stmt = stmt.where(FolhaCargo.nome.ilike(f"%{normalized}%"))
    if filtros.servidor:
        from database.models import FolhaServidor

        stmt = stmt.join(FolhaServidor, FolhaPagamentoRegistro.servidor_id == FolhaServidor.id, isouter=True)
        normalized_s = _normalizar_texto(filtros.servidor) or ""
        stmt = stmt.where(func.normalizar(FolhaServidor.nome).like(f"%{normalized_s}%"))
    return stmt


def _base_joined_stmt():
    return (
        select().select_from(FolhaPagamentoRegistro).join(FolhaCargo, FolhaPagamentoRegistro.cargo_id == FolhaCargo.id)
    )


def _build_metric_expression(metrica: str):
    if metrica == "contagem":
        return func.count(func.distinct(FolhaPagamentoRegistro.servidor_id)).label(metrica)
    field_map = {
        "soma_salario_base": FolhaPagamentoRegistro.salario_base,
        "soma_vencimentos_totais": FolhaPagamentoRegistro.vencimentos_totais,
        "soma_descontos": FolhaPagamentoRegistro.descontos,
        "soma_liquido": FolhaPagamentoRegistro.liquido,
    }
    return func.coalesce(func.sum(field_map[metrica]), 0).label(metrica)


@register(
    name=ToolName.AGREGAR_FOLHA_CARGOS,
    scope=PUBLIC_SCOPE,
    tags=["domain:folha", "shape:aggregate"],
    routing=routing_metadata(
        examples=[
            "Qual cargo tem maior massa salarial na prefeitura?",
            "Quais os cargos com maior soma de liquido em 2025?",
            "Quantos servidores distintos existem por cargo?",
        ],
        hints=[
            "cargo",
            "massa salarial por cargo",
            "ranking cargo",
            "liquido por cargo",
            "descontos por cargo",
            "vencimentos por cargo",
        ],
    ),
)
def agregar_folha_cargos(
    filtros: dict[str, Any] | None = None,
    agrupar_por: str | None = None,
    metrica: str = "contagem",
    ordenar_por: str = "metrica",
    ordem: str = "desc",
    limite: int = 10,
) -> dict[str, Any]:
    """
    Agrega registros de folha de pagamento agrupados por cargo.

    Expoe metricas de proventos, vencimentos totais, descontos e valor liquido
    que nao estao disponiveis em `agregar_servidores`.
    Use esta tool para rankings de cargos por massa salarial, total de
    vencimentos ou total de descontos. Inclui metricas de `salario_base`,
    `vencimentos_totais`, `descontos` e `liquido`.
    NAO use para historico individual; para isso use
    `buscar_historico_de_pagamentos_do_servidor`.

    Args:
        filtros: Objeto com filtros opcionais. Campos aceitos: `cargo`,
            `servidor`, `ano` e `mes` (inteiro de 1 a 12).
        agrupar_por: Aceita `cargo` ou `None`. Quando `None`, retorna
            `valor_total` sem agrupamento.
        metrica: Metrica calculada. Aceita `contagem`,
            `soma_salario_base`, `soma_vencimentos_totais`,
            `soma_descontos` ou `soma_liquido`.
        ordenar_por: Aceita `metrica` ou `cargo`.
        ordem: Direcao da ordenacao: `asc` ou `desc`.
        limite: Quantidade maxima de grupos. Inteiro de 1 a 100.

    Returns:
        dict com:
        - `total_grupos`: total de grupos encontrados.
        - `resultados`: lista de grupos com o cargo e a metrica calculada.
        - `metadata`: filtros e configuracao da agregacao.
        - `valor_total`: total agregado quando sem agrupamento.
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
        schema_type=AgregarFolhaCargosParams,
        on_error=lambda exc: AgregarFolhaCargosResponse(
            total_grupos=0,
            resultados=[],
            metadata=AgregarFolhaCargosMetadata(
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

    metric_expression = _build_metric_expression(params.metrica)

    with session_manager.get_session() as session:
        empty_suggestion = resolve_empty_result_suggestion(
            session,
            domain_key="folha_cargos",
            filters=params.filtros,
            default_suggestion="Nenhum registro de folha encontrado com os filtros.",
        )
        metadata = AgregarFolhaCargosMetadata(
            filtros_aplicados=params.filtros.to_metadata_dict(),
            agrupar_por=params.agrupar_por,
            metrica=params.metrica,
            ordenar_por=params.ordenar_por,
            ordem=params.ordem,
            limite=params.limite,
        )

        if params.agrupar_por is None:
            total_match, valor_total = execute_statement_total(
                session,
                count_stmt=_apply_filters(
                    _base_joined_stmt().add_columns(func.count()),
                    params.filtros,
                ),
                value_stmt=_apply_filters(
                    _base_joined_stmt().add_columns(metric_expression),
                    params.filtros,
                ),
            )
            return build_aggregate_response(
                response_type=AgregarFolhaCargosResponse,
                metadata=metadata,
                execution=AggregateExecutionResult(
                    valor_total=decimal_or_int_to_json(valor_total),
                    source_count=total_match,
                    suggestion=(empty_suggestion if total_match == 0 else None),
                ),
            )

        group_column = FolhaCargo.nome
        grouped_stmt = _apply_filters(
            _base_joined_stmt()
            .add_columns(group_column.label(params.agrupar_por), metric_expression)
            .group_by(group_column),
            params.filtros,
        )
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
            count_stmt=_apply_filters(
                _base_joined_stmt().add_columns(func.count()),
                params.filtros,
            ),
            value_stmt=_apply_filters(
                _base_joined_stmt().add_columns(metric_expression),
                params.filtros,
            ),
        )

    return build_aggregate_response(
        response_type=AgregarFolhaCargosResponse,
        metadata=metadata,
        execution=AggregateExecutionResult(
            total_grupos=total_grupos,
            rows=rows,
            valor_total=decimal_or_int_to_json(valor_total),
            source_count=total_match,
            suggestion=(empty_suggestion if not rows else None),
        ),
        item_model=AgregacaoFolhaCargosItem,
        agrupar_por=params.agrupar_por,
        metrica=params.metrica,
        serialize_metric=decimal_or_int_to_json,
    )
