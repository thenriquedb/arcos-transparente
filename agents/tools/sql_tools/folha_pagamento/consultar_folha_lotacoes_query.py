"""Tool publica para consultar registros de pagamento por lotacao."""

from __future__ import annotations

from decimal import Decimal
from typing import Any

from sqlalchemy import select
from sqlalchemy.orm import joinedload

from agents.tools.names import ToolName
from agents.tools.registry import PUBLIC_SCOPE, register, routing_metadata
from agents.tools.sql_tools.shared.validation import validate_tool_params
from database import session as session_manager
from database.models import FolhaCargo, FolhaLotacao, FolhaPagamentoRegistro
from database.session import _normalizar_texto
from shared.utils.decimal_to_float import decimal_to_float

from .consultar_folha_lotacoes_schema import (
    ALLOWED_FOLHA_LOTACOES_FIELDS,
    ConsultarFolhaLotacoesMetadata,
    ConsultarFolhaLotacoesParams,
    ConsultarFolhaLotacoesResponse,
    FolhaLotacoesFiltroSchema,
)


def _load_pagamentos_por_lotacao(
    session,
    filtros: FolhaLotacoesFiltroSchema,
) -> list[FolhaPagamentoRegistro]:
    stmt = (
        select(FolhaPagamentoRegistro)
        .options(
            joinedload(FolhaPagamentoRegistro.lotacao),
            joinedload(FolhaPagamentoRegistro.servidor),
            joinedload(FolhaPagamentoRegistro.cargo),
        )
        .join(FolhaLotacao, FolhaPagamentoRegistro.lotacao_id == FolhaLotacao.id)
    )
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
        from sqlalchemy import func

        stmt = stmt.join(FolhaServidor, FolhaPagamentoRegistro.servidor_id == FolhaServidor.id, isouter=True)
        normalized_s = _normalizar_texto(filtros.servidor) or ""
        stmt = stmt.where(func.normalizar(FolhaServidor.nome).like(f"%{normalized_s}%"))
    return list(session.execute(stmt).unique().scalars())


def _sort_key(registro: FolhaPagamentoRegistro, ordenar_por: str) -> Any:
    mapping = {
        "competencia_ano": (registro.competencia_ano or 0, registro.competencia_mes_num or 0),
        "competencia_mes_num": (registro.competencia_mes_num or 0, registro.competencia_ano or 0),
        "lotacao": registro.lotacao.nome if registro.lotacao else "",
        "servidor": registro.servidor.nome if registro.servidor else "",
        "cargo": registro.cargo.nome if registro.cargo else "",
        "salario_base": registro.salario_base or Decimal(0),
        "liquido": registro.liquido or Decimal(0),
        "vencimentos_totais": registro.vencimentos_totais or Decimal(0),
    }
    return mapping[ordenar_por]


def _row_to_public_dict(registro: FolhaPagamentoRegistro) -> dict[str, Any]:
    return {
        "lotacao": registro.lotacao.nome if registro.lotacao else None,
        "servidor": registro.servidor.nome if registro.servidor else None,
        "cargo": registro.cargo.nome if registro.cargo else None,
        "competencia_ano": registro.competencia_ano,
        "competencia_mes": registro.competencia_mes_nome,
        "salario_base": decimal_to_float(registro.salario_base),
        "proventos": decimal_to_float(registro.proventos),
        "vantagens": decimal_to_float(registro.vantagens),
        "vencimentos_totais": decimal_to_float(registro.vencimentos_totais),
        "descontos": decimal_to_float(registro.descontos),
        "liquido": decimal_to_float(registro.liquido),
    }


