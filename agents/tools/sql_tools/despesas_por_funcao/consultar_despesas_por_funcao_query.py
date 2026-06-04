"""Tool publica para consultas do relatorio `despesas-por-funcao`."""

from __future__ import annotations

from decimal import Decimal
from typing import Any

from pydantic import ValidationError

from agents.tools.registry import PUBLIC_SCOPE, register, routing_metadata
from database import session as session_manager
from database.models import DespesaPorFuncao
from shared.utils.decimal_to_float import decimal_to_float
from shared.utils.text import matches_text_query

from .consultar_despesas_por_funcao_schema import (
    ALLOWED_DESPESAS_POR_FUNCAO_FIELDS,
    ConsultarDespesasPorFuncaoMetadata,
    ConsultarDespesasPorFuncaoParams,
    ConsultarDespesasPorFuncaoResponse,
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


def sort_despesas_por_funcao(
    registros: list[DespesaPorFuncao],
    ordenar_por: str,
    ordem: str,
) -> list[DespesaPorFuncao]:
    reverse = ordem == "desc"

    def key(registro: DespesaPorFuncao) -> Any:
        mapping = {
            "periodo_fim": registro.periodo_fim,
            "funcao": registro.funcao or "",
            "dotacao_atualizada": registro.dotacao_atualizada or Decimal("0"),
            "valor_empenhado": registro.valor_empenhado or Decimal("0"),
            "valor_liquidado": registro.valor_liquidado or Decimal("0"),
            "valor_pago": registro.valor_pago or Decimal("0"),
        }
        return mapping[ordenar_por]

    return sorted(registros, key=key, reverse=reverse)


def project_despesas_por_funcao(
    registros: list[DespesaPorFuncao],
    campos: list[str],
) -> list[dict[str, Any]]:
    selected = campos or list(ALLOWED_DESPESAS_POR_FUNCAO_FIELDS)
    return [
        {
            campo: value
            for campo, value in _row_to_public_dict(registro).items()
            if campo in selected
        }
        for registro in registros
    ]


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

    Use esta tool quando a pergunta citar explicitamente o relatorio
    `despesas-por-funcao` ou pedir os valores agregados por funcao, como
    dotacao inicial, creditos adicionais, dotacao atualizada, empenhado,
    liquidado ou pago por funcao e periodo.
    NAO use para planejamento mensal por programa ou acao; para isso use
    `consultar_planejamento`.
    NAO use para empenhos, restos a pagar ou documentos executados
    individualmente; para isso use `consultar_despesas`.
    NAO use para totais, comparacoes ou rankings agregados; para isso use
    `agregar_despesas_por_funcao`.
    """
    try:
        params = ConsultarDespesasPorFuncaoParams.model_validate(
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
        fallback_metadata = ConsultarDespesasPorFuncaoMetadata(
            ordenar_por="periodo_fim",
            ordem="desc",
            limite=10,
            offset=0,
        )
        return ConsultarDespesasPorFuncaoResponse(
            total=0,
            resultados=[],
            metadata=fallback_metadata,
            mensagem=f"Parametros invalidos: {exc}",
        ).model_dump(mode="json")

    with session_manager.get_session() as session:
        registros = load_filtered_despesas_por_funcao(session, params.filtros)
        total = len(registros)
        ordenados = sort_despesas_por_funcao(
            registros,
            params.ordenar_por,
            params.ordem,
        )
        pagina = ordenados[params.offset : params.offset + params.limite]
        resultados = project_despesas_por_funcao(pagina, params.campos)

    metadata = ConsultarDespesasPorFuncaoMetadata(
        filtros_aplicados=params.filtros.to_metadata_dict(),
        ordenar_por=params.ordenar_por,
        ordem=params.ordem,
        limite=params.limite,
        offset=params.offset,
        campos=params.campos or list(ALLOWED_DESPESAS_POR_FUNCAO_FIELDS),
    )

    if not resultados:
        return ConsultarDespesasPorFuncaoResponse(
            total=0,
            resultados=[],
            metadata=metadata,
            sugestao=(
                "Nenhum registro de despesas por funcao encontrado com os filtros."
            ),
        ).model_dump(mode="json")

    mensagem = None
    if total > params.offset + len(resultados):
        mensagem = f"Mostrando {len(resultados)} de {total} registros encontrados."

    return ConsultarDespesasPorFuncaoResponse(
        total=total,
        resultados=resultados,
        metadata=metadata,
        mensagem=mensagem,
    ).model_dump(mode="json")
