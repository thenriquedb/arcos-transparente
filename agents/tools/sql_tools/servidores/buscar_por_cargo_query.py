"""Tool para buscar servidores por cargo."""

from __future__ import annotations

from typing import Any

from pydantic import ValidationError
from sqlalchemy import func, select

from agents.tools.registry import register
from database import session as session_manager
from database.models import Servidor

from .shared.params import BuscarServidorPorCargoParams
from .shared.responses import ServidoresToolResponse
from .shared.runtime import resposta_sem_resultados, serializar_servidor


def _executar_busca_textual(campo, termo: str, limite: int) -> list[Servidor]:
    termo_normalizado = termo.lower()

    with session_manager.get_session() as session:
        return (
            session.execute(
                select(Servidor)
                .where(func.lower(campo).like(f"%{termo_normalizado}%"))
                .order_by(Servidor.nome.asc())
                .limit(limite)
            )
            .scalars()
            .all()
        )


@register(name="buscar_servidores_por_cargo")
def buscar_servidores_por_cargo(cargo: str, limite: int = 10) -> dict[str, Any]:
    """
    Busca servidores por cargo.

    Examples:
        'quais servidores ocupam o cargo de Professor',
        'me mostre os servidores que são Médicos'.

    Args:
        cargo (str): O nome ou parte do nome do cargo a ser buscado.
        limite (int): O número máximo de resultados a serem retornados.
    Returns:
        dict com a query, total e resultados padronizados.
    """
    try:
        params = BuscarServidorPorCargoParams.model_validate(
            {"cargo": cargo, "limite": limite}
        )
    except ValidationError as exc:
        return resposta_sem_resultados(mensagem=f"Parametros invalidos: {exc}")

    if not params.cargo:
        return resposta_sem_resultados(
            query=cargo,
            mensagem="Informe um cargo para realizar a busca.",
        )

    servidores = _executar_busca_textual(Servidor.cargo, params.cargo, params.limite)
    if not servidores:
        return resposta_sem_resultados(
            query=params.cargo,
            sugestao=f"Nenhum servidor encontrado para o cargo '{params.cargo}'.",
        )

    return ServidoresToolResponse(
        query=params.cargo,
        total=len(servidores),
        resultados=[serializar_servidor(servidor) for servidor in servidores],
    ).model_dump(mode="json")