@register(
    name=ToolName.CONSULTAR_FOLHA_LOTACOES,
    scope=PUBLIC_SCOPE,
    tags=["domain:folha", "shape:lookup"],
    routing=routing_metadata(
        examples=[
            "Liste os pagamentos da lotacao da secretaria de saude em 2025.",
            "Mostre o detalhamento salarial dos servidores da educacao.",
            "Quais os descontos dos servidores lotados no CAPS?",
        ],
        hints=[
            "lotacao",
            "folha por lotacao",
            "pagamento por secretaria",
            "detalhamento salarial lotacao",
            "proventos lotacao",
            "descontos lotacao",
        ],
    ),
)
def consultar_folha_lotacoes(
    filtros: dict[str, Any] | None = None,
    ordenar_por: str = "competencia_ano",
    ordem: str = "desc",
    limite: int = 20,
    offset: int = 0,
    campos: list[str] | None = None,
) -> dict[str, Any]:
    """
    Lista registros mensais de folha de pagamento filtrados por lotacao.

    Expoe o detalhamento completo de cada registro: proventos, vantagens,
    vencimentos totais, descontos e valor liquido — agrupados pela unidade
    organizacional real de alocacao do servidor (lotacao).
    Use esta tool quando a pergunta mencionar secretaria, departamento ou
    unidade organizacional e pedir detalhes de proventos, descontos ou liquido.
    NAO use para totais ou rankings por lotacao; para isso use
    `agregar_folha_lotacoes`.

    Se `ano` nao for informado, todos os registros sao retornados.
    Recomenda-se filtrar por `ano` para limitar o volume de dados.

    Args:
        filtros: Objeto com filtros opcionais. Campos aceitos: `lotacao`,
            `servidor`, `cargo`, `ano` e `mes` (inteiro de 1 a 12).
        ordenar_por: Aceita `competencia_ano`, `competencia_mes_num`,
            `lotacao`, `servidor`, `cargo`, `salario_base`, `liquido` ou
            `vencimentos_totais`.
        ordem: Direcao da ordenacao: `asc` ou `desc`.
        limite: Tamanho da pagina. Inteiro de 1 a 100.
        offset: Deslocamento da pagina. Inteiro maior ou igual a 0.
        campos: Lista opcional com subconjunto dos campos publicos.

    Returns:
        dict com:
        - `total`: total de registros encontrados antes da paginacao.
        - `resultados`: lista de registros com campos salariais detalhados.
        - `metadata`: filtros aplicados, ordenacao e paginacao.
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
        schema_type=ConsultarFolhaLotacoesParams,
        on_error=lambda exc: ConsultarFolhaLotacoesResponse(
            total=0,
            resultados=[],
            metadata=ConsultarFolhaLotacoesMetadata(
                ordenar_por="competencia_ano",
                ordem="desc",
                limite=20,
                offset=0,
            ),
            mensagem=f"Parametros invalidos: {exc}",
        ).model_dump(mode="json"),
    )
    if isinstance(validated, dict):
        return validated
    params = validated

    with session_manager.get_session() as session:
        registros = _load_pagamentos_por_lotacao(session, params.filtros)
        reverse = params.ordem == "desc"
        ordenados = sorted(registros, key=lambda r: _sort_key(r, params.ordenar_por), reverse=reverse)
        total = len(ordenados)
        pagina = ordenados[params.offset : params.offset + params.limite]
        resultados = [_row_to_public_dict(r) for r in pagina]
        if params.campos:
            resultados = [{k: v for k, v in row.items() if k in params.campos} for row in resultados]

    metadata = ConsultarFolhaLotacoesMetadata(
        filtros_aplicados=params.filtros.to_metadata_dict(),
        ordenar_por=params.ordenar_por,
        ordem=params.ordem,
        limite=params.limite,
        offset=params.offset,
        campos=params.campos or list(ALLOWED_FOLHA_LOTACOES_FIELDS),
    )

    mensagem = None
    if total > params.offset + len(resultados):
        mensagem = f"Exibindo {len(resultados)} de {total} registros. Use limite e offset para navegar."

    return ConsultarFolhaLotacoesResponse(
        total=total,
        resultados=resultados,
        metadata=metadata,
        mensagem=mensagem,
        sugestao=("Nenhum registro de folha encontrado com os filtros." if not resultados else None),
    ).model_dump(mode="json")
