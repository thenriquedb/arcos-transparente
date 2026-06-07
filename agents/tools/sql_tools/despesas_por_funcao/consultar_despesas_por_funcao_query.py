"""Tool publica para consultas do relatorio `despesas-por-funcao`."""

from __future__ import annotations

from decimal import Decimal
from typing import Any

from agents.tools.registry import PUBLIC_SCOPE, register, routing_metadata
from agents.tools.sql_tools.shared.lookup import (
    LookupExecutionResult,
    build_lookup_response,
    execute_collection_lookup,
)
from agents.tools.sql_tools.shared.validation import validate_tool_params
from database import session as session_manager
from database.models import DespesaPorFuncao
from shared.utils.decimal_to_float import decimal_to_float
from shared.utils.text import matches_text_query

from .consultar_despesas_por_funcao_schema import (
    ConsultarDespesasPorFuncaoMetadata,
    ConsultarDespesasPorFuncaoParams,
    ConsultarDespesasPorFuncaoResponse,
    DEFAULT_DESPESAS_POR_FUNCAO_FIELDS,
    DESPESAS_POR_FUNCAO_BROAD_SPEND_GUIDANCE,
    DESPESAS_POR_FUNCAO_FIELD_EXPLANATIONS,
    DESPESAS_POR_FUNCAO_FINANCIAL_STAGE_FIELDS,
    DespesasPorFuncaoFiltroSchema,
)


def _row_to_public_dict(registro: DespesaPorFuncao) -> dict[str, Any]:
    return {
        "origem": registro.origem,
        "ano": registro.exercicio,
        "periodo_inicio": registro.periodo_inicio.isoformat(),
        "periodo_fim": registro.periodo_fim.isoformat(),
        "unidade_gestora": registro.unidade_gestora,
        "funcao": registro.funcao,
        "dotacao_inicial": decimal_to_float(registro.dotacao_inicial),
        "creditos_adicionais": decimal_to_float(registro.creditos_adicionais),
        "dotacao_atualizada": decimal_to_float(registro.dotacao_atualizada),
        "valor_empenhado": decimal_to_float(registro.valor_empenhado),
        "valor_em_liquidacao": decimal_to_float(registro.valor_em_liquidacao),
        "valor_liquidado": decimal_to_float(registro.valor_liquidado),
        "valor_pago": decimal_to_float(registro.valor_pago),
    }


def load_filtered_despesas_por_funcao(
    session,
    filtros: DespesasPorFuncaoFiltroSchema,
) -> list[DespesaPorFuncao]:
    registros = session.query(DespesaPorFuncao).all()

    if filtros.origem:
        registros = [
            r for r in registros if matches_text_query(r.origem, filtros.origem)
        ]
    if filtros.ano:
        registros = [r for r in registros if r.exercicio == filtros.ano]
    if filtros.periodo_inicio:
        registros = [r for r in registros if r.periodo_fim >= filtros.periodo_inicio]
    if filtros.periodo_fim:
        registros = [r for r in registros if r.periodo_inicio <= filtros.periodo_fim]
    if filtros.unidade_gestora:
        registros = [
            r
            for r in registros
            if matches_text_query(r.unidade_gestora, filtros.unidade_gestora)
        ]
    if filtros.funcao:
        registros = [
            r for r in registros if matches_text_query(r.funcao, filtros.funcao)
        ]
    if filtros.valor_pago_min is not None:
        registros = [
            r
            for r in registros
            if (r.valor_pago or Decimal("0")) >= filtros.valor_pago_min
        ]
    if filtros.valor_pago_max is not None:
        registros = [
            r
            for r in registros
            if (r.valor_pago or Decimal("0")) <= filtros.valor_pago_max
        ]

    return registros


SORT_FIELD_GETTERS = {
    "periodo_fim": lambda registro: registro.periodo_fim,
    "funcao": lambda registro: registro.funcao or "",
    "dotacao_atualizada": lambda registro: registro.dotacao_atualizada or Decimal("0"),
    "valor_empenhado": lambda registro: registro.valor_empenhado or Decimal("0"),
    "valor_liquidado": lambda registro: registro.valor_liquidado or Decimal("0"),
    "valor_pago": lambda registro: registro.valor_pago or Decimal("0"),
}


def project_despesas_por_funcao_fields(
    registro: DespesaPorFuncao,
    campos: list[str],
) -> dict[str, Any]:
    selected = campos or list(DEFAULT_DESPESAS_POR_FUNCAO_FIELDS)
    return {
        campo: value
        for campo, value in _row_to_public_dict(registro).items()
        if campo in selected
    }


