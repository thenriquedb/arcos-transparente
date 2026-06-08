"""Tool publica para consultas de passagens."""

from __future__ import annotations

from datetime import date
from decimal import Decimal
from typing import Any

from agents.tools.registry import PUBLIC_SCOPE, register, routing_metadata
from agents.tools.sql_tools.shared.lookup import (
    build_lookup_response,
    execute_collection_lookup_result,
)
from agents.tools.sql_tools.shared.projection import project_public_fields
from agents.tools.sql_tools.shared.validation import validate_tool_params
from database import session as session_manager
from database.models import DespesaDocumento
from shared.utils.decimal_to_float import decimal_to_float
from shared.utils.text import matches_text_query

from .consultar_passagens_schema import (
    ALLOWED_PASSAGENS_FIELDS,
    ConsultarPassagensMetadata,
    ConsultarPassagensParams,
    ConsultarPassagensResponse,
    PassagemFiltroSchema,
)


def _period_end(registro: DespesaDocumento) -> date:
    return registro.periodo_referencia_fim or registro.data_documento


def _period_start(registro: DespesaDocumento) -> date:
    return registro.periodo_referencia_inicio or registro.data_documento


def _row_to_public_dict(registro: DespesaDocumento) -> dict[str, Any]:
    return {
        "origem": registro.origem,
        "ano": registro.exercicio,
        "periodo_inicio": (
            _period_start(registro).isoformat() if _period_start(registro) else None
        ),
        "periodo_fim": _period_end(registro).isoformat()
        if _period_end(registro)
        else None,
        "beneficiario": registro.credor,
        "unidade_gestora": registro.unidade_gestora,
        "categoria": registro.categoria_documento,
        "valor_empenhado": decimal_to_float(registro.valor_empenhado),
        "valor_em_liquidacao": decimal_to_float(registro.valor_liquidacao),
        "valor_liquidado": decimal_to_float(registro.valor_liquidado),
        "valor_pago": decimal_to_float(registro.valor_pago),
        "valor_anulado": decimal_to_float(registro.valor_anulado),
    }


def load_filtered_passagens(
    session,
    filtros: PassagemFiltroSchema,
) -> list[DespesaDocumento]:
    registros = (
        session.query(DespesaDocumento)
        .filter(DespesaDocumento.tipo_origem == "passagem")
        .all()
    )

    if filtros.origem:
        registros = [
            r for r in registros if matches_text_query(r.origem, filtros.origem)
        ]
    if filtros.ano:
        registros = [r for r in registros if r.exercicio == filtros.ano]
    if filtros.beneficiario:
        registros = [
            r for r in registros if matches_text_query(r.credor, filtros.beneficiario)
        ]
    if filtros.cpf_cnpj:
        registros = [
            r for r in registros if matches_text_query(r.cpf_cnpj, filtros.cpf_cnpj)
        ]
    if filtros.unidade_gestora:
        registros = [
            r
            for r in registros
            if matches_text_query(r.unidade_gestora, filtros.unidade_gestora)
        ]
    if filtros.categoria:
        registros = [
            r
            for r in registros
            if matches_text_query(r.categoria_documento, filtros.categoria)
        ]
    if filtros.periodo_inicio:
        registros = [r for r in registros if _period_end(r) >= filtros.periodo_inicio]
    if filtros.periodo_fim:
        registros = [r for r in registros if _period_start(r) <= filtros.periodo_fim]

    return registros


SORT_FIELD_GETTERS = {
    "periodo_fim": lambda registro: _period_end(registro),
    "valor_empenhado": lambda registro: registro.valor_empenhado or Decimal("0"),
    "valor_liquidado": lambda registro: registro.valor_liquidado or Decimal("0"),
    "valor_pago": lambda registro: registro.valor_pago or Decimal("0"),
    "beneficiario": lambda registro: registro.credor or "",
    "categoria": lambda registro: registro.categoria_documento or "",
}


def project_passagem_fields(
    registro: DespesaDocumento,
    campos: list[str],
) -> dict[str, Any]:
    return project_public_fields(
        registro,
        campos,
        serializer=_row_to_public_dict,
        default_fields=ALLOWED_PASSAGENS_FIELDS,
    )


@register(
    name="consultar_passagens",
    scope=PUBLIC_SCOPE,
    tags=["domain:passagens", "shape:lookup"],
    routing=routing_metadata(
        examples=[
            "Quem recebeu passagens em 2026?",
            "Liste despesas com locomocao para Brasilia.",
        ],
        hints=[
            "passagem",
            "locomocao",
            "beneficiario",
            "destino",
            "lista",
        ],
    ),
)
def consultar_passagens(
    filtros: dict[str, Any] | None = None,
    ordenar_por: str = "periodo_fim",
    ordem: str = "desc",
    limite: int = 10,
    offset: int = 0,
    campos: list[str] | None = None,
) -> dict[str, Any]:
    """
    Lista registros consolidados de passagens por beneficiario e periodo.

    Use esta tool quando a pergunta pedir quem recebeu passagens, valores pagos,
    empenhados ou liquidados por beneficiario, origem ou periodo.
    Quando a pergunta vier em linguagem ampla de gasto, como "gastos com
    passagens" ou "quanto a prefeitura gastou com passagens", esta deve ser a
    resposta padrao para mostrar a lista detalhada que sustenta o valor.
    NAO use para totais, rankings ou contagens agregadas; para isso use
    `agregar_passagens`.
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
        schema_type=ConsultarPassagensParams,
        on_error=lambda exc: ConsultarPassagensResponse(
            total=0,
            resultados=[],
            metadata=ConsultarPassagensMetadata(
                ordenar_por="periodo_fim",
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
        registros = load_filtered_passagens(session, params.filtros)
        execution = execute_collection_lookup_result(
            registros,
            ordenar_por=params.ordenar_por,
            ordem=params.ordem,
            offset=params.offset,
            limite=params.limite,
            sort_key_getters=SORT_FIELD_GETTERS,
            empty_suggestion="Nenhuma passagem encontrada com os filtros.",
        )

    metadata = ConsultarPassagensMetadata(
        filtros_aplicados=params.filtros.to_metadata_dict(),
        ordenar_por=params.ordenar_por,
        ordem=params.ordem,
        limite=params.limite,
        offset=params.offset,
        campos=params.campos or list(ALLOWED_PASSAGENS_FIELDS),
    )

    return build_lookup_response(
        response_type=ConsultarPassagensResponse,
        metadata=metadata,
        execution=execution,
        project_row=project_passagem_fields,
        campos=params.campos,
        pagination_message_builder=lambda shown, total: (
            f"Mostrando {shown} de {total} passagens encontradas."
        ),
    )
