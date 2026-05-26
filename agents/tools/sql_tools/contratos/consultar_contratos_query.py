"""Tool publica para consultas amplas do dominio de contratos."""

from __future__ import annotations

from typing import Any

from pydantic import ValidationError
from sqlalchemy import func, literal, select

from agents.tools.registry import PUBLIC_SCOPE, register
from database import session as session_manager
from database.models import Contrato

from .consultar_contratos_schema import (
    ConsultarContratosMetadata,
    ConsultarContratosParams,
    ConsultarContratosResponse,
)
from .shared.filters import ALLOWED_CONTRACT_FIELDS, ContratosFiltroSchema
from .shared.querying import (
    apply_contratos_filters,
    build_descricao_despesa_unavailable_message,
    contratos_supports_descricao_despesa,
    project_contrato_fields,
)


CONTRACT_ORDER_COLUMNS = {
    "numero": Contrato.numero,
    "fornecedor": Contrato.fornecedor,
    "valor": Contrato.valor,
    "data_inicio": Contrato.data_inicio,
    "data_fim": Contrato.data_fim,
    "categoria": Contrato.categoria,
    "secretaria": Contrato.secretaria,
}


def _fetch_contratos(
    session,
    params: ConsultarContratosParams,
    filtros: ContratosFiltroSchema,
    *,
    include_descricao_despesa: bool,
) -> tuple[int, list[dict[str, Any]]]:
    """Executa a consulta principal de contratos com os filtros informados."""

    descricao_despesa_column = (
        Contrato.descricao_despesa.label("classificacao_da_despesa")
        if include_descricao_despesa
        else literal(None).label("classificacao_da_despesa")
    )
    base_stmt = apply_contratos_filters(
        select(
            Contrato.id.label("id"),
            Contrato.numero.label("numero"),
            Contrato.fornecedor.label("fornecedor"),
            Contrato.cnpj.label("documento_fornecedor"),
            Contrato.valor.label("valor"),
            Contrato.data_inicio.label("data_inicio"),
            Contrato.data_fim.label("data_fim"),
            Contrato.categoria.label("categoria"),
            Contrato.secretaria.label("secretaria"),
            Contrato.descricao.label("descricao"),
            descricao_despesa_column,
        ),
        filtros,
        include_descricao_despesa=include_descricao_despesa,
    )
    total = session.execute(
        select(func.count()).select_from(base_stmt.order_by(None).subquery())
    ).scalar_one()

    order_column = CONTRACT_ORDER_COLUMNS[params.ordenar_por]
    ordered_stmt = base_stmt.order_by(
        order_column.desc() if params.ordem == "desc" else order_column.asc(),
        Contrato.id.desc(),
    )
    contratos = [
        dict(row)
        for row in session.execute(
            ordered_stmt.offset(params.offset).limit(params.limite)
        ).mappings()
    ]
    return total, contratos


@register(
    name="consultar_contratos",
    scope=PUBLIC_SCOPE,
    tags=["domain:contratos", "shape:lookup"],
)
def consultar_contratos(
    filtros: dict[str, Any] | None = None,
    ordenar_por: str = "data_inicio",
    ordem: str = "desc",
    limite: int = 10,
    offset: int = 0,
    campos: list[str] | None = None,
) -> dict[str, Any]:
    """
    Consulta contratos por filtros, ordenacao e campos de retorno.

    Use para listagens, busca por fornecedor, secretaria, categoria e periodo,
    alem de rankings simples por ordenacao.
    """
    try:
        params = ConsultarContratosParams.model_validate(
            {
                "filtros": filtros,
                "ordenar_por": ordenar_por,
                "ordem": ordem,
                "limite": limite,
                "offset": offset,
                "campos": campos,
            }
        )
    except ValidationError as exc:
        fallback_metadata = ConsultarContratosMetadata(
            ordenar_por="data_inicio",
            ordem="desc",
            limite=10,
            offset=0,
        )
        return ConsultarContratosResponse(
            total=0,
            resultados=[],
            metadata=fallback_metadata,
            mensagem=f"Parametros invalidos: {exc}",
        ).model_dump(mode="json")

    with session_manager.get_session() as session:
        include_descricao_despesa = contratos_supports_descricao_despesa(session)
        filtros_execucao = params.filtros
        total, contratos = _fetch_contratos(
            session,
            params,
            filtros_execucao,
            include_descricao_despesa=include_descricao_despesa,
        )
        fallback_filters = params.filtros.build_fornecedor_descricao_fallback()
        fallback_aplicado = False

        if total == 0 and fallback_filters is not None:
            fallback_total, fallback_contratos = _fetch_contratos(
                session,
                params,
                fallback_filters,
                include_descricao_despesa=include_descricao_despesa,
            )
            if fallback_total > 0:
                filtros_execucao = fallback_filters
                total = fallback_total
                contratos = fallback_contratos
                fallback_aplicado = True

    metadata = ConsultarContratosMetadata(
        filtros_aplicados=params.filtros.to_metadata_dict(),
        filtros_fallback_aplicados=(
            filtros_execucao.to_metadata_dict() if fallback_aplicado else None
        ),
        ordenar_por=params.ordenar_por,
        ordem=params.ordem,
        limite=params.limite,
        offset=params.offset,
        campos=params.campos or list(ALLOWED_CONTRACT_FIELDS),
    )

    if not contratos:
        sugestao = "Nenhum contrato encontrado com os filtros informados."
        if not include_descricao_despesa:
            sugestao = (
                build_descricao_despesa_unavailable_message(params.filtros)
                or sugestao
            )
        return ConsultarContratosResponse(
            total=0,
            resultados=[],
            metadata=metadata,
            sugestao=sugestao,
        ).model_dump(mode="json")

    resultados = [
        project_contrato_fields(contrato, params.campos) for contrato in contratos
    ]
    mensagens: list[str] = []
    if not include_descricao_despesa:
        warning = build_descricao_despesa_unavailable_message(params.filtros)
        if warning is not None:
            mensagens.append(warning)
    if fallback_aplicado:
        mensagens.append(
            "Nenhum contrato foi encontrado pelo fornecedor informado. "
            "Exibindo contratos relacionados pela descricao."
        )
    if total > len(resultados):
        mensagens.append(
            f"Mostrando {len(resultados)} de {total} registros encontrados."
        )
    mensagem = " ".join(mensagens) or None

    return ConsultarContratosResponse(
        total=total,
        resultados=resultados,
        metadata=metadata,
        mensagem=mensagem,
    ).model_dump(mode="json")
