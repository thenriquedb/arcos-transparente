"""Tool publica para consultas amplas de receitas."""

from __future__ import annotations

from typing import Any

from pydantic import ValidationError

from agents.tools.registry import PUBLIC_SCOPE, register
from database import session as session_manager

from .consultar_receitas_schema import (
    ConsultarReceitasMetadata,
    ConsultarReceitasParams,
    ConsultarReceitasResponse,
)
from .shared.filters import ALLOWED_RECEITA_FIELDS
from .shared.querying import load_filtered_receitas, project_rows, sort_receitas


@register(
    name="consultar_receitas",
    scope=PUBLIC_SCOPE,
    tags=["domain:receitas", "shape:lookup"],
)
def consultar_receitas(
    filtros: dict[str, Any] | None = None,
    ordenar_por: str = "data",
    ordem: str = "desc",
    limite: int = 10,
    offset: int = 0,
    campos: list[str] | None = None,
) -> dict[str, Any]:
    """
    Consulta arrecadacoes efetivas ou lancamentos de receitas por filtros simples.

    Use `tipo_de_dado='arrecadacao'` para valores efetivamente recebidos.
    Use `tipo_de_dado='lancamento'` para impostos e valores apenas lancados.
    """
    try:
        params = ConsultarReceitasParams.model_validate(
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
        fallback_metadata = ConsultarReceitasMetadata(
            ordenar_por="data",
            ordem="desc",
            limite=10,
            offset=0,
        )
        return ConsultarReceitasResponse(
            total=0,
            resultados=[],
            metadata=fallback_metadata,
            mensagem=f"Parametros invalidos: {exc}",
        ).model_dump(mode="json")

    with session_manager.get_session() as session:
        registros = load_filtered_receitas(session, params.filtros)
        total = len(registros)
        ordenados = sort_receitas(registros, params.ordenar_por, params.ordem)
        pagina = ordenados[params.offset : params.offset + params.limite]

    metadata = ConsultarReceitasMetadata(
        filtros_aplicados=params.filtros.to_metadata_dict(),
        ordenar_por=params.ordenar_por,
        ordem=params.ordem,
        limite=params.limite,
        offset=params.offset,
        campos=params.campos or list(ALLOWED_RECEITA_FIELDS),
    )

    if not pagina:
        tipo_label = (
            "arrecadacoes" if params.filtros.tipo_de_dado == "arrecadacao" else "lancamentos"
        )
        return ConsultarReceitasResponse(
            total=0,
            resultados=[],
            metadata=metadata,
            sugestao=f"Nenhum registro de {tipo_label} encontrado com os filtros.",
        ).model_dump(mode="json")

    resultados = project_rows(pagina, params.campos)
    mensagem = None
    if total > len(resultados):
        mensagem = f"Mostrando {len(resultados)} de {total} registros encontrados."

    return ConsultarReceitasResponse(
        total=total,
        resultados=resultados,
        metadata=metadata,
        mensagem=mensagem,
    ).model_dump(mode="json")
