"""Tool publica para consultas do quadro de pessoal."""

from __future__ import annotations

from typing import Any

from agents.tools.registry import PUBLIC_SCOPE, register, routing_metadata
from agents.tools.sql_tools.shared.lookup import (
    LookupExecutionResult,
    build_lookup_response,
    execute_collection_lookup,
)
from agents.tools.sql_tools.shared.validation import validate_tool_params
from database import session as session_manager
from database.models import QuadroPessoal
from shared.utils.text import matches_text_query

from .consultar_quadro_pessoal_schema import (
    ALLOWED_QUADRO_FIELDS,
    ConsultarQuadroPessoalMetadata,
    ConsultarQuadroPessoalParams,
    ConsultarQuadroPessoalResponse,
    QuadroPessoalFiltroSchema,
)


def _saldo_vagas(registro: QuadroPessoal) -> int | None:
    if registro.vagas_criadas is None or registro.vagas_preenchidas is None:
        return None
    return registro.vagas_criadas - registro.vagas_preenchidas


def _row_to_public_dict(registro: QuadroPessoal) -> dict[str, Any]:
    return {
        "origem": registro.origem,
        "mes_de_referencia": registro.competencia_referencia.isoformat(),
        "regime": registro.regime_contratacao,
        "vagas_criadas": registro.vagas_criadas,
        "vagas_preenchidas": registro.vagas_preenchidas,
        "saldo_vagas": _saldo_vagas(registro),
    }


def load_filtered_quadro_pessoal(
    session,
    filtros: QuadroPessoalFiltroSchema,
) -> list[QuadroPessoal]:
    registros = session.query(QuadroPessoal).all()

    if filtros.origem:
        registros = [
            r for r in registros if matches_text_query(r.origem, filtros.origem)
        ]
    if filtros.ano:
        registros = [
            r for r in registros if r.competencia_referencia.year == filtros.ano
        ]
    if filtros.mes:
        registros = [
            r for r in registros if r.competencia_referencia.month == filtros.mes
        ]
    if filtros.regime:
        registros = [
            r
            for r in registros
            if matches_text_query(r.regime_contratacao, filtros.regime)
        ]

    return registros


SORT_FIELD_GETTERS = {
    "mes_de_referencia": lambda registro: registro.competencia_referencia,
    "origem": lambda registro: registro.origem,
    "regime": lambda registro: registro.regime_contratacao,
    "vagas_criadas": lambda registro: registro.vagas_criadas or 0,
    "vagas_preenchidas": lambda registro: registro.vagas_preenchidas or 0,
    "saldo_vagas": lambda registro: _saldo_vagas(registro) or 0,
}


def project_quadro_pessoal_fields(
    registro: QuadroPessoal,
    campos: list[str],
) -> dict[str, Any]:
    selected = campos or list(ALLOWED_QUADRO_FIELDS)
    return {
        campo: value
        for campo, value in _row_to_public_dict(registro).items()
        if campo in selected
    }


@register(
    name="consultar_quadro_pessoal",
    scope=PUBLIC_SCOPE,
    tags=["domain:quadro_pessoal", "shape:lookup"],
    routing=routing_metadata(
        examples=[
            "Mostre o quadro de pessoal da prefeitura em 2025.",
            "Quais vagas estao preenchidas na saude?",
        ],
        hints=[
            "quadro de pessoal",
            "vaga",
            "regime",
            "origem",
            "lista",
        ],
    ),
)
def consultar_quadro_pessoal(
    filtros: dict[str, Any] | None = None,
    ordenar_por: str = "mes_de_referencia",
    ordem: str = "asc",
    limite: int = 10,
    offset: int = 0,
    campos: list[str] | None = None,
) -> dict[str, Any]:
    """
    Lista registros de vagas criadas e preenchidas do quadro de pessoal.

    Use esta tool quando a pergunta pedir vagas, saldo de vagas ou quadro de
    pessoal por regime, competencia e origem.
    NAO use para listar pessoas, nomes ou salarios de servidores; para isso use
    `consultar_servidores` ou `buscar_historico_de_pagamentos_do_servidor`.
    NAO use para totais, comparacoes ou rankings agregados; para isso use
    `agregar_quadro_pessoal`.

    Args:
        filtros: Objeto com filtros opcionais. Campos aceitos: `origem`, `ano`,
            `mes` e `regime`.
        ordenar_por: Campo de ordenacao. Aceita `mes_de_referencia`, `origem`,
            `regime`, `vagas_criadas`, `vagas_preenchidas` ou `saldo_vagas`.
        ordem: Direcao da ordenacao: `asc` ou `desc`.
        limite: Tamanho da pagina. Inteiro de 1 a 100.
        offset: Deslocamento da pagina. Inteiro maior ou igual a 0.
        campos: Lista opcional com qualquer subconjunto dos campos publicos do
            quadro de pessoal retornados em cada item.

    Returns:
        dict com:
        - `total`: total de registros encontrados antes da paginacao.
        - `resultados`: lista de registros; cada item pode incluir `origem`,
          `mes_de_referencia`, `regime`, `vagas_criadas`,
          `vagas_preenchidas` e `saldo_vagas`.
        - `metadata`: filtros aplicados, ordenacao, paginacao e campos pedidos.
        - `mensagem`: aviso quando a resposta estiver paginada.
        - `sugestao`: dica quando nenhum registro for encontrado.
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
        schema_type=ConsultarQuadroPessoalParams,
        on_error=lambda exc: ConsultarQuadroPessoalResponse(
            total=0,
            resultados=[],
            metadata=ConsultarQuadroPessoalMetadata(
                ordenar_por="mes_de_referencia",
                ordem="asc",
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
        registros = load_filtered_quadro_pessoal(session, params.filtros)
        total, pagina = execute_collection_lookup(
            registros,
            ordenar_por=params.ordenar_por,
            ordem=params.ordem,
            offset=params.offset,
            limite=params.limite,
            sort_key_getters=SORT_FIELD_GETTERS,
        )

    metadata = ConsultarQuadroPessoalMetadata(
        filtros_aplicados=params.filtros.to_metadata_dict(),
        ordenar_por=params.ordenar_por,
        ordem=params.ordem,
        limite=params.limite,
        offset=params.offset,
        campos=params.campos or list(ALLOWED_QUADRO_FIELDS),
    )

    return build_lookup_response(
        response_type=ConsultarQuadroPessoalResponse,
        metadata=metadata,
        execution=LookupExecutionResult(
            total=total,
            rows=pagina,
            suggestion=(
                "Nenhum registro de quadro de pessoal encontrado."
                if not pagina
                else None
            ),
        ),
        project_row=project_quadro_pessoal_fields,
        campos=params.campos,
    )
