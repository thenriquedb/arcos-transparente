"""Tool publica para consultas amplas de planejamento."""

from __future__ import annotations

from typing import Any

from pydantic import ValidationError

from agents.tools.registry import PUBLIC_SCOPE, register
from database import session as session_manager

from .consultar_planejamento_schema import (
    ConsultarPlanejamentoMetadata,
    ConsultarPlanejamentoParams,
    ConsultarPlanejamentoResponse,
)
from .shared.filters import ALLOWED_PLANNING_FIELDS
from .shared.querying import (
    load_filtered_planejamentos,
    project_rows,
    sort_planejamentos,
)


@register(
    name="consultar_planejamento",
    scope=PUBLIC_SCOPE,
    tags=["domain:planejamento", "shape:lookup"],
)
def consultar_planejamento(
    filtros: dict[str, Any] | None = None,
    ordenar_por: str = "mes_num",
    ordem: str = "asc",
    limite: int = 10,
    offset: int = 0,
    campos: list[str] | None = None,
) -> dict[str, Any]:
    """
    Consulta linhas do planejamento orcamentario por filtros e ordenacao.

    O filtro `origem` suporta ao menos `saude` e `prefeitura`.
    Se `origem` nao for informado, o padrao continua sendo `saude`.
    Use para listar acoes, programas, grupos de gasto e valores mensais.
    """
    try:
        params = ConsultarPlanejamentoParams.model_validate(
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
        fallback_metadata = ConsultarPlanejamentoMetadata(
            ordenar_por="mes_num",
            ordem="asc",
            limite=10,
            offset=0,
        )
        return ConsultarPlanejamentoResponse(
            total=0,
            resultados=[],
            metadata=fallback_metadata,
            mensagem=f"Parametros invalidos: {exc}",
        ).model_dump(mode="json")

    with session_manager.get_session() as session:
        registros = load_filtered_planejamentos(session, params.filtros)
        total = len(registros)
        ordenados = sort_planejamentos(registros, params.ordenar_por, params.ordem)
        pagina = ordenados[params.offset : params.offset + params.limite]

    metadata = ConsultarPlanejamentoMetadata(
        filtros_aplicados=params.filtros.to_metadata_dict(),
        ordenar_por=params.ordenar_por,
        ordem=params.ordem,
        limite=params.limite,
        offset=params.offset,
        campos=params.campos or list(ALLOWED_PLANNING_FIELDS),
    )

    if not pagina:
        return ConsultarPlanejamentoResponse(
            total=0,
            resultados=[],
            metadata=metadata,
            sugestao="Nenhum registro de planejamento encontrado com os filtros.",
        ).model_dump(mode="json")

    resultados = project_rows(pagina, params.campos)
    mensagem = None
    if total > len(resultados):
        mensagem = f"Mostrando {len(resultados)} de {total} registros encontrados."

    return ConsultarPlanejamentoResponse(
        total=total,
        resultados=resultados,
        metadata=metadata,
        mensagem=mensagem,
    ).model_dump(mode="json")
