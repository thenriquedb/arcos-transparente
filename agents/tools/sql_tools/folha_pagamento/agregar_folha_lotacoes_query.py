"""Tool publica para agregacoes de folha de pagamento por lotacao."""

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
from database.models import FolhaCargo, FolhaLotacao, FolhaPagamentoRegistro
from database.session import _normalizar_texto
from shared.utils.decimal_to_float import decimal_or_int_to_json

from .agregar_folha_lotacoes_schema import (
    AgregacaoFolhaLotacoesItem,
    AgregarFolhaLotacoesMetadata,
    AgregarFolhaLotacoesParams,
    AgregarFolhaLotacoesResponse,
)


def _apply_filters(stmt, filtros):
    if filtros.ano is not None:
        stmt = stmt.where(FolhaPagamentoRegistro.competencia_ano == filtros.ano)
    if filtros.mes is not None:
        stmt = stmt.where(FolhaPagamentoRegistro.competencia_mes_num == filtros.mes)
    if filtros.lotacao:
        normalized = _normalizar_texto(filtros.lotacao) or ""
        stmt = stmt.where(FolhaLotacao.nome.ilike(f"%{normalized}%"))
    if filtros.cargo:
        stmt = stmt.join(FolhaCargo, FolhaPagamentoRegistro.cargo_id == FolhaCargo.id, isouter=True)
        normalized_c = _normalizar_texto(filtros.cargo) or ""
        stmt = stmt.where(FolhaCargo.nome.ilike(f"%{normalized_c}%"))
    if filtros.servidor:
        from database.models import FolhaServidor

        stmt = stmt.join(FolhaServidor, FolhaPagamentoRegistro.servidor_id == FolhaServidor.id, isouter=True)
        normalized_s = _normalizar_texto(filtros.servidor) or ""
        stmt = stmt.where(func.normalizar(FolhaServidor.nome).like(f"%{normalized_s}%"))
    return stmt


def _base_joined_stmt():
    return (
        select()
        .select_from(FolhaPagamentoRegistro)
        .join(FolhaLotacao, FolhaPagamentoRegistro.lotacao_id == FolhaLotacao.id)
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
    name=ToolName.AGREGAR_FOLHA_LOTACOES,
    scope=PUBLIC_SCOPE,
    tags=["domain:folha", "shape:aggregate"],
    routing=routing_metadata(
        examples=[
            "Qual secretaria tem maior massa salarial em 2025?",
            "Ranking de lotacoes por total de liquido pago.",
            "Qual unidade organizacional tem mais servidores na folha?",
        ],
        hints=[
            "lotacao",
            "secretaria",
            "massa salarial lotacao",
            "ranking secretaria",
            "liquido por lotacao",
            "folha por secretaria",
            "total pago lotacao",
        ],
    ),
)
def agregar_folha_lotacoes(
    filtros: dict[str, Any] | None = None,
    agrupar_por: str | None = None,
    metrica: str = "contagem",
    ordenar_por: str = "metrica",
    ordem: str = "desc",
    limite: int = 10,
) -> dict[str, Any]:
    """
    Agrega registros de folha de pagamento agrupados por lotacao.

    A lotacao e a unidade organizacional real de alocacao do servidor, mais
    precisa que o campo `secretaria` em `agregar_servidores`. Expoe metricas
    de proventos, vencimentos totais, descontos e valor liquido.
    Use esta tool para rankings de secretarias ou unidades por massa salarial,
    total pago ou contagem de servidores distintos.
    NAO use para ver detalhes individuais; para isso use
    `consultar_folha_lotacoes`.

    Args:
        filtros: Objeto com filtros opcionais. Campos aceitos: `lotacao`,
            `servidor`, `cargo`, `ano` e `mes` (inteiro de 1 a 12).
        agrupar_por: Aceita `lotacao` ou `None`. Quando `None`, retorna
            `valor_total` sem agrupamento.
        metrica: Metrica calculada. Aceita `contagem`,
            `soma_salario_base`, `soma_vencimentos_totais`,
            `soma_descontos` ou `soma_liquido`.
        ordenar_por: Aceita `metrica` ou `lotacao`.
        ordem: Direcao da ordenacao: `asc` ou `desc`.
        limite: Quantidade maxima de grupos. Inteiro de 1 a 100.

    Returns:
        dict com:
        - `total_grupos`: total de grupos encontrados.
        - `resultados`: lista de grupos com a lotacao e a metrica calculada.
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
        schema_type=AgregarFolhaLotacoesParams,
        on_error=lambda exc: AgregarFolhaLotacoesResponse(
            total_grupos=0,
            resultados=[],
            metadata=AgregarFolhaLotacoesMetadata(
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
            domain_key="folha_lotacoes",
            filters=params.filtros,
            default_suggestion="Nenhum registro de folha encontrado com os filtros.",
        )
        metadata = AgregarFolhaLotacoesMetadata(
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
                response_type=AgregarFolhaLotacoesResponse,
                metadata=metadata,
                execution=AggregateExecutionResult(
                    valor_total=decimal_or_int_to_json(valor_total),
                    source_count=total_match,
                    suggestion=(empty_suggestion if total_match == 0 else None),
                ),
            )

        group_column = FolhaLotacao.nome
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
        response_type=AgregarFolhaLotacoesResponse,
        metadata=metadata,
        execution=AggregateExecutionResult(
            total_grupos=total_grupos,
            rows=rows,
            valor_total=decimal_or_int_to_json(valor_total),
            source_count=total_match,
            suggestion=(empty_suggestion if not rows else None),
        ),
        item_model=AgregacaoFolhaLotacoesItem,
        agrupar_por=params.agrupar_por,
        metrica=params.metrica,
        serialize_metric=decimal_or_int_to_json,
    )