def _field_explanations(campos: list[str]) -> dict[str, str]:
    return {
        campo: DESPESAS_POR_FUNCAO_FIELD_EXPLANATIONS[campo]
        for campo in campos
        if campo in DESPESAS_POR_FUNCAO_FIELD_EXPLANATIONS
    }


def _financial_stage_explanations() -> dict[str, str]:
    return {
        campo: DESPESAS_POR_FUNCAO_FIELD_EXPLANATIONS[campo]
        for campo in DESPESAS_POR_FUNCAO_FINANCIAL_STAGE_FIELDS
    }


@register(
    name="consultar_despesas_por_funcao",
    scope=PUBLIC_SCOPE,
    tags=["domain:despesas_por_funcao", "shape:lookup"],
    routing=routing_metadata(
        examples=[
            "Liste o relatorio de despesas por funcao de 2025.",
            "Quais valores pagos aparecem na funcao Saude no relatorio de despesas por funcao?",
        ],
        hints=[
            "despesas por funcao",
            "relatorio por funcao",
            "dotacao inicial",
            "valor pago",
            "dotacao atualizada",
        ],
    ),
)
def consultar_despesas_por_funcao(
    filtros: dict[str, Any] | None = None,
    ordenar_por: str = "periodo_fim",
    ordem: str = "desc",
    limite: int = 10,
    offset: int = 0,
    campos: list[str] | None = None,
) -> dict[str, Any]:
    """
    Lista linhas agregadas do relatorio `despesas-por-funcao`.

    Use esta tool quando a pergunta vier em linguagem ampla de gasto por
    funcao de governo, como "gastos da saude", "quanto foi gasto com
    educacao" ou "quanto a prefeitura gastou em urbanismo".
    Em perguntas como "qual foi o gasto com saude em 2025?", nao reduza a
    resposta a `valor_pago`: mostre tambem `valor_empenhado`,
    `valor_em_liquidacao`, `valor_liquidado` e explique a diferenca.
    Se o usuario ja informar um ano, como "em 2025", esse recorte ja basta;
    nao peca dia e mes para executar a consulta.
    NAO use para planejamento mensal por programa ou acao; para isso use
    `consultar_planejamento`.
    NAO use para empenhos, restos a pagar ou documentos executados
    individualmente; para isso use `consultar_despesas`.
    NAO use para totais, comparacoes ou rankings agregados; para isso use
    `agregar_despesas_por_funcao`.

    Returns:
        dict com:
        - `total`: total de linhas encontradas antes da paginacao.
        - `resultados`: lista de linhas do relatorio por funcao.
        - `metadata`: filtros aplicados, paginacao, campos retornados e a
          explicacao resumida de cada campo em `explicacao_campos`. Para
          perguntas amplas de gasto, use tambem `campos_financeiros_prioritarios`,
          `explicacao_estagios_despesa` e `orientacao_gasto_amplo`.
        - `mensagem`: aviso quando a resposta estiver paginada.
        - `sugestao`: dica quando nenhuma linha for encontrada.
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
        schema_type=ConsultarDespesasPorFuncaoParams,
        on_error=lambda exc: ConsultarDespesasPorFuncaoResponse(
            total=0,
            resultados=[],
            metadata=ConsultarDespesasPorFuncaoMetadata(
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
        registros = load_filtered_despesas_por_funcao(session, params.filtros)
        total, pagina = execute_collection_lookup(
            registros,
            ordenar_por=params.ordenar_por,
            ordem=params.ordem,
            offset=params.offset,
            limite=params.limite,
            sort_key_getters=SORT_FIELD_GETTERS,
        )

    campos_retorno = params.campos or list(DEFAULT_DESPESAS_POR_FUNCAO_FIELDS)

    metadata = ConsultarDespesasPorFuncaoMetadata(
        filtros_aplicados=params.filtros.to_metadata_dict(),
        ordenar_por=params.ordenar_por,
        ordem=params.ordem,
        limite=params.limite,
        offset=params.offset,
        campos=campos_retorno,
        explicacao_campos=_field_explanations(campos_retorno),
        campos_financeiros_prioritarios=list(
            DESPESAS_POR_FUNCAO_FINANCIAL_STAGE_FIELDS
        ),
        explicacao_estagios_despesa=_financial_stage_explanations(),
        orientacao_gasto_amplo=DESPESAS_POR_FUNCAO_BROAD_SPEND_GUIDANCE,
    )

    return build_lookup_response(
        response_type=ConsultarDespesasPorFuncaoResponse,
        metadata=metadata,
        execution=LookupExecutionResult(
            total=total,
            rows=pagina,
            suggestion=(
                "Nenhum registro de despesas por funcao encontrado com os filtros."
                if not pagina
                else None
            ),
        ),
        project_row=project_despesas_por_funcao_fields,
        campos=params.campos,
    )
