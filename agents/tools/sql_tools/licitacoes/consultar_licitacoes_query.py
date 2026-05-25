"""Tool publica para consultas amplas do dominio de licitacoes."""

from __future__ import annotations

from typing import Any

from pydantic import ValidationError
from sqlalchemy import func, select
from sqlalchemy.orm import selectinload

from agents.tools.registry import PUBLIC_SCOPE, register
from database import session as session_manager
from database.models import InstrumentoContratual, Licitacao
from shared.utils.decimal_to_float import decimal_to_float

from .consultar_licitacoes_schema import (
    ConsultarLicitacoesMetadata,
    ConsultarLicitacoesParams,
    ConsultarLicitacoesResponse,
)
from .shared.filters import ALLOWED_BIDDING_FIELDS
from .shared.querying import (
    apply_licitacoes_filters,
    matches_text_query,
    project_licitacao_fields,
)


BIDDING_ORDER_COLUMNS = {
    "numero": Licitacao.numero,
    "modalidade": Licitacao.modalidade,
    "valor_estimado": Licitacao.valor_estimado,
    "data_abertura": Licitacao.data_abertura,
    "situacao": Licitacao.situacao,
    "secretaria": Licitacao.secretaria,
}


@register(
    name="consultar_licitacoes",
    scope=PUBLIC_SCOPE,
    tags=["domain:licitacoes", "shape:lookup"],
)
def consultar_licitacoes(
    filtros: dict[str, Any] | None = None,
    ordenar_por: str = "data_abertura",
    ordem: str = "desc",
    limite: int = 10,
    offset: int = 0,
    campos: list[str] | None = None,
    incluir_detalhes: bool = False,
    max_vencedores: int = 5,
    max_instrumentos: int = 5,
    max_itens: int = 10,
) -> dict[str, Any]:
    """
    Consulta licitacoes por filtros, ordenacao e campos de retorno.

    Use para listagens, buscas por objeto, fornecedor, secretaria, situacao,
    modalidade e rankings simples por valor estimado.
    O retorno inclui `valor_total_estimado`, que soma todas as licitacoes
    encontradas pelos filtros, mesmo quando a lista exibida esta paginada.

    Exemplos:
    - 'quais licitacoes da saude?'
    - 'quais as 10 maiores licitacoes?'
    - 'detalhe a licitacao numero 12/2025'
    """
    try:
        params = ConsultarLicitacoesParams.model_validate(
            {
                "filtros": filtros,
                "ordenar_por": ordenar_por,
                "ordem": ordem,
                "limite": limite,
                "offset": offset,
                "campos": campos,
                "incluir_detalhes": incluir_detalhes,
                "max_vencedores": max_vencedores,
                "max_instrumentos": max_instrumentos,
                "max_itens": max_itens,
            }
        )
    except ValidationError as exc:
        fallback_metadata = ConsultarLicitacoesMetadata(
            ordenar_por="data_abertura",
            ordem="desc",
            limite=10,
            offset=0,
        )
        return ConsultarLicitacoesResponse(
            total=0,
            resultados=[],
            metadata=fallback_metadata,
            mensagem=f"Parametros invalidos: {exc}",
        ).model_dump(mode="json")

    with session_manager.get_session() as session:
        base_stmt = apply_licitacoes_filters(select(Licitacao), params.filtros)
        order_column = BIDDING_ORDER_COLUMNS[params.ordenar_por]
        ordered_stmt = base_stmt.order_by(
            order_column.desc() if params.ordem == "desc" else order_column.asc(),
            Licitacao.numero.asc(),
        )

        if params.incluir_detalhes:
            ordered_stmt = ordered_stmt.options(
                selectinload(Licitacao.vencedores),
                selectinload(Licitacao.instrumentos_contratuais).selectinload(
                    InstrumentoContratual.materias
                ),
                selectinload(Licitacao.instrumentos_contratuais).selectinload(
                    InstrumentoContratual.fornecedor
                ),
            )

        if params.filtros.objeto:
            todas_licitacoes_filtradas = [
                licitacao
                for licitacao in session.execute(ordered_stmt).scalars().all()
                if matches_text_query(licitacao.objeto, params.filtros.objeto)
            ]
            total = len(todas_licitacoes_filtradas)
            valor_total_estimado = sum(
                licitacao.valor_estimado for licitacao in todas_licitacoes_filtradas
            )
            licitacoes = todas_licitacoes_filtradas[
                params.offset : params.offset + params.limite
            ]
        else:
            total = session.execute(
                select(func.count()).select_from(base_stmt.order_by(None).subquery())
            ).scalar_one()
            total_subquery = base_stmt.order_by(None).subquery()
            valor_total_estimado = session.execute(
                select(func.coalesce(func.sum(total_subquery.c.valor_estimado), 0))
            ).scalar_one()
            licitacoes = (
                session.execute(ordered_stmt.offset(params.offset).limit(params.limite))
                .scalars()
                .all()
            )

        resultados = [
            project_licitacao_fields(
                licitacao,
                params.campos,
                incluir_detalhes=params.incluir_detalhes,
                max_vencedores=params.max_vencedores,
                max_instrumentos=params.max_instrumentos,
                max_itens=params.max_itens,
            )
            for licitacao in licitacoes
        ]

    metadata = ConsultarLicitacoesMetadata(
        filtros_aplicados=params.filtros.to_metadata_dict(),
        ordenar_por=params.ordenar_por,
        ordem=params.ordem,
        limite=params.limite,
        offset=params.offset,
        campos=params.campos or list(ALLOWED_BIDDING_FIELDS),
        incluir_detalhes=params.incluir_detalhes,
    )

    if not resultados:
        return ConsultarLicitacoesResponse(
            total=0,
            valor_total_estimado=0.0,
            resultados=[],
            metadata=metadata,
            sugestao="Nenhuma licitacao encontrada com os filtros informados.",
        ).model_dump(mode="json")

    mensagem = None
    if total > len(resultados):
        mensagem = f"Mostrando {len(resultados)} de {total} registros encontrados."

    return ConsultarLicitacoesResponse(
        total=total,
        valor_total_estimado=decimal_to_float(valor_total_estimado),
        resultados=resultados,
        metadata=metadata,
        mensagem=mensagem,
    ).model_dump(mode="json")
