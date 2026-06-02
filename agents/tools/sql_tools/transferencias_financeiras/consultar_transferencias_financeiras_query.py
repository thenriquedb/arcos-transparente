"""Tool publica para consultas de transferencias financeiras e emendas."""

from __future__ import annotations

from datetime import date
from decimal import Decimal
from typing import Any

from pydantic import ValidationError

from agents.tools.registry import PUBLIC_SCOPE, register
from database import session as session_manager
from database.models import EmendaParlamentar, TransferenciaFinanceiraMovimento
from shared.utils.decimal_to_float import decimal_to_float
from shared.utils.text import matches_text_query

from .consultar_transferencias_financeiras_schema import (
    ALLOWED_TRANSFERENCIAS_FIELDS,
    ConsultarTransferenciasFinanceirasMetadata,
    ConsultarTransferenciasFinanceirasParams,
    ConsultarTransferenciasFinanceirasResponse,
    TransferenciasFinanceirasFiltroSchema,
)


def _movement_to_public_dict(
    registro: TransferenciaFinanceiraMovimento,
) -> dict[str, Any]:
    return {
        "tipo_registro": "movimentacao",
        "ano": registro.exercicio,
        "data": registro.data_movimento.isoformat()
        if registro.data_movimento
        else None,
        "identificacao": registro.identificacao,
        "unidade_concessora": registro.unidade_gestora_concessora,
        "unidade_recebedora": registro.unidade_gestora_recebedora,
        "tipo_movimento": registro.tipo_movimento,
        "finalidade": registro.finalidade,
        "fonte_recurso": registro.fonte_recurso,
        "detalhamento_fonte": registro.detalhamento_fonte,
        "programacao_inicial": decimal_to_float(registro.programacao_inicial),
        "valor": decimal_to_float(registro.valor_movimento),
        "exercicio_consulta": None,
        "ano_numero": None,
        "autor": None,
        "objeto": None,
        "tipo_emenda": None,
        "funcao": None,
    }


def _emenda_to_public_dict(registro: EmendaParlamentar) -> dict[str, Any]:
    return {
        "tipo_registro": "emenda",
        "ano": registro.ano,
        "data": None,
        "identificacao": None,
        "unidade_concessora": None,
        "unidade_recebedora": None,
        "tipo_movimento": None,
        "finalidade": None,
        "fonte_recurso": None,
        "detalhamento_fonte": None,
        "programacao_inicial": None,
        "valor": decimal_to_float(registro.valor),
        "exercicio_consulta": registro.exercicio_consulta,
        "ano_numero": registro.ano_numero,
        "autor": registro.autor,
        "objeto": registro.objeto,
        "tipo_emenda": registro.tipo_emenda,
        "funcao": registro.funcao,
    }


def _load_movimentacoes(session) -> list[dict[str, Any]]:
    registros = session.query(TransferenciaFinanceiraMovimento).all()
    return [_movement_to_public_dict(registro) for registro in registros]


def _load_emendas(session) -> list[dict[str, Any]]:
    registros = session.query(EmendaParlamentar).all()
    return [_emenda_to_public_dict(registro) for registro in registros]


def load_filtered_transferencias_financeiras(
    session,
    filtros: TransferenciasFinanceirasFiltroSchema,
) -> list[dict[str, Any]]:
    registros: list[dict[str, Any]] = []

    if filtros.tipo_registro in (None, "movimentacao"):
        registros.extend(_load_movimentacoes(session))
    if filtros.tipo_registro in (None, "emenda"):
        registros.extend(_load_emendas(session))

    if filtros.ano:
        registros = [r for r in registros if r.get("ano") == filtros.ano]
    if filtros.data_inicio:
        registros = [
            r
            for r in registros
            if r.get("data") is not None
            and date.fromisoformat(r["data"]) >= filtros.data_inicio
        ]
    if filtros.data_fim:
        registros = [
            r
            for r in registros
            if r.get("data") is not None
            and date.fromisoformat(r["data"]) <= filtros.data_fim
        ]
    if filtros.identificacao:
        registros = [
            r for r in registros if matches_text_query(r["identificacao"], filtros.identificacao)
        ]
    if filtros.unidade_concessora:
        registros = [
            r
            for r in registros
            if matches_text_query(r["unidade_concessora"], filtros.unidade_concessora)
        ]
    if filtros.unidade_recebedora:
        registros = [
            r
            for r in registros
            if matches_text_query(r["unidade_recebedora"], filtros.unidade_recebedora)
        ]
    if filtros.tipo_movimento:
        registros = [
            r for r in registros if matches_text_query(r["tipo_movimento"], filtros.tipo_movimento)
        ]
    if filtros.finalidade:
        registros = [
            r for r in registros if matches_text_query(r["finalidade"], filtros.finalidade)
        ]
    if filtros.fonte_recurso:
        registros = [
            r
            for r in registros
            if matches_text_query(r["fonte_recurso"], filtros.fonte_recurso)
        ]
    if filtros.exercicio_consulta:
        registros = [
            r
            for r in registros
            if r.get("exercicio_consulta") == filtros.exercicio_consulta
        ]
    if filtros.ano_numero:
        registros = [r for r in registros if matches_text_query(r["ano_numero"], filtros.ano_numero)]
    if filtros.autor:
        registros = [r for r in registros if matches_text_query(r["autor"], filtros.autor)]
    if filtros.objeto:
        registros = [r for r in registros if matches_text_query(r["objeto"], filtros.objeto)]
    if filtros.tipo_emenda:
        registros = [
            r for r in registros if matches_text_query(r["tipo_emenda"], filtros.tipo_emenda)
        ]
    if filtros.funcao:
        registros = [r for r in registros if matches_text_query(r["funcao"], filtros.funcao)]

    return registros


