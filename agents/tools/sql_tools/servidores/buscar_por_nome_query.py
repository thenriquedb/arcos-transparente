"""Tool para buscar servidores por nome."""

from __future__ import annotations

from typing import Any

from pydantic import ValidationError
from sqlalchemy import func, select

from agents.tools.registry import register
from database import session as session_manager
from database.models import Servidor

from .shared.params import BuscarServidorPorNomeParams
from .shared.responses import ServidoresToolResponse
from .shared.runtime import resposta_sem_resultados, serializar_servidor


@register(name="buscar_servidores_por_nome")
def buscar_servidores_por_nome(nome: str, limite: int = 10) -> dict[str, Any]:
    """
    Busca um servidor pelo nome ou parte do nome.

    Examples:
      'qual o salário de João Silva',
      'me mostre os dados de Maria Souza'.

    Args:
        nome (str): O nome ou parte do nome do servidor a ser buscado.
        limite (int): O número máximo de resultados a serem retornados.
    Returns:
        dict com a query, total e resultados padronizados.
    """
    try:
        params = BuscarServidorPorNomeParams.model_validate(
            {"nome": nome, "limite": limite}
        )
    except ValidationError as exc:
        return resposta_sem_resultados(mensagem=f"Parametros invalidos: {exc}")

    if not params.nome:
        return resposta_sem_resultados(
            query=nome,
            mensagem="Informe um nome de servidor para realizar a busca.",
        )

    palavras = params.nome.lower().split()
    filtros = [func.lower(Servidor.nome).like(f"%{palavra}%") for palavra in palavras]

    with session_manager.get_session() as session:
        servidores = (
            session.execute(
                select(Servidor)
                .where(*filtros)
                .order_by(Servidor.nome.asc())
                .limit(params.limite)
            )
            .scalars()
            .all()
        )

    if not servidores:
        return resposta_sem_resultados(
            query=params.nome,
            sugestao=(
                f"Nenhum servidor encontrado com '{params.nome}'. "
                "Tente buscar por partes do nome, ex: só o sobrenome."
            ),
        )

    return ServidoresToolResponse(
        query=params.nome,
        total=len(servidores),
        resultados=[serializar_servidor(servidor) for servidor in servidores],
    ).model_dump(mode="json")
