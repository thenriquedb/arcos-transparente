"""Tool para buscar servidores por mes de referencia em um periodo."""

from __future__ import annotations

from typing import Any

from pydantic import ValidationError
from sqlalchemy import select

from agents.tools.registry import register
from database import session as session_manager
from database.models import Servidor

from .shared.params import BuscarServidorPorMesDeReferenciaParams
from .shared.responses import ServidoresToolResponse
from .shared.runtime import resposta_sem_resultados, serializar_servidor


@register(name="buscar_servidores_por_mes_de_referencia_no_periodo")
def buscar_servidores_por_mes_de_referencia_no_periodo(
    data_inicio: str,
    data_fim: str,
    limite: int = 10,
) -> dict[str, Any]:
    """
    Busca servidores com registros em um periodo especifico.

    Examples:
        'quais servidores aparecem entre 01/01/2025 e 31/03/2025',
        'me mostre os servidores com mes de referencia em 2025-02-01'.

    Args:
        data_inicio (str): Data inicial do periodo no formato `DD/MM/YYYY` ou ISO.
        data_fim (str): Data final do periodo no formato `DD/MM/YYYY` ou ISO.
        limite (int): O numero maximo de resultados a serem retornados.
    Returns:
        dict com o periodo consultado, total e resultados padronizados.
    """
    try:
        params = BuscarServidorPorMesDeReferenciaParams.model_validate(
            {
                "data_inicio": data_inicio,
                "data_fim": data_fim,
                "limite": limite,
            }
        )
    except ValidationError as exc:
        return resposta_sem_resultados(mensagem=f"Parametros invalidos: {exc}")

    with session_manager.get_session() as session:
        servidores = (
            session.execute(
                select(Servidor)
                .where(
                    Servidor.competencia_referencia.between(
                        params.data_inicio,
                        params.data_fim,
                    )
                )
                .order_by(
                    Servidor.competencia_referencia.asc(),
                    Servidor.nome.asc(),
                )
                .limit(params.limite)
            )
            .scalars()
            .all()
        )

    if not servidores:
        return resposta_sem_resultados(
            data_inicio=params.data_inicio,
            data_fim=params.data_fim,
            sugestao="Nenhum servidor encontrado no periodo informado.",
        )

    return ServidoresToolResponse(
        data_inicio=params.data_inicio,
        data_fim=params.data_fim,
        total=len(servidores),
        resultados=[serializar_servidor(servidor) for servidor in servidores],
    ).model_dump(mode="json")