def sort_transferencias_financeiras(
    registros: list[dict[str, Any]],
    ordenar_por: str,
    ordem: str,
) -> list[dict[str, Any]]:
    reverse = ordem == "desc"

    def key(registro: dict[str, Any]) -> Any:
        if ordenar_por == "data":
            return registro.get("data") or ""
        if ordenar_por == "valor":
            return Decimal(str(registro.get("valor") or 0))
        if ordenar_por == "ano":
            return registro.get("ano") or 0
        return registro.get(ordenar_por) or ""

    return sorted(registros, key=key, reverse=reverse)


def project_transferencias_financeiras(
    registros: list[dict[str, Any]],
    campos: list[str],
) -> list[dict[str, Any]]:
    selected = campos or list(ALLOWED_TRANSFERENCIAS_FIELDS)
    return [
        {campo: valor for campo, valor in registro.items() if campo in selected}
        for registro in registros
    ]


@register(
    name="consultar_transferencias_financeiras",
    scope=PUBLIC_SCOPE,
    tags=["domain:transferencias_financeiras", "shape:lookup"],
)
def consultar_transferencias_financeiras(
    filtros: dict[str, Any] | None = None,
    ordenar_por: str = "data",
    ordem: str = "desc",
    limite: int = 10,
    offset: int = 0,
    campos: list[str] | None = None,
) -> dict[str, Any]:
    """
    Lista movimentos de transferencias financeiras e emendas parlamentares.

    Use esta tool quando a pergunta pedir repasses, recebimentos, devolucoes
    entre unidades publicas ou detalhes de emendas parlamentares.
    NAO use para totais, contagens ou rankings agregados; para isso use
    `agregar_transferencias_financeiras`.
    """
    try:
        params = ConsultarTransferenciasFinanceirasParams.model_validate(
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
        fallback_metadata = ConsultarTransferenciasFinanceirasMetadata(
            ordenar_por="data",
            ordem="desc",
            limite=10,
            offset=0,
        )
        return ConsultarTransferenciasFinanceirasResponse(
            total=0,
            resultados=[],
            metadata=fallback_metadata,
            mensagem=f"Parametros invalidos: {exc}",
        ).model_dump(mode="json")

    with session_manager.get_session() as session:
        registros = load_filtered_transferencias_financeiras(session, params.filtros)
        total = len(registros)
        ordenados = sort_transferencias_financeiras(
            registros,
            params.ordenar_por,
            params.ordem,
        )
        pagina = ordenados[params.offset : params.offset + params.limite]
        resultados = project_transferencias_financeiras(pagina, params.campos)

    metadata = ConsultarTransferenciasFinanceirasMetadata(
        filtros_aplicados=params.filtros.to_metadata_dict(),
        ordenar_por=params.ordenar_por,
        ordem=params.ordem,
        limite=params.limite,
        offset=params.offset,
        campos=params.campos or list(ALLOWED_TRANSFERENCIAS_FIELDS),
    )

    if not resultados:
        return ConsultarTransferenciasFinanceirasResponse(
            total=0,
            resultados=[],
            metadata=metadata,
            sugestao=(
                "Nenhum registro de transferencias financeiras encontrado com os filtros."
            ),
        ).model_dump(mode="json")

    mensagem = None
    if total > params.offset + len(resultados):
        mensagem = (
            f"Mostrando {len(resultados)} de {total} registros encontrados."
        )

    return ConsultarTransferenciasFinanceirasResponse(
        total=total,
        resultados=resultados,
        metadata=metadata,
        mensagem=mensagem,
    ).model_dump(mode="json")
