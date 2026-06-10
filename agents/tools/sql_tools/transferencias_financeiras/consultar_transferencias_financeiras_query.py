"""Tool publica para consultas de transferencias financeiras e emendas."""

from __future__ import annotations

from datetime import date
from decimal import Decimal
from typing import Any

from sqlalchemy import select

from agents.tools.registry import PUBLIC_SCOPE, register, routing_metadata
from agents.tools.sql_tools.shared.filtering import (
    apply_declared_filters,
    predicate_filter,
    text_filter,
)
from agents.tools.sql_tools.shared.lookup import (
    build_lookup_response,
    execute_collection_lookup_result,
)
from agents.tools.sql_tools.shared.projection import project_public_dict
from agents.tools.sql_tools.shared.validation import validate_tool_params
from database import session as session_manager
from database.models import EmendaParlamentar, TransferenciaFinanceiraMovimento
from shared.utils.decimal_to_float import decimal_to_float

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
    registros = list(
        session.execute(select(TransferenciaFinanceiraMovimento)).scalars()
    )
    return [_movement_to_public_dict(registro) for registro in registros]


def _load_emendas(session) -> list[dict[str, Any]]:
    registros = list(session.execute(select(EmendaParlamentar)).scalars())
    return [_emenda_to_public_dict(registro) for registro in registros]


_TRANSFERENCIAS_FILTER_CONDITIONS = (
    predicate_filter("ano", lambda r, v: r.get("ano") == v),
    predicate_filter(
        "data_inicio",
        lambda r, v: r.get("data") is not None and date.fromisoformat(r["data"]) >= v,
    ),
    predicate_filter(
        "data_fim",
        lambda r, v: r.get("data") is not None and date.fromisoformat(r["data"]) <= v,
    ),
    text_filter("identificacao", lambda r: r["identificacao"]),
    text_filter("unidade_concessora", lambda r: r["unidade_concessora"]),
    text_filter("unidade_recebedora", lambda r: r["unidade_recebedora"]),
    text_filter("tipo_movimento", lambda r: r["tipo_movimento"]),
    text_filter("finalidade", lambda r: r["finalidade"]),
    text_filter("fonte_recurso", lambda r: r["fonte_recurso"]),
    predicate_filter(
        "exercicio_consulta",
        lambda r, v: r.get("exercicio_consulta") == v,
    ),
    text_filter("ano_numero", lambda r: r["ano_numero"]),
    text_filter("autor", lambda r: r["autor"]),
    text_filter("objeto", lambda r: r["objeto"]),
    text_filter("tipo_emenda", lambda r: r["tipo_emenda"]),
    text_filter("funcao", lambda r: r["funcao"]),
)


def load_filtered_transferencias_financeiras(
    session,
    filtros: TransferenciasFinanceirasFiltroSchema,
) -> list[dict[str, Any]]:
    """Carrega os registros do dominio aplicando os filtros publicos."""

    registros: list[dict[str, Any]] = []

    if filtros.tipo_registro in (None, "movimentacao"):
        registros.extend(_load_movimentacoes(session))
    if filtros.tipo_registro in (None, "emenda"):
        registros.extend(_load_emendas(session))

    return apply_declared_filters(registros, filtros, _TRANSFERENCIAS_FILTER_CONDITIONS)


SORT_FIELD_GETTERS = {
    "ano": lambda registro: registro.get("ano") or 0,
    "data": lambda registro: registro.get("data") or "",
    "valor": lambda registro: Decimal(str(registro.get("valor") or 0)),
    "tipo_registro": lambda registro: registro.get("tipo_registro") or "",
    "unidade_recebedora": lambda registro: registro.get("unidade_recebedora") or "",
    "tipo_movimento": lambda registro: registro.get("tipo_movimento") or "",
    "autor": lambda registro: registro.get("autor") or "",
    "funcao": lambda registro: registro.get("funcao") or "",
    "ano_numero": lambda registro: registro.get("ano_numero") or "",
}


def project_transferencia_financeira_fields(
    registro: dict[str, Any],
    campos: list[str],
) -> dict[str, Any]:
    """Projeta o registro nos campos publicos solicitados."""

    return project_public_dict(
        registro,
        campos,
        default_fields=ALLOWED_TRANSFERENCIAS_FIELDS,
    )


@register(
    name="consultar_transferencias_financeiras",
    scope=PUBLIC_SCOPE,
    tags=["domain:transferencias_financeiras", "shape:lookup"],
    routing=routing_metadata(
        examples=[
            "Quanto foi transferido para a camara em 2026?",
            "Quais emendas parlamentares foram recebidas na saude?",
            "Liste as emendas do Nikolas Ferreira na saude em 2025.",
        ],
        hints=[
            "transferencia financeira",
            "repasse",
            "emenda parlamentar",
            "recebimento",
            "movimentacao",
            "autor da emenda",
            "funcao da emenda",
            "ano da emenda",
        ],
    ),
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
    entre unidades publicas ou detalhes de emendas parlamentares por autor,
    funcao, ano, tipo de emenda ou objeto.
    NAO use para totais, contagens ou rankings agregados; para isso use
    `agregar_transferencias_financeiras`.
    """
    validated = validate_tool_params(
        {
            "filtros": filtros,
            "ordenar_por": ordenar_por,
            "ordem": ordem,
            "limite": limite,
            "offset": offset,
            "campos": campos,
        },
        schema_type=ConsultarTransferenciasFinanceirasParams,
        on_error=lambda exc: ConsultarTransferenciasFinanceirasResponse(
            total=0,
            resultados=[],
            metadata=ConsultarTransferenciasFinanceirasMetadata(
                ordenar_por="data",
                ordem="desc",
                limite=10,
                offset=0,
            ),
            mensagem=f"Parametros invalidos: {exc}",
        ).model_dump(mode="json"),
    )
    if isinstance(validated, dict):
        return validated
    params = validated

    with session_manager.get_session() as session:
        registros = load_filtered_transferencias_financeiras(session, params.filtros)
        execution = execute_collection_lookup_result(
            registros,
            ordenar_por=params.ordenar_por,
            ordem=params.ordem,
            offset=params.offset,
            limite=params.limite,
            sort_key_getters=SORT_FIELD_GETTERS,
            empty_suggestion=(
                "Nenhum registro de transferencias financeiras encontrado com os filtros."
            ),
        )

    metadata = ConsultarTransferenciasFinanceirasMetadata(
        filtros_aplicados=params.filtros.to_metadata_dict(),
        ordenar_por=params.ordenar_por,
        ordem=params.ordem,
        limite=params.limite,
        offset=params.offset,
        campos=params.campos or list(ALLOWED_TRANSFERENCIAS_FIELDS),
    )

    return build_lookup_response(
        response_type=ConsultarTransferenciasFinanceirasResponse,
        metadata=metadata,
        execution=execution,
        project_row=project_transferencia_financeira_fields,
        campos=params.campos,
    )
