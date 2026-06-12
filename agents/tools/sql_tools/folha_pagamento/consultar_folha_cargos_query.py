"""Tool publica para consultar registros de pagamento por cargo."""

from __future__ import annotations

from decimal import Decimal
from typing import Any

from sqlalchemy import select
from sqlalchemy.orm import joinedload

from agents.tools.names import ToolName
from agents.tools.registry import PUBLIC_SCOPE, register, routing_metadata
from agents.tools.sql_tools.shared.validation import validate_tool_params
from database import session as session_manager
from database.models import FolhaCargo, FolhaPagamentoRegistro
from database.session import _normalizar_texto
from shared.utils.decimal_to_float import decimal_to_float
from shared.utils.text import matches_text_query

from .consultar_folha_cargos_schema import (
    ALLOWED_FOLHA_CARGOS_FIELDS,
    ConsultarFolhaCargosMetadata,
    ConsultarFolhaCargosParams,
    ConsultarFolhaCargosResponse,
    FolhaCargosFiltroSchema,
)


def _load_pagamentos_por_cargo(
    session,
    filtros: FolhaCargosFiltroSchema,
) -> list[FolhaPagamentoRegistro]:
    stmt = (
        select(FolhaPagamentoRegistro)
        .options(
            joinedload(FolhaPagamentoRegistro.cargo),
            joinedload(FolhaPagamentoRegistro.servidor),
            joinedload(FolhaPagamentoRegistro.lotacao),
        )
        .join(FolhaCargo, FolhaPagamentoRegistro.cargo_id == FolhaCargo.id)
    )
    if filtros.ano is not None:
        stmt = stmt.where(FolhaPagamentoRegistro.competencia_ano == filtros.ano)
    if filtros.mes is not None:
        stmt = stmt.where(FolhaPagamentoRegistro.competencia_mes_num == filtros.mes)
    if filtros.cargo:
        normalized = _normalizar_texto(filtros.cargo) or ""
        stmt = stmt.where(FolhaCargo.nome.ilike(f"%{normalized}%"))
    if filtros.servidor:
        from database.models import FolhaServidor

        stmt = stmt.join(FolhaServidor, FolhaPagamentoRegistro.servidor_id == FolhaServidor.id)
        normalized_s = _normalizar_texto(filtros.servidor) or ""
        from sqlalchemy import func

        stmt = stmt.where(func.normalizar(FolhaServidor.nome).like(f"%{normalized_s}%"))
    return list(session.execute(stmt).unique().scalars())


def _sort_key(registro: FolhaPagamentoRegistro, ordenar_por: str) -> Any:
    mapping = {
        "competencia_ano": (registro.competencia_ano or 0, registro.competencia_mes_num or 0),
        "competencia_mes_num": (registro.competencia_mes_num or 0, registro.competencia_ano or 0),
        "cargo": registro.cargo.nome if registro.cargo else "",
        "servidor": registro.servidor.nome if registro.servidor else "",
        "salario_base": registro.salario_base or Decimal(0),
        "liquido": registro.liquido or Decimal(0),
        "vencimentos_totais": registro.vencimentos_totais or Decimal(0),
    }
    return mapping[ordenar_por]


def _row_to_public_dict(registro: FolhaPagamentoRegistro) -> dict[str, Any]:
    return {
        "cargo": registro.cargo.nome if registro.cargo else None,
        "servidor": registro.servidor.nome if registro.servidor else None,
        "lotacao": registro.lotacao.nome if registro.lotacao else None,
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
    name=ToolName.CONSULTAR_FOLHA_CARGOS,
    scope=PUBLIC_SCOPE,
    tags=["domain:folha", "shape:lookup"],
    routing=routing_metadata(
        examples=[
            "Liste os registros de pagamento dos professores em 2025.",
            "Quais sao os descontos dos agentes de saude?",
            "Mostre o detalhamento salarial do cargo de fiscal tributario.",
        ],
        hints=[
            "cargo",
            "folha por cargo",
            "proventos",
            "descontos folha",
            "liquido cargo",
            "vencimentos cargo",
            "detalhamento salarial",
        ],
    ),
)
def consultar_folha_cargos(
    filtros: dict[str, Any] | None = None,
    ordenar_por: str = "competencia_ano",
    ordem: str = "desc",
    limite: int = 20,
    offset: int = 0,
    campos: list[str] | None = None,
) -> dict[str, Any]:
    """
    Lista registros mensais de folha de pagamento filtrados por cargo.

    Expoe o detalhamento completo de cada registro: proventos, vantagens,
    vencimentos totais, descontos e valor liquido — campos que nao estao
    disponiveis em `consultar_servidores`.
    Use esta tool quando a pergunta mencionar cargo especifico e pedir
    detalhes de proventos, descontos, vencimentos ou valor liquido.
    NAO use para totais ou rankings por cargo; para isso use
    `agregar_folha_cargos`.
    NAO use para historico de pagamento de uma pessoa especifica; para isso
    use `buscar_historico_de_pagamentos_do_servidor`.

    Se `ano` nao for informado, todos os registros disponiveis sao retornados.
    Recomenda-se filtrar por `ano` para limitar o volume de dados.

    Args:
        filtros: Objeto com filtros opcionais. Campos aceitos: `cargo`, `servidor`,
            `ano` (inteiro, ex: 2025) e `mes` (inteiro de 1 a 12).
        ordenar_por: Aceita `competencia_ano`, `competencia_mes_num`, `cargo`,
            `servidor`, `salario_base`, `liquido` ou `vencimentos_totais`.
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
        schema_type=ConsultarFolhaCargosParams,
        on_error=lambda exc: ConsultarFolhaCargosResponse(
            total=0,
            resultados=[],
            metadata=ConsultarFolhaCargosMetadata(
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
        registros = _load_pagamentos_por_cargo(session, params.filtros)
        reverse = params.ordem == "desc"
        ordenados = sorted(registros, key=lambda r: _sort_key(r, params.ordenar_por), reverse=reverse)
        total = len(ordenados)
        pagina = ordenados[params.offset : params.offset + params.limite]
        resultados = [_row_to_public_dict(r) for r in pagina]
        if params.campos:
            resultados = [{k: v for k, v in row.items() if k in params.campos} for row in resultados]

    metadata = ConsultarFolhaCargosMetadata(
        filtros_aplicados=params.filtros.to_metadata_dict(),
        ordenar_por=params.ordenar_por,
        ordem=params.ordem,
        limite=params.limite,
        offset=params.offset,
        campos=params.campos or list(ALLOWED_FOLHA_CARGOS_FIELDS),
    )

    mensagem = None
    if total > params.offset + len(resultados):
        mensagem = f"Exibindo {len(resultados)} de {total} registros. Use limite e offset para navegar."

    return ConsultarFolhaCargosResponse(
        total=total,
        resultados=resultados,
        metadata=metadata,
        mensagem=mensagem,
        sugestao=("Nenhum registro de folha encontrado com os filtros." if not resultados else None),
    ).model_dump(mode="json")
